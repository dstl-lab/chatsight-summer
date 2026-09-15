"""Offline next-message retrieval; query targets are deliberately not an input."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class Turn(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    role: Literal['student', 'tutor']
    text: str


class Query(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    id: str
    conversation_id: str
    student_id: str | None = None
    prefix: list[Turn] = Field(min_length=2)

    @field_validator('id', 'conversation_id', 'student_id')
    @classmethod
    def identifier(cls, value):
        if value is not None and (not value or value != value.strip()):
            raise ValueError('Identifiers must be nonblank without surrounding whitespace.')
        return value

    @model_validator(mode='after')
    def tutor_boundary(self):
        if self.prefix[-1].role != 'tutor' or not any(t.role == 'student' for t in self.prefix):
            raise ValueError('A prefix needs a student contribution and must end at a tutor turn.')
        return self


class Example(Query):
    response: str


class Input(BaseModel):
    model_config = Query.model_config
    train: list[Example] = Field(min_length=1)
    queries: list[Query] = Field(min_length=1)


def predict(value: dict) -> dict:
    data = Input.model_validate(value)
    records = data.train + data.queries
    if len({r.id for r in records}) != len(records):
        raise ValueError('Example and query IDs must be unique across both splits.')
    if {r.conversation_id for r in data.train} & {r.conversation_id for r in data.queries}:
        raise ValueError('Reference-library and query conversations overlap.')
    learners = {}
    for row in records:
        if row.student_id is not None:
            if learners.setdefault(row.conversation_id, row.student_id) != row.student_id:
                raise ValueError('A conversation has conflicting learner identities.')
    if ({r.student_id for r in data.train if r.student_id is not None}
            & {r.student_id for r in data.queries if r.student_id is not None}):
        raise ValueError('Reference-library and query learners overlap.')

    library = sorted(data.train, key=lambda r: r.id)
    # ponytail: whole-prefix lexical matching; consider role weighting only if
    # a fixed comparison shows tutor/task wording obscures student behavior.
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), token_pattern=r'(?u)\b\w+\b')
    text = lambda row: '\n'.join(turn.text for turn in row.prefix)
    try:
        features = vectorizer.fit_transform([text(row) for row in library])
    except ValueError as error:
        if 'empty vocabulary' not in str(error):
            raise
        features = None
    rows = []
    for query in data.queries:
        row = {'id': query.id, 'status': 'no-match', 'source_id': None,
               'source_conversation_id': None, 'similarity': 0.0, 'text': None}
        if features is not None:
            similarities = linear_kernel(vectorizer.transform([text(query)]), features)[0]
            index = int(similarities.argmax())
            if similarities[index] > 0:
                source = library[index]
                row.update(status='matched' if source.response.strip() else 'recorded-blank',
                           source_id=source.id, source_conversation_id=source.conversation_id,
                           similarity=float(similarities[index]), text=source.response)
        rows.append(row)
    return {'method': 'Train-prefix word unigram/bigram TF-IDF cosine; ties by source ID.',
            'counts': {'library_examples': len(library), 'queries': len(data.queries),
                       'library_conversations': len({r.conversation_id for r in library}),
                       'query_conversations': len({r.conversation_id for r in data.queries})},
            'predictions': rows,
            'limits': ['Retrieves recorded text verbatim; relevance and student fidelity are unmeasured.',
                       'Unknown learner IDs cannot establish learner-separated evaluation.',
                       'Similarity is not a probability. A blank message or no match is not student silence.',
                       'No semantic labels, notebook actions, execution or model calls.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    result = predict(json.loads(raw))
    result['provenance'] = {'input_sha256': sha256(raw).hexdigest(),
                            'source_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    with args.output.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    print(args.output)


if __name__ == '__main__':
    main()
