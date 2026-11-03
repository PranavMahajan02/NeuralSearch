"""scripts/eval_search.py --aliases: real names are used for querying and judging,
but only aliases (or public names) are ever written to the report."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "eval_search.py"


@pytest.fixture
def harness():

    spec = importlib.util.spec_from_file_location("eval_search", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


QUERIES = [
    {"query": "receipt query 01", "expected": ["fee-receipt-01.pdf"]},
    {"query": "dog", "expected": ["Golden_Retriever.webp"], "visual": True},
    {"query": "xqzv", "negative": True},
]
MAPPING = {
    "files": {"fee-receipt-01.pdf": "Real Receipt 123.pdf"},
    "queries": {"receipt query 01": "real receipt 123"},
}


class FakeResponse:
    status_code = 200

    def __init__(self, results, possible=()):
        self._body = {"results": results, "possible_matches": list(possible)}

    def json(self):
        return self._body


def fake_post(sent):

    answers = {
        "real receipt 123": FakeResponse(
            [{"file": "Some Private Name.pdf"}, {"file": "Real Receipt 123.pdf"}],
            possible=[{"file": "Another Private.jpg"}],
        ),
        "dog": FakeResponse([{"file": "Golden_Retriever.webp"}]),
    }

    def post(url, json, headers, timeout):
        sent.append(json["query"])
        return answers.get(json["query"], FakeResponse([]))

    return post


def test_aliases_send_the_real_query_judge_real_names_and_write_only_aliases(harness, monkeypatch):

    sent = []
    monkeypatch.setattr(harness.requests, "post", fake_post(sent))

    report = harness.run("http://x", {}, QUERIES, 0, aliases=harness.Aliases(MAPPING, QUERIES))
    rows = {r["query"]: r for r in report["per_query"]}

    assert "real receipt 123" in sent and "receipt query 01" not in sent
    receipt = rows["receipt query 01"]
    assert receipt["first_relevant_rank"] == 2
    assert receipt["top5"][1] == "fee-receipt-01.pdf"
    assert receipt["top5"][0].startswith("unlisted-") and receipt["top5"][0].endswith(".pdf")
    assert receipt["possible"][0].startswith("unlisted-")
    assert rows["dog"]["top5"] == ["Golden_Retriever.webp"]  # public names stay readable

    dumped = repr(report)
    for private in ("Real Receipt", "real receipt", "Some Private", "Another Private"):
        assert private not in dumped


def test_without_aliases_names_are_used_as_they_are(harness, monkeypatch):

    sent = []
    monkeypatch.setattr(harness.requests, "post", fake_post(sent))
    queries = [{"query": "dog", "expected": ["Golden_Retriever.webp"]}]

    report = harness.run("http://x", {}, queries, 0)

    assert report["per_query"][0]["top5"] == ["Golden_Retriever.webp"]
    assert report["per_query"][0]["first_relevant_rank"] == 1


def test_unlisted_names_are_stable_and_reveal_nothing(harness):

    aliases = harness.Aliases(MAPPING, QUERIES)

    first, second = aliases.display("Private Thing.JPG"), aliases.display("private thing.jpg")
    assert first == second and first.startswith("unlisted-") and first.endswith(".jpg")
    assert "rivate" not in first
