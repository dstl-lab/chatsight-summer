"""Open an existing answer-free query as a saved chat, without model calls."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from src.agents import chat_student as chat, notebook_student as store
from src.eval import retrieval_baseline as retrieval


def _load(source):
    source = Path(source).resolve(strict=True)
    raw = source.read_bytes()
    try:
        value = json.loads(raw)
        # Reuse strict split/learner checks, as continuation_selection does.
        # ponytail: includes unused TF-IDF work; extract validation if corpus size makes this slow.
        retrieval.predict(value)
        data = retrieval.Input.model_validate(value)
    except ValueError:
        # Validation errors can contain private input text; keep CLI output metadata-only.
        raise ValueError('Invalid query input or overlapping IDs, conversations or known learners.') from None
    return source, raw, data


def catalog(source):
    source, raw, data = _load(source)
    return {'input_sha256': sha256(raw).hexdigest(),
            'unknown_learner_ids': any(row.student_id is None for row in [*data.train, *data.queries]),
            'queries': [{'id': query.id, 'conversation_id': query.conversation_id,
                         'turns': len(query.prefix),
                         'student_turns': sum(turn.role == 'student' for turn in query.prefix)}
                        for query in sorted(data.queries, key=lambda row: row.id)]}


def create(source, folder, *, query_id, input_sha256, model, max_decisions=6):
    """Select by ID and inspected input hash; preserve prefix text and omit every target."""
    folder = Path(folder).absolute()
    if folder.exists() or folder.is_symlink():
        raise FileExistsError('The destination already exists; use a fresh session directory.')
    source, raw, data = _load(source)
    if sha256(raw).hexdigest() != input_sha256:
        raise ValueError('The input changed; inspect its catalog again.')
    selected = next((query for query in data.queries if query.id == query_id), None)
    if selected is None:
        raise ValueError('The selected query ID does not exist in this input.')
    query = selected.model_dump()
    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent, prefix='.recorded-chat-') as temporary:
        staged = Path(temporary) / 'session'
        chat.create(staged, query=query, model=model, max_decisions=max_decisions)
        snapshot = chat.show(staged)  # Creates the lock needed by read-only browser projection.
        receipt = {'version': 1, 'input_path': str(source), 'input_sha256': input_sha256,
                   'split': 'queries', 'selection': 'explicit-query-id', 'query_id': query_id,
                   'query_sha256': store.digest(query),
                   'session_sha256': snapshot['binding']['session_sha256']}
        store._save(staged / 'recorded-start.json', receipt, exclusive=True)
        if source.read_bytes() != raw:
            raise ValueError('The input changed during preparation; no session was published.')
        # Reserve before publication, as chat_policy_pair does; never replace another creator's directory.
        folder.mkdir(exist_ok=False)
        os.replace(staged, folder)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    listing = commands.add_parser('list', help='List query IDs and context counts, without message text.')
    listing.add_argument('input', type=Path)
    creating = commands.add_parser('create', help='Create one offline chat from an inspected query split.')
    creating.add_argument('input', type=Path)
    creating.add_argument('folder', type=Path)
    creating.add_argument('--query-id', required=True)
    creating.add_argument('--input-sha256', required=True, help='Input hash returned by list.')
    creating.add_argument('--model', required=True, help='Saved chat model label; does not configure a backend.')
    creating.add_argument('--max-decisions', type=int, default=6)
    args = parser.parse_args()
    try:
        result = (catalog(args.input) if args.command == 'list' else
                  create(args.input, args.folder, query_id=args.query_id, input_sha256=args.input_sha256,
                         model=args.model, max_decisions=args.max_decisions))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
