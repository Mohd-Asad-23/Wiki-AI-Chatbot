"""
Tests for quiz_engine using small SYNTHETIC records shaped like the Wikimedia
Structured Wikipedia JSON. These exist only to check the code; the app itself
uses only the real Wikimedia dataset.

Run:  python test_engine.py
"""

import io
import json

from quiz_engine import (
    extract_fields, generate_quiz, load_from_handle, good_sentences, clean,
)

COUNTRIES = ["Aldoria", "Brenmark", "Calvera", "Dunhollow", "Estovia", "Farrowen",
             "Gelmora", "Hartsvale", "Ilvania", "Jorathen", "Kestrel Bay", "Lunmere"]


def fake_article(i, name):
    return {
        "name": name,
        "url": f"https://example.org/wiki/{name.replace(' ', '_')}",
        "description": f"Sovereign nation number {i} in the test world",
        "abstract": (
            f"{name} is a fictional country used for testing the quiz engine. "
            f"It was founded in {1800 + i} and its capital city is called Capital{i}. "
            f"The population of {name} is about {i + 2} million people today."
        ),
        "infobox": [{
            "type": "infobox", "name": "Infobox country",
            "has_parts": [{"type": "section", "has_parts": [
                {"type": "field", "name": "Capital", "value": f"Capital{i}"},
                {"type": "field", "name": "Founded", "value": str(1800 + i)},
            ]}],
        }],
    }


POOL = [fake_article(i, n) for i, n in enumerate(COUNTRIES)]


def test_clean_and_sentences():
    assert clean("Hello[1]  world [citation needed]") == "Hello world"
    assert good_sentences("Short. " + "x" * 60 + ".")


def test_extract_fields():
    fields = extract_fields(POOL[0]["infobox"])
    assert ("Capital", "Capital0") in fields and ("Founded", "1800") in fields


def test_generate_all_kinds():
    quiz = generate_quiz(POOL, n=12, seed=1)
    assert len(quiz) == 12
    kinds = {q["kind"] for q in quiz}
    assert kinds == {"blank", "description", "infobox", "tf"}, kinds
    for q in quiz:
        assert q["answer"] in q["options"]
        assert len(set(q["options"])) == len(q["options"])
        if q["kind"] != "tf":
            assert len(q["options"]) == 4
        if q["kind"] == "blank":
            assert "_____" in q["prompt"] and q["answer"] not in q["prompt"].split("“", 1)[1]


def test_true_false_balance():
    quiz = generate_quiz(POOL, n=30, kinds=["tf"], seed=3)
    answers = {q["answer"] for q in quiz}
    assert answers == {"True", "False"}


def test_loader_jsonl_and_array_and_keyword():
    jsonl = "\n".join(json.dumps(a) for a in POOL) + "\nnot json\n"
    assert len(load_from_handle(io.StringIO(jsonl))) == len(POOL)
    assert len(load_from_handle(io.StringIO(json.dumps(POOL)))) == len(POOL)
    assert len(load_from_handle(io.StringIO(jsonl), keyword="aldoria")) == 1
    assert len(load_from_handle(io.StringIO(jsonl), limit=3)) == 3


def test_too_small_pool():
    try:
        generate_quiz(POOL[:3], n=5)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok ", name)
    print("All tests passed.")
