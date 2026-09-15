"""Score supplied action probabilities offline against training frequencies."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    conversation_id: str
    student_id: str | None = None
    label: str | None
    exclusion_reason: str | None = None

    @field_validator('id', 'conversation_id', 'student_id', 'label')
    @classmethod
    def clean_identifier(cls, value):
        if value is not None and (not value or value != value.strip()):
            raise ValueError('Identifiers and labels must be nonblank with no surrounding whitespace.')
        return value

    @model_validator(mode='after')
    def labeled_or_excluded(self):
        if self.label is None:
            if not self.exclusion_reason or not self.exclusion_reason.strip():
                raise ValueError('An unknown reference needs an explicit exclusion reason.')
        elif self.exclusion_reason is not None:
            raise ValueError('Use a label or an exclusion reason, not both.')
        return self


class Prediction(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, allow_inf_nan=False)
    id: str = Field(min_length=1)
    status: Literal['ok', 'error', 'no-reply', 'unlabeled']
    probabilities: dict[str, float] | None = None
    reason: str | None = None

    @model_validator(mode='after')
    def forecast_or_failure(self):
        if self.status == 'ok':
            if self.probabilities is None or self.reason is not None:
                raise ValueError('An ok forecast needs probabilities and no failure reason.')
        elif self.probabilities is not None or not self.reason or not self.reason.strip():
            raise ValueError('A non-ok outcome needs a reason and no probabilities.')
        return self


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    description: str = Field(min_length=1)
    classes: list[str] = Field(min_length=2)
    train: list[Record] = Field(min_length=1)
    evaluation: list[Record] = Field(min_length=1)
    predictions: list[Prediction]


def _brier(probabilities, label):
    # Multiclass sum, not divided by class count or by two: range [0, 2].
    return math.fsum((p - int(action == label)) ** 2 for action, p in probabilities.items())


def _averages(rows):
    baseline = mean(row['baseline_brier'] for row in rows) if rows else None
    model = mean(row['model_brier'] for row in rows) if rows else None
    return {'baseline_brier':baseline, 'model_brier':model,
            'baseline_minus_model':baseline - model if rows else None}


def evaluate(value: dict) -> dict:
    data = Input.model_validate(value)
    classes = set(data.classes)
    if (len(classes) != len(data.classes) or any(not k or k != k.strip() for k in classes)
            or classes & {'insufficient-evidence', 'unclear', 'no-followup-observed', 'no-reply', 'error', 'unlabeled'}):
        raise ValueError('Use unique observable actions; uncertainty, absence and model failures are not target classes.')
    records = data.train + data.evaluation
    if len({r.id for r in records}) != len(records):
        raise ValueError('Record IDs must be unique across both splits.')
    if any(r.label is not None and r.label not in classes for r in records):
        raise ValueError('Every known reference label must belong to classes.')
    students = {}
    for record in records:
        if record.student_id is not None:
            previous = students.setdefault(record.conversation_id, record.student_id)
            if previous != record.student_id:
                raise ValueError('A conversation has conflicting declared student IDs.')
    train_conversations = {r.conversation_id for r in data.train}
    if train_conversations & {r.conversation_id for r in data.evaluation}:
        raise ValueError('Training and evaluation conversations overlap, including excluded rows.')
    train_students = {r.student_id for r in data.train if r.student_id is not None}
    if train_students & {r.student_id for r in data.evaluation if r.student_id is not None}:
        raise ValueError('Training and evaluation students overlap, including excluded rows.')

    def group(record):
        student = students.get(record.conversation_id)
        return ('student', student) if student is not None else ('conversation', record.conversation_id)

    predicted = {p.id:p for p in data.predictions}
    if len(predicted) != len(data.predictions) or predicted.keys() - {r.id for r in data.evaluation}:
        raise ValueError('Predictions must have unique IDs from the evaluation split.')
    for prediction in data.predictions:
        p = prediction.probabilities
        if prediction.status == 'ok' and (set(p) != classes or any(not 0 <= x <= 1 for x in p.values())
                or not math.isclose(math.fsum(p.values()), 1, rel_tol=0, abs_tol=1e-9)):
            raise ValueError('Each forecast must name every class with finite probabilities in [0,1] summing to 1.')
    train_counts = Counter(r.label for r in data.train if r.label is not None)
    n_train = sum(train_counts.values())
    if not n_train:
        raise ValueError('At least one labeled training record is required for the frequency baseline.')
    probabilities = {key:train_counts[key] / n_train for key in data.classes}
    rows, grouped = [], defaultdict(list)
    for reference in data.evaluation:
        prediction = predicted.get(reference.id)
        status = prediction.status if prediction else 'missing'
        known = reference.label is not None
        scored = known and status == 'ok'
        unit, group_id = group(reference)
        row = {'id':reference.id, 'group':{'unit':unit, 'id':group_id}, 'label':reference.label,
               'reference_exclusion_reason':reference.exclusion_reason, 'prediction_status':status,
               'prediction_reason':prediction.reason if prediction else 'No supplied prediction for this record.',
               'scored':scored, 'baseline_brier':_brier(probabilities, reference.label) if known else None,
               'model_brier':_brier(prediction.probabilities, reference.label) if scored else None}
        rows.append(row)
        if scored:
            grouped[group(reference)].append(row)
    paired = [row for row in rows if row['scored']]
    labeled = [row for row in rows if row['label'] is not None]
    group_scores = [_averages(members) for members in grouped.values()]
    by_label = {label:{'n':len(selected), **_averages(selected)} for label in data.classes
                for selected in [[row for row in paired if row['label'] == label]]}
    statuses = Counter(row['prediction_status'] for row in rows)
    return {
        'dataset':data.description,
        'scope':'Descriptive scores of supplied forecasts for the next recorded message action; no generation or automatic labeling.',
        'metric':'Multiclass Brier = sum over classes of (probability - observed indicator)^2; lower is better; range [0,2].',
        'counts':{'train':len(data.train), 'train_labeled':n_train, 'evaluation':len(rows),
                  'evaluation_labeled':len(labeled), 'paired_scored':len(paired)},
        'grouping':{'rule':'Declared student ID when known, otherwise conversation ID.',
                    'evaluation_groups':len({group(r) for r in data.evaluation}),
                    'conversation_only_groups':len({group(r) for r in data.evaluation if group(r)[0] == 'conversation'}),
                    'limit':'Missing student identities cannot rule out the same student across different conversations.'},
        'prediction_status':{status:statuses[status] for status in ('ok','error','no-reply','unlabeled','missing')},
        'coverage':{'reference_labeled':len(labeled)/len(rows),
                    'prediction_on_labeled':len(paired)/len(labeled) if labeled else None,
                    'joint':len(paired)/len(rows)},
        'baseline':{'train_counts':{key:train_counts[key] for key in data.classes}, 'probabilities':probabilities,
                    'all_labeled_evaluation':{'n':len(labeled), 'encounter_mean_brier':mean(r['baseline_brier'] for r in labeled) if labeled else None}},
        'paired':{'n':len(paired), 'groups':len(grouped), 'encounter_mean':_averages(paired),
                  'group_mean':_averages(group_scores), 'by_reference_label':by_label},
        'train_exclusions':[r.model_dump() for r in data.train if r.label is None], 'rows':rows,
        'limits':[
            'Paired scores compare the same labeled rows with usable forecasts; failed or missing forecasts are excluded and counted separately.',
            'Selective prediction failures can bias paired scores. Coverage and all excluded rows must accompany every comparison.',
            'Group means give each represented group equal weight; they are not confidence intervals or a significance test.',
            'Supplied probabilities are not verified generator frequencies. Any draw sampling, output labeling and uncertainty analysis require a separate frozen protocol.',
            'This report selects no winner, practical improvement threshold or next experiment; it does not establish student realism, learning, reply probability or tutor effects.'
        ]}


def render(report):
    def number(value):
        return 'not scored' if value is None else f'{value:.6f}'

    count, paired = report['counts'], report['paired']
    table = ['| Weighting | Frequency baseline | Supplied forecasts | Baseline minus forecast |',
             '| --- | ---: | ---: | ---: |']
    for name, key in (('Each encounter equally','encounter_mean'), ('Each represented group equally','group_mean')):
        scores = paired[key]
        table.append('| ' + name + ' | ' + ' | '.join(number(scores[k]) for k in ('baseline_brier','model_brier','baseline_minus_model')) + ' |')
    # A JSON string stays on one fenced line, so supplied descriptions cannot become Markdown/HTML.
    parts = ['# Offline action scoring', '```json\n' + json.dumps(report['dataset'], ensure_ascii=False) + '\n```', report['scope'],
             f"Paired comparison: {paired['n']} of {count['evaluation']} evaluation records, across {paired['groups']} groups. "
             f"{count['evaluation_labeled']} records have known reference actions.", '\n'.join(table), report['metric'],
                  'A positive difference means lower error for the supplied forecasts on the scored subset. It is not a pass/fail decision.',
                  '## Coverage and limitations', '\n'.join('- ' + limit for limit in report['limits']),
                  report['grouping']['limit'], '## Full counts and record-level accounting',
                  '```json\n' + json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n```']
    return '\n\n'.join(parts) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='New directory for report.json and report.md.')
    args = parser.parse_args()
    raw = args.input.read_bytes()
    report = evaluate(json.loads(raw))
    report['provenance'] = {'input_sha256':sha256(raw).hexdigest(),
                            'source_sha256':sha256(Path(__file__).read_bytes()).hexdigest()}
    encoded = json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    markdown = render(report)
    args.output.mkdir(parents=True, exist_ok=False)
    for name, content in (('report.json',encoded), ('report.md',markdown)):
        with (args.output / name).open('x', encoding='utf-8') as stream:
            stream.write(content)
    print(args.output / 'report.md')


if __name__ == '__main__':
    main()
