"""Lossless prompt encoding. Never drops an event, code string, output or warning."""
from collections import Counter
from copy import deepcopy
import json

VERSION = "session-evidence.compact.v1"
INSTRUCTIONS = """The evidence below uses a lossless compact representation.
For each timeline record, apply record_defaults first, then the record's fields.
An object {\"$text\": N} means the exact string at text_table[N]; it is not a summary.
warning_codes [record_index, template_index] means timeline[record_index].id + ': ' +
warning_templates[template_index]. A code [-1, text] is a literal warning.
Every event, timestamp, ID, sequence, explicit link, code/output and warning is retained.
Return ORIGINAL event IDs in the assessment, never table indexes or $text references.
"""


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def pack(evidence):
    document = deepcopy(evidence)
    timeline = document.pop("timeline")
    defaults = {k: v for k, v in timeline[0].items() if k != "id" and all(k in r and r[k] == v for r in timeline)} if timeline else {}
    records = [{k: v for k, v in r.items() if k not in defaults} for r in timeline]
    ids = {r["id"]: i for i, r in enumerate(timeline)}
    templates, codes = [], []
    for warning in document.pop("warnings"):
        prefix, sep, suffix = warning.partition(": ")
        if sep and prefix in ids:
            if suffix not in templates: templates.append(suffix)
            codes.append([ids[prefix], templates.index(suffix)])
        else:
            codes.append([-1, warning])
    body = {**document, "record_defaults": defaults, "timeline": records,
            "warning_templates": templates, "warning_codes": codes}
    strings = Counter()
    def count(value):
        if isinstance(value, str) and len(value) >= 96: strings[value] += 1
        elif isinstance(value, list):
            for item in value: count(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key != "id" and not key.endswith(("_id", "_ids")): count(item)
    count(body)
    table = sorted(s for s, n in strings.items() if n > 1 and (n - 1) * len(dumps(s)) > n * 24 + 16)
    lookup = {value: i for i, value in enumerate(table)}
    def encode(value):
        if isinstance(value, str): return {"$text": lookup[value]} if value in lookup else value
        if isinstance(value, list): return [encode(item) for item in value]
        if isinstance(value, dict): return {k: v if k == "id" or k.endswith(("_id", "_ids")) else encode(v) for k, v in value.items()}
        return value
    packed = {"format": VERSION, "text_table": table, "evidence": encode(body)}
    if unpack(packed) != evidence: raise ValueError("Compaction changed evidence")
    return packed


def unpack(packed):
    if packed.get("format") != VERSION: raise ValueError("Unknown compact evidence version")
    table = packed["text_table"]
    def decode(value):
        if isinstance(value, dict):
            if set(value) == {"$text"}: return table[value["$text"]]
            return {k: decode(v) for k, v in value.items()}
        if isinstance(value, list): return [decode(item) for item in value]
        return value
    body = decode(packed["evidence"])
    defaults = body.pop("record_defaults")
    body["timeline"] = [{**defaults, **record} for record in body["timeline"]]
    templates = body.pop("warning_templates")
    body["warnings"] = [code[1] if code[0] == -1 else body["timeline"][code[0]]["id"] + ": " + templates[code[1]] for code in body.pop("warning_codes")]
    return body
