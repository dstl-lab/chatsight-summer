"""Run one bounded encounter through the existing saved student and tutor."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from src.agents import notebook_student as student, notebook_tutor as tutor, tutor_context


def run(folder, *, policy, generate_student, generate_tutor, check, max_tutor_turns=2, reference=None):
    if not isinstance(policy, str) or not policy.strip():
        raise ValueError('Supply a nonblank teaching policy.')
    if type(max_tutor_turns) is not int or not 0 <= max_tutor_turns <= 10:
        raise ValueError('Use zero to ten tutor replies.')
    folder = Path(folder)
    output = folder / 'lesson'
    with student._locked(folder):
        manifest, state, _, initial_decisions = student._load(folder)
        if reference is not None:
            reference = tutor.LibraryReference.model_validate(reference).model_dump()
            if any(reference[key] != state['activity'][key] for key in ('library', 'library_version')):
                raise ValueError('Library reference must match the activity library and version exactly.')
        # ponytail: one invocation per session; inspect receipts before any explicit manual continuation.
        output.mkdir(exist_ok=False)
        receipt = {'version':1, 'status':'pending', 'started_at':datetime.now(timezone.utc).isoformat(),
            'source_sha256':student.digest(Path(__file__).read_text()), 'engine':student._engine(),
            'sources':{Path(module.__file__).name:student.digest(Path(module.__file__).read_text())
                       for module in (tutor, tutor_context)},
            'authorization':'Standing project Gemini approval; generated tutor replies are supplied interventions.',
            'request':{'session_sha256':student.digest(manifest), 'state_sha256':student.digest(state),
                       'model':manifest['model'], 'policy':policy, 'reference':reference,
                       'max_tutor_turns':max_tutor_turns, 'max_student_decisions':manifest['max_decisions'],
                       'student_decisions_before':initial_decisions}}
        path = output / 'receipt.json'
        student._save(path, receipt, exclusive=True)
    turns = 0
    try:
        while True:
            with student._locked(folder):
                current, observed, _, decisions = student._load(folder)
                if current != manifest or observed != state:
                    raise ValueError('Student session changed outside this lesson; inspect its receipts.')
            if state['status'] not in ('active', 'awaiting-tutor'):
                reason = state['status']
                break
            if decisions >= manifest['max_decisions']:
                reason = 'student-budget'
                break
            if state['status'] == 'active':
                result = student.step(folder, generate=generate_student, check=check, max_actions=1,
                    expected_state_sha256=student.digest(state), expected_session_sha256=student.digest(manifest))
            else:
                if turns >= max_tutor_turns:
                    reason = 'tutor-budget'
                    break
                exchange = output / f'tutor-{turns+1:04}'
                binding = {'state_sha256':student.digest(state), 'session_sha256':student.digest(manifest)}

                def bound_tutor(prompt, schema):
                    if student._read(exchange / 'context.json')['binding'] != binding:
                        raise ValueError('Student session changed before this tutor request.')
                    return generate_tutor(prompt, schema)

                result = tutor.respond(folder, exchange, policy=policy, generate_tutor=bound_tutor,
                    generate_student=generate_student, check=check, model=manifest['model'],
                    max_actions=1, reference=reference)
                turns += 1
            state = result['state']
        result = {'state':state, 'stop_reason':reason,
                  'student_decisions':decisions-initial_decisions, 'tutor_turns':turns}
        receipt.update(status='complete', result=result, finished_at=datetime.now(timezone.utc).isoformat())
        student._save(path, receipt)
        return result
    except Exception as error:
        receipt.update(status='error', error={'type':type(error).__name__, 'message':str(error)},
                       finished_at=datetime.now(timezone.utc).isoformat())
        student._save(path, receipt)
        raise


def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--policy-file', type=Path, required=True)
    parser.add_argument('--reference-file', type=Path)
    parser.add_argument('--max-tutor-turns', type=int, default=2)
    parser.add_argument('--send', action='store_true', help='Allow this bounded student–tutor encounter.')
    args = parser.parse_args()
    if not args.send:
        parser.error('Use --send to run; notebook_student show provides offline replay.')
    reference = tutor.LibraryReference.model_validate(student._read(args.reference_file)) if args.reference_file else None
    model = student._read(args.folder / 'session.json')['model']
    provider = None

    def generate(prompt, schema):
        nonlocal provider
        if provider is None:
            load_dotenv(Path.cwd() / '.env')
            load_dotenv(Path(__file__).resolve().parents[3] / 'main/.env')
            provider = student.llm.make_generate(os.environ['GEMINI_API_KEY'], model=model)
        return provider(prompt, schema)

    result = run(args.folder, policy=args.policy_file.read_text(encoding='utf-8'), reference=reference,
                 max_tutor_turns=args.max_tutor_turns, generate_student=generate, generate_tutor=generate,
                 check=student.notebook_runtime.check_work)
    print(json.dumps({key:value for key,value in result.items() if key != 'state'}, indent=2))
    print(tutor_context.render(tutor_context.snapshot(args.folder)), end='')
    if result['state']['status'] in ('error', 'environment-error', 'execution-limit'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
