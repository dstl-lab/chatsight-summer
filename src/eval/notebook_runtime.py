"""Evaluate one table cell in an explicitly selected local container."""
import json
import keyword
import os
from pathlib import Path
import selectors
import subprocess
import tempfile
import time
from uuid import uuid4
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from src.eval.student_continuation import _digest

DISTINCT_COUNT_SOURCE = '28551ed1cb82d471ca4af9b0c5235f3a8598d10ab64077d45bef29415b919abf'


class Evaluation(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    expected: str | int | FiniteFloat | bool


class Activity(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    image_id: Annotated[str, Field(pattern=r'^sha256:[0-9a-f]{64}$')]
    library: Literal['pandas', 'babypandas']
    library_version: Annotated[str, Field(min_length=1, max_length=64)]
    table: Annotated[str, Field(pattern=r'^[A-Za-z_][A-Za-z_0-9]*$')]
    column: Annotated[str, Field(min_length=1, max_length=256)]
    result: Annotated[str, Field(pattern=r'^[A-Za-z_][A-Za-z_0-9]*$')]
    values: Annotated[list[Annotated[str, Field(max_length=256)]], Field(max_length=2048)]

    @model_validator(mode='after')
    def names(self):
        if self.table == self.result or any(keyword.iskeyword(n) or n == '__builtins__' for n in (self.table, self.result)):
            raise ValueError('Use distinct ordinary table and result identifiers.')
        return self


def _binding(work, branch_id, activity, timeout, evaluation=None):
    if not isinstance(branch_id, str) or not branch_id.strip():
        raise ValueError('A branch identity is required.')
    if (not isinstance(work, dict) or not isinstance(work.get('source'), str) or len(work['source']) > 20000
            or type(work.get('revision')) is not int or work['revision'] < 0):
        raise ValueError('Supply source (at most 20000 characters) and a nonnegative revision.')
    if type(timeout) not in (int, float) or not 0 < timeout <= 30:
        raise ValueError('Use a positive timeout of at most 30 seconds.')
    binding = {'branch_id':branch_id, 'revision':work['revision'], 'source_sha256':_digest(work['source']),
            'activity_sha256':_digest(activity.model_dump()), 'image_id':activity.image_id,
            'checker_sha256':_digest(Path(__file__).read_text()), 'timeout_seconds':float(timeout)}
    if evaluation is not None:
        binding['evaluation_sha256'] = _digest(Evaluation.model_validate(evaluation).model_dump())
    return binding


def _local_docker(image_id):
    contexts = json.loads(subprocess.run(['docker', 'context', 'inspect'], check=True,
                                        capture_output=True, text=True, timeout=5).stdout)
    if len(contexts) != 1 or not contexts[0]['Endpoints']['docker']['Host'].startswith('unix://'):
        raise ValueError('Only an explicitly local Docker context is supported.')
    command = ['docker', '--context', contexts[0]['Name']]
    actual = subprocess.run(command + ['image', 'inspect', '--format', '{{.Id}}', image_id],
                            check=True, capture_output=True, text=True, timeout=5).stdout.strip()
    if actual != image_id:
        raise ValueError('The requested immutable image is not available locally.')
    return command


def _execute(command, image_id, request, timeout):
    """Bound even direct OS-level output; remove only this call's named container."""
    name = 'learner-check-' + uuid4().hex
    args = command + ['run', '--name', name, '--pull=never', '--network=none', '--read-only',
                      '--user=65534:65534', '--cap-drop=ALL', '--security-opt=no-new-privileges',
                      '--pids-limit=64', '--memory=512m', '--cpus=1', '--log-driver=none',
                      '--tmpfs=/tmp:rw,noexec,nosuid,size=33554432', '--workdir=/tmp', '-i', image_id]
    output, problem, process, code = bytearray(), None, None, None
    try:
        with tempfile.TemporaryFile() as input_file:
            input_file.write(json.dumps(request, ensure_ascii=False).encode())
            input_file.seek(0)
            process = subprocess.Popen(args, stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            deadline = time.monotonic() + timeout
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0 or not selector.select(remaining):
                        problem = 'timeout'
                        break
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        try:
                            code = process.wait(timeout=max(0.001, deadline-time.monotonic()))
                        except subprocess.TimeoutExpired:
                            problem = 'timeout'
                        break
                    output.extend(chunk)
                    if len(output) > 65536:
                        del output[65536:]
                        problem = 'output-limit'
                        break
    finally:
        try:
            if process is not None:
                try:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
                finally:
                    process.stdout.close()
        finally:
            cleanup = subprocess.run(command + ['rm', '-f', name], capture_output=True, timeout=5)
            if cleanup.returncode and b'No such container' not in cleanup.stderr:
                raise RuntimeError('Container cleanup could not be verified: ' + name)
    return code, bytes(output), problem


def check_work(work: dict, *, branch_id: str, activity: dict, timeout: float = 10, evaluation=None) -> dict:
    """Evaluate one cell, then grade its returned scalar outside the candidate process.

    No host execution or implicit image pull. This checks supplied data, not a
    recovered notebook kernel, general correctness or resistance to grader gaming.
    """
    activity = Activity.model_validate(activity)
    binding = _binding(work, branch_id, activity, timeout, evaluation)
    expected = len(set(activity.values)) if evaluation is None else Evaluation.model_validate(evaluation).expected
    result = {'binding':binding, 'basis':'container', 'execution':'not-started',
              'status':'environment-error', 'success':None, 'value':None, 'runtime':None,
              'runtime_sha256':None, 'error':None, 'output':''}
    try:
        command = _local_docker(activity.image_id)
        request = activity.model_dump(exclude={'image_id'}) | {'source':work['source']}
        result['execution'] = 'attempted'
        code, output, problem = _execute(command, activity.image_id, request, timeout)
        lines = output.decode('utf-8', errors='replace').split('\n')
        if lines[-1] == '':
            lines.pop()
        if lines:
            try:
                runtime = json.loads(lines[0])
                if (isinstance(runtime, dict) and runtime.get('kind') == 'runtime' and isinstance(runtime.get('python'), str)
                        and isinstance(runtime.get('libraries'), dict)):
                    result['runtime'] = runtime | {'image_id':activity.image_id}
                    result['runtime_sha256'] = _digest(result['runtime'])
            except ValueError:
                pass
        if problem:
            result.update(status='execution-limit', output=problem)
            return result
        if code != 0:
            raise RuntimeError(f'Container exited with status {code}; no result established.')
        if len(lines) == 1:
            failure = json.loads(lines[0])
            if isinstance(failure, dict) and failure.get('kind') == 'environment-error':
                result.update(execution='not-started', error=failure.get('error'))
                return result
        if len(lines) != 2 or result['runtime'] is None:
            raise ValueError('Invalid worker output; no grade established.')
        response = json.loads(lines[1])
        if not isinstance(response, dict) or not isinstance(response.get('output', ''), str):
            raise ValueError('Worker response must be an object with text output.')
        if response.get('kind') == 'environment-error':
            result.update(execution='not-started', error=response.get('error'), output=response.get('output', ''))
            return result
        runtime = result['runtime']
        if runtime.get('library') != activity.library or runtime['libraries'].get(activity.library) != activity.library_version:
            raise ValueError('Reported runtime differs from the declared activity.')
        result['output'] = response.get('output', '')
        kind = response.get('kind')
        if kind == 'output-limit':
            result['status'] = 'execution-limit'
        elif kind == 'runtime-error':
            result.update(status='runtime-error', execution='completed', error=response['error'])
        elif kind == 'value':
            value = response['value']
            # ponytail: exact scalar equality; richer outputs need a separately declared evaluator.
            result.update(status='checked', execution='completed', value=value,
                          success=type(value) is type(expected) and value == expected)
        else:
            raise ValueError('Unknown worker response; no grade established.')
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError) as error:
        result.update(status='environment-error', success=None,
                      error={'type':type(error).__name__, 'message':str(error)[:2048]})
    return result


def require_current(observation: dict, work: dict, *, branch_id: str, activity: dict, timeout: float = 10,
                    evaluation=None) -> None:
    activity = Activity.model_validate(activity)
    binding = _binding(work, branch_id, activity, timeout, evaluation)
    legacy = binding | {'checker_sha256': DISTINCT_COUNT_SOURCE}
    if observation['binding'] != binding and not (evaluation is None and observation['binding'] == legacy):
        raise ValueError('Observation is stale or belongs to another source, activity, evaluation, image or checker.')
    runtime = observation['runtime']
    if observation['runtime_sha256'] != (_digest(runtime) if runtime is not None else None):
        raise ValueError('Runtime fingerprint changed.')
    if runtime is not None and runtime.get('image_id') != activity.image_id:
        raise ValueError('Runtime image differs from the activity.')
