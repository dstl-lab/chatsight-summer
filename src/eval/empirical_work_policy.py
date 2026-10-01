"""Retrospective human-reference work-presence baseline; no labels or LLM calls."""
from collections import Counter, defaultdict
from fractions import Fraction
from statistics import mean
from typing import Literal

from pydantic import BaseModel, field_validator

from src.eval.behavior_scoring import Record, _brier


Flag = Literal['yes', 'no', 'unclear', 'conflict'] | None
RULES = ('frequency', 'constant_half', 'always_no')


class Observation(BaseModel):
    model_config = Record.model_config
    id: str
    conversation_id: str
    account_id: str | None
    source: str
    origin: Literal['recorded']
    label_origin: Literal['human']
    rubric_id: Literal['help-work-v1']
    work_present: Flag
    help_request: Flag

    @field_validator('id', 'conversation_id', 'account_id', 'source')
    @classmethod
    def identifier(cls, value):
        if value is not None and (not value or value != value.strip()):
            raise ValueError('Identifiers must be nonblank without surrounding whitespace.')
        return value


def _reason(row):
    if row.account_id is None:
        return 'Account linkage unavailable; do not substitute conversation identity.'
    if row.work_present not in ('yes', 'no'):
        return 'Work reference unresolved; unknown is not absence.'
    return None


def _fit(rows):
    grouped = defaultdict(list)
    for row in rows:
        if _reason(row) is None:
            grouped[row.account_id].append(row)
    accounts = []
    for account, members in sorted(grouped.items()):
        positives = sum(r.work_present == 'yes' for r in members)
        accounts.append({'account_id': account, 'observation_ids': sorted(r.id for r in members),
            'messages': len(members), 'work_yes': positives, 'work_no': len(members) - positives,
            'fraction': str(Fraction(positives, len(members))),
            'account_weight': str(Fraction(1, len(grouped))),
            'message_weight': str(Fraction(1, len(grouped) * len(members)))})
    # ponytail: fixed support rule, not a statistical reliability threshold.
    enough = len(accounts) >= 2
    rate = sum((Fraction(r['fraction']) for r in accounts), Fraction()) / len(accounts) if enough else None
    return {'status': 'estimated' if enough else 'insufficient-evidence',
        'p_work_present': float(rate) if rate is not None else None,
        'fraction': str(rate) if rate is not None else None,
        'counts': {'input_messages': len(rows), 'eligible_messages': sum(r['messages'] for r in accounts),
                   'accounts': len(accounts), 'work_yes': sum(r['work_yes'] for r in accounts),
                   'work_no': sum(r['work_no'] for r in accounts),
                   'accounts_with_work_yes': sum(r['work_yes'] > 0 for r in accounts),
                   'accounts_with_work_no': sum(r['work_no'] > 0 for r in accounts)},
        'accounts': accounts}


def _predict(fit, rows):
    predictions = []
    for row in rows:
        probabilities = {'frequency': fit['p_work_present'], 'constant_half': .5, 'always_no': 0.0}
        reason = _reason(row)
        errors = {name: _brier({'yes': p, 'no': 1 - p}, row.work_present)
                  if reason is None and p is not None else None for name, p in probabilities.items()}
        predictions.append({'id': row.id, 'account_id': row.account_id, 'source': row.source,
            'work_present': row.work_present, 'p_work_present': probabilities['frequency'],
            'scored': errors['frequency'] is not None,
            'reason': reason or ('Insufficient training accounts.' if probabilities['frequency'] is None else None),
            'brier': errors})
    return predictions


def _summary(rows):
    grouped = defaultdict(list)
    for row in rows:
        if row['scored']:
            grouped[row['account_id']].append(row)
    return {'messages': len(rows), 'scored_messages': sum(len(v) for v in grouped.values()),
        'scored_accounts': len(grouped),
        'unknown_reference_messages': sum(r['work_present'] not in ('yes', 'no') for r in rows),
        'unlinked_messages': sum(r['account_id'] is None for r in rows),
        'account_mean_brier': {name: mean(mean(r['brier'][name] for r in members)
                                        for members in grouped.values()) if grouped else None
                               for name in RULES}}


def evaluate(value):
    """Fit descriptive frequencies and check predeclared account/source holdouts."""
    if not isinstance(value, list) or not value:
        raise ValueError('Supply recorded human observations.')
    rows = sorted((Observation.model_validate(row) for row in value), key=lambda r: r.id)
    if len({r.id for r in rows}) != len(rows):
        raise ValueError('Observation IDs must be unique; deduplicate exact inputs upstream.')
    identities = {}
    for row in rows:
        if row.account_id is not None and identities.setdefault(row.conversation_id, row.account_id) != row.account_id:
            raise ValueError('A conversation has conflicting account identities.')
    sources = sorted({r.source for r in rows})
    accounts = sorted({r.account_id for r in rows if r.account_id is not None})
    exclusions = [{'id': r.id, 'reason': _reason(r)} for r in rows if _reason(r) is not None]
    folds, predictions = [], []
    for account in accounts:
        fit = _fit([r for r in rows if r.account_id != account])
        targets = _predict(fit, [r for r in rows if r.account_id == account])
        folds.append({'held_account': account, 'fit': fit, 'predictions': targets, 'summary': _summary(targets)})
        predictions.extend(targets)
    # Unlinked observations are kept in coverage, but never get a guessed holdout identity.
    predictions.extend(_predict(_fit([]), [r for r in rows if r.account_id is None]))
    source_checks = {}
    for source in sources:
        targets = [r for r in rows if r.source == source]
        excluded = {r.account_id for r in targets if r.account_id is not None}
        fit = _fit([r for r in rows if r.source != source and r.account_id not in excluded])
        scored = _predict(fit, targets)
        source_checks[source] = {'excluded_accounts': sorted(excluded), 'fit': fit,
                                 'predictions': scored, 'summary': _summary(scored)}
    fitted = _fit(rows)
    return {'kind': 'retrospective-human-work-presence-baseline',
        'rubric_id': 'help-work-v1', 'target': 'work_present',
        'scope': 'Selected exposed development mixture; conditional on a recorded next message.',
        'metric': 'Two-class summed Brier = 2*(p-y)^2, range 0–2; account-average, lower better.',
        'weighting': 'Mean within each account, then equal weight per account. No smoothing.',
        'counts': {'observations': len(rows), 'linked_accounts': len(accounts),
                   'eligible_messages': fitted['counts']['eligible_messages'], 'excluded_messages': len(exclusions)},
        'exclusions': exclusions, 'fitted': fitted,
        'leave_account_out': {'folds': folds, 'summary': _summary(predictions),
            'by_class': {label: _summary([r for r in predictions if r['work_present'] == label])
                         for label in ('yes', 'no')},
            'by_source': {source: _summary([r for r in predictions if r['source'] == source]) for source in sources}},
        'sources': {source: {'fitted': _fit([r for r in rows if r.source == source]),
            'help_labels': dict(Counter(r.help_request or 'unresolved' for r in rows if r.source == source)),
            'work_labels': dict(Counter(r.work_present or 'unresolved' for r in rows if r.source == source))}
            for source in sources},
        'leave_source_out': source_checks,
        'limits': ['Human judgments retain their old rubric and unknown measurement error; they are not infallible truth.',
            'Generated messages and assistant labels are not observations used to fit this rule.',
            'Observed sources are selected development cases, not representative course-account samples.',
            'Source summaries have different case composition; the combined rate describes only this mixture.',
            'The fitted frequency is not scored on its own training labels as validation.',
            'Account exclusion prevents within-fold leakage, not prior research exposure or counterfactual bias.',
            'No calibration guarantee, rich behavior-policy validation, tutor-effect estimate or automatic adoption.',
            'No label conversion to hint/solution, work versus diagnostic, task changes, notebook actions or silence.']}
