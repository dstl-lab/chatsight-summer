from src.eval.routing import route_audit, vote_entropy
from src.labeling.draft import MessageLabels
from src.labeling.llm import gen_config

from pydantic import BaseModel


def _run(verdicts: dict[int, bool]):
    return [MessageLabels(chatlog_id=1, message_index=i,
                          labels={"x": v}, rationales={"x": "r"})
            for i, v in verdicts.items()]


def test_vote_entropy_orders_uncertain_first():
    # msg 0: 5/5 yes (entropy 0); msg 1: 3/5 yes; msg 2: gets 2/5
    runs = [_run({0: True, 1: True, 2: True}),
            _run({0: True, 1: True, 2: True}),
            _run({0: True, 1: True, 2: False}),
            _run({0: True, 1: False, 2: False}),
            _run({0: True, 1: False, 2: False})]
    ent = vote_entropy(runs)
    assert ent[(1, 0)]["max_entropy"] == 0.0
    assert ent[(1, 1)]["max_entropy"] == ent[(1, 2)]["max_entropy"] > 0.9
    picked = route_audit(ent, n=2)
    assert (1, 0) not in picked
    assert set(picked) == {(1, 1), (1, 2)}


def test_gen_config_temperature_only_when_asked():
    class M(BaseModel):
        x: bool

    assert "temperature" not in gen_config(M)
    assert gen_config(M, temperature=0.7)["temperature"] == 0.7
