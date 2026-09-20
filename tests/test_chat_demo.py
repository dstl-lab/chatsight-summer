"""The teammate demo replays invented outcomes without credentials or providers."""
import importlib.util
import shutil

import pytest

from src.agents import chat_policy_pair, chat_student, chat_workspace, notebook_student
from tests.test_chat_student import files


def test_offline_demo_reopens_after_copy_and_never_overwrites(tmp_path, monkeypatch):
    assert importlib.util.find_spec('src.agents.chat_demo'), 'The portable demo is missing'
    from src.agents.chat_demo import create

    def forbidden(*_args, **_kwargs):
        pytest.fail('The authored demo must never construct or call a provider')

    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setattr(notebook_student.llm, 'make_generate', forbidden)
    monkeypatch.setattr(chat_workspace, '_generate', forbidden)
    folder = tmp_path / 'demo'
    saved = create(folder)
    assert saved == chat_policy_pair.show(folder / 'comparison')
    assert chat_student.show(folder / 'source')['decisions'] == 1
    for name, status in [('a', 'awaiting-tutor'), ('b', 'no-reply')]:
        condition = saved['conditions'][name]
        assert not condition['error']
        assert 'Authored offline demo' in condition['policy']
        assert condition['snapshot']['status'] == status
        assert condition['snapshot']['decisions_remaining'] == 0
        assert 'scripted' in condition['snapshot']['dialogue'][0]['text']
        assert condition['policy'] in condition['history']
    assert len(list(folder.rglob('receipt.json'))) == 2
    before = files(folder)
    with pytest.raises(FileExistsError):
        create(folder)
    assert files(folder) == before
    copied = tmp_path / 'another-checkout' / 'demo'
    shutil.copytree(folder, copied)
    assert chat_policy_pair.show(copied / 'comparison') == saved
    assert files(copied) == before
