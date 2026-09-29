"""Persistent, explicitly started batches using the frozen diagnostic's sampler."""
from collections import Counter
from copy import deepcopy
import fcntl
from hashlib import sha256
import importlib.util
from importlib.metadata import version
import os
from pathlib import Path
from threading import Lock, Thread
from uuid import UUID

from src.agents import notebook_student as store
from src.eval import notebook_action
from src.labeling import llm


RUNNER = Path(__file__).resolve().parents[2]/'experiments/2026-09-29-next-action-monte-carlo/run.py'
DECISIONS = ('revise-work', 'reply', 'no-reply')


def _pins():
    return {str(path):sha256(path.read_bytes()).hexdigest() for path in (
        RUNNER, Path(__file__), Path(store.__file__), Path(llm.__file__), Path(notebook_action.__file__))}


def _identifier(value):
    try:
        if not isinstance(value, str) or str(UUID(value)) != value:
            raise ValueError
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError('Supply a canonical request UUID.') from exc
    return value


def _no_symlinks(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Sampling storage cannot use symlinks.')


def _prepared(data):
    if (not isinstance(data, dict) or data.get('model') != 'gemini-2.5-pro'
            or not isinstance(data.get('prompt'), str)
            or sha256(data['prompt'].encode()).hexdigest() != data.get('prompt_sha256')
            or data.get('schema') != notebook_action.Action.model_json_schema()):
        raise ValueError('Prepared input, prompt, model or action schema changed.')
    return deepcopy(data)


class SamplingJobs:
    def __init__(self, root, get_input, generate=None):
        self.root = Path(root).absolute()
        _no_symlinks(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._thread = None
        self._active = None
        self._closed = False
        lock_path = self.root/'.lock'
        _no_symlinks(lock_path)
        self._owner = lock_path.open('a')
        try:
            # ponytail: one local owner and one in-flight call; use a service queue for multiple hosts.
            try:
                fcntl.flock(self._owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError('Sampling storage already has an active owner.') from exc
            self.get_input = get_input
            self._input_sha256 = store.digest(_prepared(get_input()))
            self._code_pins = _pins()
            spec = importlib.util.spec_from_file_location('next_action_sampling_frozen', RUNNER)
            self.sampler = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.sampler)
            self.generate = generate if generate is not None else self.sampler.live_generate
            self._live = generate is None
            for path in self.root.glob('*.json'):
                batch = self._read(_identifier(path.stem))
                if batch['status'] == 'running':
                    batch.update(status='interrupted', finished_at=self.sampler.now())
                    self._write(batch)
        except BaseException:
            self._owner.close()
            raise

    def _read(self, batch_id):
        path = self.root/f'{_identifier(batch_id)}.json'
        _no_symlinks(path)
        if not path.exists():
            raise KeyError(batch_id)
        if not path.is_file() or path.stat().st_size > 64*1024*1024:
            raise ValueError('Sampling receipt must be a bounded regular file.')
        envelope = store._read(path)
        batch = envelope['batch']
        if (envelope['sha256'] != store.digest(batch) or batch['id'] != batch_id
                or batch['request_id'] != batch_id or batch.get('version') != 1
                or type(batch['requested']) is not int or not 1 <= batch['requested'] <= 100
                or type(batch['cancel_requested']) is not bool or not isinstance(batch['records'], list)
                or batch['status'] not in ('running', 'complete', 'cancelled', 'interrupted', 'error')
                or batch['input_sha256'] != store.digest(batch['prepared'])
                or batch['input_sha256'] != self._input_sha256
                or len(batch['records']) > batch['requested']):
            raise ValueError('Sampling receipt changed or is incomplete.')
        data = _prepared(batch['prepared'])
        plan = batch['plan']
        # The receipt format may outlive runtime fixes; the frozen interpretation stays pinned.
        pins = plan['code_pins']
        if (set(pins) != set(self._code_pins)
                or any(pins[path] != pin for path, pin in self._code_pins.items() if path != __file__)
                or plan['model'] != data['model'] or plan['prompt_sha256'] != data['prompt_sha256']
                or plan['generation_config'] != {'response_mime_type':'application/json', 'response_schema':data['schema']}
                or plan['timeout_ms'] != 120000 or plan['sdk_attempts'] != 1):
            raise ValueError('Sampling plan differs from its frozen input or implementation.')
        pending = 0
        for index, record in enumerate(batch['records'], 1):
            if (type(record['index']) is not int or record['index'] != index
                    or record['status'] not in ('pending', 'complete', 'error')
                    or record.get('prompt_sha256') != data['prompt_sha256']):
                raise ValueError('Sampling record changed.')
            if record['status'] == 'pending':
                pending += 1
                if index != len(batch['records']):
                    raise ValueError('Only the last sample may be pending.')
            elif record['finished_at'] < record['started_at']:
                raise ValueError('Sample completion precedes its request.')
            if record['status'] == 'complete':
                if record.get('response') != self.sampler.parse_response(record['raw_response']):
                    raise ValueError('Accepted action differs from raw provider response.')
            elif 'response' in record:
                raise ValueError('Incomplete samples cannot contain accepted actions.')
        if ((batch['status'] == 'complete' and len(batch['records']) != batch['requested'])
                or (batch['status'] in ('complete', 'cancelled') and pending)
                or (batch['status'] == 'cancelled' and not batch['cancel_requested'])):
            raise ValueError('Sampling status differs from its completed records.')
        return batch

    def _write(self, batch):
        path = self.root/f'{_identifier(batch["id"])}.json'
        _no_symlinks(path)
        # ponytail: rewrite at most 100 samples; use per-draw files if larger batches are needed.
        store._save(path, {'sha256':store.digest(batch), 'batch':batch})

    def _summary(self, batch):
        counts = Counter(record['status'] for record in batch['records'])
        return {**{key:batch[key] for key in (
            'id', 'request_id', 'status', 'requested', 'cancel_requested', 'created_at', 'input_sha256')},
            'finished':counts['complete']+counts['error'], 'valid':counts['complete'],
            'failed':counts['error'], 'model':batch['prepared']['model']}

    def _verify_send(self, batch):
        data = _prepared(self.get_input())
        plan = batch['plan']
        if (store.digest(data) != batch['input_sha256'] or batch['input_sha256'] != self._input_sha256
                or _pins() != self._code_pins or plan['code_pins'] != self._code_pins
                or plan['sdk_version'] != version('google-genai')
                or plan['model'] != data['model'] or plan['prompt_sha256'] != data['prompt_sha256']
                or plan['generation_config'] != {'response_mime_type':'application/json', 'response_schema':data['schema']}
                or plan['timeout_ms'] != 120000 or plan['sdk_attempts'] != 1):
            raise ValueError('Sampling input or pinned implementation changed.')
        return data

    def start(self, request_id, runs, input_sha256):
        request_id = _identifier(request_id)
        if type(runs) is not int or not 1 <= runs <= 100:
            raise ValueError('Choose between 1 and 100 samples.')
        if not isinstance(input_sha256, str) or input_sha256 != self._input_sha256:
            raise ValueError('The selected sampling input changed.')
        with self._lock:
            if self._closed:
                raise RuntimeError('Sampling is shutting down.')
            path = self.root/f'{request_id}.json'
            if path.exists() or path.is_symlink():
                batch = self._read(request_id)
                if batch['requested'] != runs or batch['input_sha256'] != input_sha256:
                    raise ValueError('This request UUID already identifies a different batch.')
                return self._summary(batch)
            if self._thread is not None and self._thread.is_alive():
                raise RuntimeError('A sampling batch is already running.')
            if self._live and not os.environ.get('GEMINI_API_KEY'):
                raise ValueError('GEMINI_API_KEY is not configured.')
            data = _prepared(self.get_input())
            batch = {'version':1, 'id':request_id, 'request_id':request_id, 'status':'running',
                'requested':runs, 'cancel_requested':False, 'created_at':self.sampler.now(),
                'input_sha256':input_sha256, 'prepared':data, 'records':[],
                'plan':{'model':data['model'], 'prompt_sha256':data['prompt_sha256'],
                    'generation_config':{'response_mime_type':'application/json', 'response_schema':data['schema']},
                    'code_pins':self._code_pins, 'sdk_version':version('google-genai'),
                    'timeout_ms':120000, 'sdk_attempts':1}}
            self._verify_send(batch)
            self._write(batch)
            self._active = request_id
            self._thread = Thread(target=self._run, args=(request_id,), daemon=True)
            self._thread.start()
            return self._summary(batch)

    def _run(self, batch_id):
        try:
            while True:
                with self._lock:
                    batch = self._read(batch_id)
                    if batch['cancel_requested'] or len(batch['records']) == batch['requested']:
                        batch.update(status='cancelled' if batch['cancel_requested'] else 'complete',
                                     finished_at=self.sampler.now())
                        self._write(batch)
                        return
                    data = self._verify_send(batch)
                    record = {'index':len(batch['records'])+1, 'status':'pending',
                              'started_at':self.sampler.now(), 'prompt_sha256':data['prompt_sha256']}
                    batch['records'].append(record)
                    self._write(batch)
                    plan = deepcopy(batch['plan'])
                try:
                    raw = self.generate(plan, data['prompt'])
                except Exception as exc:
                    outcome = {'status':'error', 'error':{'type':type(exc).__name__}}
                else:
                    with self._lock:
                        batch = self._read(batch_id)
                        record = batch['records'][-1]
                        record['raw_response'] = raw
                        self._write(batch)  # Preserve failed/partial responses before validating them.
                    try:
                        outcome = {'status':'complete', 'response':self.sampler.parse_response(raw)}
                    except Exception as exc:
                        outcome = {'status':'error', 'error':{'type':type(exc).__name__}}
                with self._lock:
                    batch = self._read(batch_id)
                    batch['records'][-1].update(**outcome, finished_at=self.sampler.now())
                    self._write(batch)
        except BaseException as exc:
            # Never log provider exceptions: their messages can contain credentials or payloads.
            with self._lock:
                try:
                    batch = self._read(batch_id)
                    batch.update(status='error' if isinstance(exc, Exception) else 'interrupted',
                                 finished_at=self.sampler.now(), error={'type':type(exc).__name__})
                    self._write(batch)
                except (OSError, ValueError, KeyError, TypeError):
                    pass  # A damaged receipt remains blocked; reopening never sends it.

    def cancel(self, batch_id):
        with self._lock:
            batch = self._read(batch_id)
            if batch['status'] == 'running' and not batch['cancel_requested']:
                batch['cancel_requested'] = True
                self._write(batch)
            return self._summary(batch)

    def list(self):
        with self._lock:
            batches = [self._summary(self._read(path.stem)) for path in self.root.glob('*.json')]
            return sorted(batches, key=lambda batch:batch['created_at'], reverse=True)

    def snapshot(self, batch_id):
        with self._lock:
            batch = self._read(batch_id)
            summary = self._summary(batch)
            counts = Counter(record['response']['decision'] for record in batch['records']
                             if record['status'] == 'complete')
            return {**summary, 'attempts':summary['finished'], 'records':batch['records'],
                'categories':[{'decision':decision, 'count':counts[decision],
                    'proportion':counts[decision]/summary['valid'] if summary['valid'] else None,
                    'interval':self.sampler.wilson(counts[decision], summary['valid'])} for decision in DECISIONS]}

    def close(self):
        try:
            with self._lock:
                if self._closed:
                    return
                self._closed = True
                if self._thread is not None and self._thread.is_alive():
                    batch = self._read(self._active)
                    if batch['status'] == 'running':
                        batch['cancel_requested'] = True
                        self._write(batch)
        finally:
            if self._thread is not None:
                self._thread.join()  # The live provider call has its pinned 120-second timeout.
            self._owner.close()
