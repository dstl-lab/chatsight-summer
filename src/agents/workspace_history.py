"""Read saved workspace receipts without continuing, repairing or rewriting a run."""
from pathlib import Path

from src.agents import notebook_student as store, tutor_context


def _record(path):
    value = store._read(path)
    if not isinstance(value, dict):
        raise ValueError('Expected a saved object.')
    return value


def _binding(request):
    return request['binding'] if 'binding' in request else {
        key: request[key] for key in ('session_sha256', 'state_sha256')}


def _error(value, diagnostics=True):
    if not diagnostics:
        return 'Diagnostic details are omitted from this view.'
    return tutor_context._block(value.get('message', 'No diagnostic saved.') if isinstance(value, dict) else value)


def _actions(receipt, notebook, diagnostics=True):
    calls = receipt['calls'] if notebook else [receipt | {'kind': 'model'}]
    sections = []
    for call in calls:
        if call['status'] == 'pending':
            sections.append('Request incomplete: no final result was saved. It is not automatically retried.')
        elif call['status'] == 'error':
            sections += [('Student generation failed.' if call['kind'] == 'model' else 'Local check failed.'),
                         _error(call['error'], diagnostics)]
        elif call['status'] == 'complete':
            response = call['response']
            if call['kind'] == 'check':
                status = response['status']
                outcome = ('Passed' if response['success'] else 'Failed') if status == 'checked' else {
                    'runtime-error': 'Execution error; ungraded',
                    'environment-error': 'Execution unavailable; ungraded',
                    'execution-limit': 'Execution limit reached; ungraded',
                }[status]
                sections.append('**Local check:** ' + outcome + '. This is not the course grader.')
                if response.get('error'):
                    sections.append(_error(response['error'], diagnostics))
            else:
                decision = response['decision']
                sections.append({'reply': '**Simulated student reply**',
                    'no-reply': '**Student chose no reply.** This does not establish learning or abandonment.',
                    'revise-work': '**Work edited**', 'request-check': '**Student requested a local check.**'}[decision])
                if decision == 'revise-work':
                    sections.append(tutor_context._block(response['source'], 'python'))
                if response['text']:
                    sections.append(tutor_context._block(response['text']))
        else:
            raise ValueError('Unknown request status.')
    if receipt['status'] == 'pending' and not any(call['status'] == 'pending' for call in calls):
        sections.append('Operation incomplete: no final result was saved. It is not automatically retried.')
    return sections


def _outcome(state, remaining):
    status = state['status']
    outcome = {
        'awaiting-tutor': 'Waiting for a tutor reply.',
        'active': 'Paused after the requested actions; the student can continue working.',
        'no-reply': 'Student chose no reply.',
        'error': 'Simulation stopped after an error.',
        'environment-error': 'Local execution was unavailable; work is ungraded.',
        'execution-limit': 'Local execution reached its limit; work is ungraded.',
    }[status]
    if remaining == 0 and status in ('active', 'awaiting-tutor'):
        outcome = 'Decision budget exhausted. This is a simulation pause, not student silence.'
    return '**Recorded outcome:** ' + outcome + (f' {remaining} decisions remaining.' if remaining is not None else '')


def render(folder, *, diagnostics=True):
    """Display both successful and incomplete receipts; link only confirmed policy delivery."""
    folder = Path(folder)
    manifest = _record(folder / 'session.json')
    notebook = 'initial' in manifest
    budget = manifest.get('max_decisions')
    if type(budget) is not int or not 1 <= budget <= 100:
        raise ValueError('Invalid saved decision budget.')
    sections = ['## Saved results',
        'These are saved records, not a new simulation. Saved record time can describe a cached '
        'reply being imported rather than a fresh model call. Policies below are the saved '
        'instructions for those exchanges, independent of the current draft. '
        'This view does not validate replay; if the session cannot reopen, these records remain unverified.']
    policies = []
    errors = []
    directories = sorted((folder / 'tutor-exchanges').glob('*'))
    if notebook and (folder / 'lesson').exists():
        directories.extend(sorted((folder / 'lesson').glob('tutor-*')))
        try:
            lesson = _record(folder / 'lesson/receipt.json')
            if lesson['request']['session_sha256'] != store.digest(manifest):
                raise ValueError('Lesson record belongs to a different session.')
            policy = lesson['request']['policy']
            if not isinstance(policy, str) or not policy.strip():
                raise ValueError('Missing configured lesson policy.')
            if lesson['status'] not in ('pending', 'complete', 'error'):
                raise ValueError('Unknown lesson status.')
            sections += ['### Configured lesson policy', tutor_context._block(policy),
                         'Configuration does not confirm delivery. Confirmed policy delivery '
                         'is shown at matching student steps below.']
            if lesson['status'] == 'pending':
                sections.append('Lesson incomplete. It is not automatically retried.')
            elif lesson['status'] == 'error':
                sections += ['Lesson failed.', _error(lesson.get('error', {}), diagnostics)]
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors += ['**The lesson record is unreadable or inconsistent.**', _error(str(exc), diagnostics)]
    for directory in directories:
        if not directory.is_dir():
            continue
        path = directory / 'receipt.json'
        try:
            receipt = _record(path)
            context = _record(path.parent / 'context.json')
            binding = context['binding']
            if binding['session_sha256'] != store.digest(manifest):
                raise ValueError('Tutor record belongs to a different session.')
            if notebook:
                if tutor_context.read_handoff(path.parent / 'context.json')['sha256'] != receipt['request']['context_sha256']:
                    raise ValueError('Tutor context changed.')
            elif receipt['request']['binding'] != binding:
                raise ValueError('Tutor context binding changed.')
            policy = receipt['request']['policy']
            if not isinstance(policy, str) or not policy.strip():
                raise ValueError('Missing saved policy.')
            if (receipt['status'] not in ('pending', 'complete', 'error') or
                    receipt['continuation']['status'] not in ('not-started', 'pending', 'complete', 'error')):
                raise ValueError('Unknown tutor or continuation status.')
            if not isinstance(receipt.get('response', {}), dict):
                raise ValueError('Invalid tutor response record.')
            if receipt['status'] == 'complete':
                reply = receipt['response']['text']
                if not isinstance(reply, str) or not reply.strip():
                    raise ValueError('Missing generated tutor reply.')
            if receipt['continuation']['status'] == 'complete' and not isinstance(receipt['continuation']['result']['state'], dict):
                raise ValueError('Missing saved continuation state.')
            policies.append((binding, receipt))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            errors += ['**A tutor record is unreadable or inconsistent.**', _error(str(exc), diagnostics)]

    used = set()
    decisions = 0
    for index, path in enumerate(sorted(folder.glob('step-*.json')), 1):
        sections.append(f'### Student step {index}')
        try:
            receipt = _record(path)
            request = receipt['request']
            binding = _binding(request)
            if binding['session_sha256'] != store.digest(manifest):
                raise ValueError('Step belongs to a different session.')
            matches = [i for i, (bound, tutor) in enumerate(policies)
                if bound == binding and tutor['status'] == 'complete'
                and tutor.get('response', {}).get('text') == request['tutor_reply']
                and tutor['continuation']['status'] == 'complete'
                and tutor['continuation']['result'].get('state') == (
                    receipt.get('result', {}).get('state') if notebook else receipt.get('result'))]
            body = ['**Saved record time**', tutor_context._block(receipt['started_at'])]
            if len(matches) == 1:
                matched = matches[0]
                body += ['**Tutor policy used**', tutor_context._block(policies[matched][1]['request']['policy']),
                         '**Tutor reply**', tutor_context._block(request['tutor_reply'])]
            elif request['tutor_reply'] is not None:
                body += ['**Supplied tutor reply** (no confirmed policy link)', tutor_context._block(request['tutor_reply'])]
            else:
                body.append('No tutor intervention in this step; continuing the existing context.')
            body += _actions(receipt, notebook, diagnostics)
            if decisions is not None:
                decisions += sum(call['kind'] == 'model' for call in receipt['calls']) if notebook else 1
                if decisions > budget:
                    raise ValueError('Saved requests exceed the decision budget.')
            if receipt['status'] in ('complete', 'error'):
                state = receipt['result']['state'] if notebook else receipt['result']
                body.append(_outcome(state, budget - decisions if decisions is not None else None))
                if state.get('error'):
                    body.append(_error(state['error'], diagnostics))
            if len(matches) == 1:
                used.add(matches[0])
            sections += body
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            decisions = None
            sections += ['**This student record is unreadable or inconsistent.**', _error(str(exc), diagnostics)]

    for i, (_, receipt) in enumerate(policies):
        if i in used:
            continue
        sections += ['### Tutor exchange without a confirmed student result',
                     '**Tutor policy saved**', tutor_context._block(receipt['request']['policy'])]
        reply = receipt.get('response', {}).get('text')
        sections += ['**Saved tutor reply**', tutor_context._block(reply)] if reply else ['No saved tutor reply.']
        if receipt.get('status') == 'error':
            sections += ['Tutor generation failed.', _error(receipt.get('error', {}), diagnostics)]
        elif receipt.get('status') == 'pending':
            sections.append('Tutor request incomplete. It is not automatically retried.')
        delivery = receipt.get('continuation', {})
        if delivery.get('status') == 'error':
            sections += ['Delivery failed; this tutor reply has no confirmed linked student result.', _error(delivery.get('error', {}), diagnostics)]
        elif delivery.get('status') == 'pending':
            sections.append('Student continuation incomplete. It is not automatically retried.')
        elif delivery.get('status') == 'complete':
            sections.append('The saved continuation could not be linked to a matching student step.')
        else:
            sections.append('No student continuation was started for this tutor exchange.')
    if not policies and not list(folder.glob('step-*.json')):
        sections.append('No saved exchanges yet.')
    return '\n\n'.join(sections + errors)
