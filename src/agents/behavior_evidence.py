"""Versioned, offline evidence admission checks; never fit or dispatch a policy."""
import argparse
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FINE = 'behavior-pilot-v1-20261001'
RUBRICS = {'assistance': FINE, 'material': FINE, 'task_relation': FINE,
           'work_present': 'help-work-v1', 'help_requested': 'help-work-v1',
           'last_assistance': FINE, 'feedback': 'execution-feedback-v1'}
TARGETS = ('assistance', 'material', 'task_relation', 'work_present', 'help_requested')
CONTEXT = ('last_assistance', 'feedback')
ASSISTANCE = {'hint', 'explanation', 'solution', 'checking', 'unspecified'}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + '\n'


def event_digest(event):
    return sha256(canonical({k: v for k, v in event.items() if k != 'sha256'}).encode()).hexdigest()


def instant(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Timestamps require an explicit timezone.')
    return parsed


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Event(Strict):
    id: str = Field(min_length=1)
    account_id: str | None
    conversation_id: str = Field(min_length=1)
    timestamp: str
    origin: Literal['recorded', 'authored', 'generated']
    kind: Literal['student', 'tutor', 'execution']
    text: str
    source_ref: str = Field(min_length=1)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    revision_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    feedback: Literal['pass', 'fail', 'runtime-error', 'not-checked'] | None = None

    @field_validator('timestamp')
    @classmethod
    def aware(cls, value):
        instant(value)
        return value


class Annotation(Strict):
    field: Literal['assistance', 'material', 'task_relation', 'work_present', 'help_requested', 'last_assistance', 'feedback']
    value: list[str] | str | bool | None
    origin: Literal['human', 'assistant', 'authored', 'instrumentation']
    coder: str = Field(min_length=1)
    rubric: str = Field(min_length=1)
    evidence_event_ids: list[str]

    @model_validator(mode='after')
    def supported_value(self):
        value = self.value
        if value is None:
            return self
        if self.field in ('assistance', 'last_assistance', 'material'):
            allowed = {'work', 'diagnostic'} if self.field == 'material' else ASSISTANCE
            if not isinstance(value, list) or len(value) != len(set(value)) or not set(value) <= allowed:
                raise ValueError('Invalid or duplicate behavior labels.')
        elif self.field in ('work_present', 'help_requested'):
            if type(value) is not bool:
                raise ValueError('Coarse help/work observations require boolean or null.')
        elif self.field == 'task_relation':
            if value not in ('same', 'different'):
                raise ValueError('Task relation must be same, different or null.')
        elif value not in ('pass', 'fail', 'runtime-error', 'not-checked'):
            raise ValueError('Unsupported feedback.')
        return self


class Record(Strict):
    id: str = Field(min_length=1)
    account_id: str | None
    conversation_id: str = Field(min_length=1)
    membership: Literal['development', 'test']
    cutoff: str
    prefix_event_ids: list[str]
    outcome_event_id: str
    revision_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    context: list[Annotation]
    annotations: list[Annotation]

    @field_validator('cutoff')
    @classmethod
    def aware(cls, value):
        instant(value)
        return value


class Packet(Strict):
    version: Literal[1]
    synthetic: bool
    development_accounts: list[str]
    test_accounts: list[str]
    reserved_accounts: list[str]
    exposed_accounts: list[str]
    events: list[Event]
    records: list[Record]


def observation(rows, field):
    """Keep every judgment; agreement does not establish human accuracy."""
    selected = [row for row in rows if row.field == field]
    values = {canonical(sorted(r.value) if isinstance(r.value, list) else r.value) for r in selected}
    if not selected:
        status = 'missing'
    elif any(r.rubric != RUBRICS[field] for r in selected):
        status = 'incompatible-rubric'
    elif len(values) > 1:
        status = 'disputed'
    elif any(r.value is None for r in selected):
        status = 'unknown'
    elif not any(r.origin == ('instrumentation' if field == 'feedback' else 'human') for r in selected):
        status = 'exploratory-only'
    else:
        status = 'candidate'
    return {'status': status, 'value': selected[0].value if status == 'candidate' else None,
            'judgments': [r.model_dump() for r in selected]}


def admit(value):
    """Pure packet consistency checks, not authentication or scientific admission."""
    packet = Packet.model_validate(value)
    # Hash exactly the supplied event representation, including optional-field presence.
    raw_events = {e['id']: e for e in value['events']}
    events = {e.id: e for e in packet.events}
    if len(events) != len(packet.events) or len({r.id for r in packet.records}) != len(packet.records):
        raise ValueError('Duplicate event or record identity.')
    partitions = set(packet.development_accounts) & set(packet.test_accounts)
    outputs = []
    for row in packet.records:
        issues = []
        if not row.account_id:
            issues.append('unknown-account')
        if row.account_id in partitions:
            issues.append('account-partition-overlap')
        if row.account_id in packet.reserved_accounts:
            issues.append('reserved-account')
        membership = packet.development_accounts if row.membership == 'development' else packet.test_accounts
        if row.account_id not in membership:
            issues.append('account-membership-mismatch')
        if row.membership == 'test' and row.account_id in packet.exposed_accounts:
            issues.append('test-account-exposed')
        if row.outcome_event_id in row.prefix_event_ids:
            issues.append('target-in-prefix')
        if len(set(row.prefix_event_ids)) != len(row.prefix_event_ids):
            issues.append('duplicate-prefix-event')
        if sum(r.outcome_event_id == row.outcome_event_id for r in packet.records) > 1:
            issues.append('duplicate-outcome')
        refs = [*row.prefix_event_ids, row.outcome_event_id]
        for eid in refs:
            event = events.get(eid)
            if event is None:
                issues.append('missing-source-event')
                continue
            if event.sha256 != event_digest(raw_events[eid]):
                issues.append('source-hash-mismatch')
            if event.account_id != row.account_id:
                issues.append('event-account-mismatch')
            if event.conversation_id != row.conversation_id:
                issues.append('event-conversation-mismatch')
            if not packet.synthetic and event.source_ref.startswith('synthetic:'):
                issues.append('synthetic-source-in-recorded-packet')
            if event.origin != 'recorded':
                issues.append('nonrecorded-content')
        prefix = [events[eid] for eid in row.prefix_event_ids if eid in events]
        if any(instant(e.timestamp) > instant(row.cutoff) for e in prefix):
            issues.append('prefix-after-cutoff')
        if any(instant(a.timestamp) > instant(b.timestamp) for a, b in zip(prefix, prefix[1:])):
            issues.append('unordered-prefix')
        target = events.get(row.outcome_event_id)
        if target is not None:
            if instant(target.timestamp) <= instant(row.cutoff):
                issues.append('target-not-after-cutoff')
            if target.kind != 'student':
                issues.append('nonstudent-outcome')
        for label in row.context:
            if label.field not in CONTEXT:
                issues.append('outcome-field-in-context')
            if not label.evidence_event_ids or not set(label.evidence_event_ids) <= set(row.prefix_event_ids):
                issues.append('context-uses-nonprefix-evidence')
            if label.field == 'last_assistance' and label.value is not None and not any(
                    eid in events and events[eid].kind == 'student' for eid in label.evidence_event_ids):
                issues.append('context-assistance-missing-student-evidence')
            if label.field == 'feedback' and label.value is not None:
                bound = [events[eid] for eid in label.evidence_event_ids if eid in events]
                if not row.revision_sha256 or not any(e.kind == 'execution' and
                    e.revision_sha256 == row.revision_sha256 and e.feedback == label.value for e in bound):
                    issues.append('feedback-not-revision-bound')
        for label in row.annotations:
            if label.field not in TARGETS:
                issues.append('context-field-in-outcome')
            if row.outcome_event_id not in label.evidence_event_ids:
                issues.append('outcome-missing-target-evidence')
            if not set(label.evidence_event_ids) <= set(refs):
                issues.append('outcome-uses-outside-evidence')
            if label.field == 'task_relation' and label.value is not None and not (
                    set(label.evidence_event_ids) & set(row.prefix_event_ids)):
                issues.append('task-relation-missing-prefix-anchor')
        context = {field: observation(row.context, field) for field in CONTEXT}
        targets = {field: observation(row.annotations, field) for field in TARGETS}
        for target_result in targets.values():
            supported = not issues and target_result['status'] == 'candidate'
            target_result.update(candidate_reference=supported,
                empirical_reference=supported and not packet.synthetic,
                use_scope=row.membership + '-reference-under-original-rubric')
        context_ready = all(r['status'] == 'candidate' for r in context.values())
        joint_ready = all(targets[f]['candidate_reference'] for f in TARGETS[:3])
        reasons = []
        if issues:
            reasons.append('packet-integrity-or-isolation-failed')
        if not context_ready:
            reasons.append('incomplete-or-unqualified-prefix-context')
        if not joint_ready:
            reasons.append('incomplete-or-unqualified-joint-outcome')
        if row.membership != 'development':
            reasons.append('test-record-never-fit')
        ready = not reasons
        status = 'rejected' if issues else 'accepted' if ready else 'partial'
        outputs.append({'id': row.id, 'account_id': row.account_id, 'membership': row.membership,
            'status': status, 'issues': sorted(set(issues)), 'student_eligibility': 'not-assessed',
            'source_bindings': {eid: {key: events[eid].model_dump()[key] for key in
                ('sha256', 'source_ref', 'timestamp', 'kind', 'origin', 'account_id', 'conversation_id')}
                for eid in refs if eid in events},
            'cutoff': row.cutoff, 'prefix_event_ids': row.prefix_event_ids,
            'outcome_event_id': row.outcome_event_id,
            'content_origin': target.origin if target is not None else None,
            'prefix_context': context, 'annotations': [r.model_dump() for r in row.annotations],
            'targets': targets, 'joint_fit': {'eligible': False,
                'ready_for_protocol_review': ready, 'reasons': reasons +
                (['synthetic-fixture-not-empirical'] if packet.synthetic else []) +
                ['joint-fit-admission-protocol-not-established']}})
    return {'version': 1, 'synthetic': packet.synthetic, 'records': outputs,
        'limits': ['Acceptance means packet consistency and candidate reference support, not ground truth.',
            'Source hashes check supplied bytes, not independent source authenticity or natural use.',
            'Account partitions and exposure are supplied inventories; completeness is not established.',
            'No automatic semantic state extraction, label validation, fitting or sampler admission.',
            'Unknowns and disagreement are retained; coarse and fine rubrics are never translated.']}


def report(value):
    return {'version': 1, 'kind': 'behavior-evidence-admission',
        'input_sha256': sha256(canonical(value).encode()).hexdigest(),
        'source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(), 'result': admit(value)}


def markdown(saved):
    result = saved['result']
    lines = ['# Behavior evidence admission', '',
        'SYNTHETIC FIXTURE — no empirical evidence.' if result['synthetic'] else
        'Candidate reference checks — not verified student identity or annotation accuracy.', '',
        'No record is admitted for joint fitting or to the authored sampler.', '']
    for row in result['records']:
        lines += [f"    {row['id']}: {row['status']}",
            '    Candidate targets: ' + ', '.join(f for f, t in row['targets'].items() if t['candidate_reference']),
            '    Issues: ' + (', '.join(row['issues']) or 'none'), '']
    lines += ['Full observations, uncertainties, exclusions and bindings:', '']
    lines.extend('    ' + line for line in canonical(saved).splitlines())
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--format', choices=('json', 'markdown'), default='json')
    args = parser.parse_args()
    try:
        saved = report(json.loads(args.input.read_text(encoding='utf-8')))
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(markdown(saved) if args.format == 'markdown' else canonical(saved), end='')


if __name__ == '__main__':
    main()
