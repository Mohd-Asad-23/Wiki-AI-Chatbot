"""
quiz_engine.py - turns Wikimedia Structured Wikipedia articles into quiz questions.

Pure Python (no third-party packages), so it can be tested anywhere, including Colab.

Expected article fields (Wikimedia Structured Contents JSON):
    name         article title
    abstract     lead summary text
    description  short description
    infobox      nested structure holding fact-box data
    url          link to the article
A few alternative names (e.g. "title") are also accepted.
"""

import io
import json
import random
import re

QUESTION_KINDS = {
    "blank": "Fill the blank (which article?)",
    "description": "Match the short description",
    "infobox": "Infobox facts",
    "tf": "True / False",
}

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_REF = re.compile(r"\[\s*(?:\d+|citation needed|note \d+)\s*\]", re.I)
BLANK = "_____"


# --------------------------------------------------------------------------
# Field helpers
# --------------------------------------------------------------------------
def clean(text):
    """Remove reference markers like [1] and collapse whitespace."""
    if not isinstance(text, str):
        return ""
    return re.sub(r"\s+", " ", _REF.sub("", text)).strip()


def get_title(a):
    return clean(a.get("name") or a.get("title") or "")


def get_abstract(a):
    return clean(a.get("abstract") or "")


def get_description(a):
    return clean(a.get("description") or a.get("short_description") or "")


def get_url(a):
    u = a.get("url")
    return u if isinstance(u, str) else ""


def usable(a):
    return isinstance(a, dict) and bool(get_title(a)) and len(get_abstract(a)) >= 80


def good_sentences(text):
    parts = _SENT_SPLIT.split(clean(text))
    return [p for p in parts if 50 <= len(p) <= 250 and p[-1] in ".!?"]


def extract_fields(node, out=None):
    """Walk a (possibly nested) infobox structure and collect (label, value) pairs."""
    if out is None:
        out = []
    if isinstance(node, dict):
        label, value = node.get("name"), node.get("value")
        if isinstance(label, str) and isinstance(value, str):
            label, value = clean(label), clean(value)
            if label and value and len(label) <= 40 and len(value) <= 60:
                out.append((label, value))
        for v in node.values():
            if isinstance(v, (list, dict)):
                extract_fields(v, out)
    elif isinstance(node, list):
        for item in node:
            extract_fields(item, out)
    return out


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def _matches(a, keyword):
    if not keyword:
        return True
    k = keyword.lower()
    return k in get_title(a).lower() or k in get_abstract(a).lower()


def _iter_records(handle):
    """Yield dicts from a text handle holding JSON Lines or one JSON array."""
    first = handle.read(1)
    while first and first.isspace():
        first = handle.read(1)
    if not first:
        return
    if first == "[":
        data = json.loads("[" + handle.read())
        for rec in data:
            yield rec
        return
    rest = handle.readline()
    line = first + rest
    while True:
        line = line.strip()
        if line:
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                pass  # skip a damaged line instead of crashing
        line = handle.readline()
        if not line:
            break


def load_from_handle(handle, limit=3000, keyword="", max_scan=300000):
    articles, scanned = [], 0
    for rec in _iter_records(handle):
        scanned += 1
        if usable(rec) and _matches(rec, keyword):
            articles.append(rec)
        if len(articles) >= limit or scanned >= max_scan:
            break
    return articles


def load_articles(path, limit=3000, keyword=""):
    with open(path, encoding="utf-8") as f:
        return load_from_handle(f, limit, keyword)


def load_articles_from_bytes(data, limit=3000, keyword=""):
    return load_from_handle(io.StringIO(data.decode("utf-8", errors="replace")), limit, keyword)


# --------------------------------------------------------------------------
# Question builders. Each returns a dict or None (the caller retries).
# --------------------------------------------------------------------------
def _question(kind, prompt, options, answer, article, explanation):
    return {
        "kind": kind,
        "prompt": prompt,
        "options": options,
        "answer": answer,
        "source_title": get_title(article),
        "source_url": get_url(article),
        "explanation": explanation,
    }


def _title_in(sentence, title):
    return re.search(re.escape(title), sentence, flags=re.I) is not None


def _other_titles(pool, title, k, rng):
    titles = list({get_title(x) for x in pool if get_title(x).lower() != title.lower()})
    if len(titles) < k:
        return None
    return rng.sample(titles, k)


def make_blank(pool, rng):
    a = rng.choice(pool)
    title = get_title(a)
    candidates = [s for s in good_sentences(get_abstract(a)) if _title_in(s, title)]
    if not candidates:
        return None
    blanked = re.sub(re.escape(title), BLANK, rng.choice(candidates), flags=re.I)
    wrong = _other_titles(pool, title, 3, rng)
    if wrong is None:
        return None
    options = wrong + [title]
    rng.shuffle(options)
    return _question(
        "blank", f"Which article is this about?\n\n“{blanked}”", options, title, a,
        f"The sentence comes from the Wikipedia article “{title}”.",
    )


def make_description(pool, rng):
    a = rng.choice(pool)
    title, desc = get_title(a), get_description(a)
    if not (3 <= len(desc) <= 120) or _title_in(desc, title):
        return None
    wrong = _other_titles(pool, title, 3, rng)
    if wrong is None:
        return None
    options = wrong + [title]
    rng.shuffle(options)
    return _question(
        "description", f"Which article has this short description?\n\n“{desc}”", options, title, a,
        f"“{title}” is described on Wikipedia as: {desc}",
    )


def make_infobox(pool, rng, label_index):
    """label_index maps an infobox label to the list of values seen across the pool."""
    a = rng.choice(pool)
    title = get_title(a)
    fields = [(l, v) for l, v in extract_fields(a.get("infobox")) if v.lower() != title.lower()]
    fields = [(l, v) for l, v in fields if len({x.lower() for x in label_index.get(l, [])}) >= 4]
    if not fields:
        return None
    label, value = rng.choice(fields)
    pool_values = list({x for x in label_index[label] if x.lower() != value.lower()})
    if len(pool_values) < 3:
        return None
    options = rng.sample(pool_values, 3) + [value]
    rng.shuffle(options)
    return _question(
        "infobox", f"In the infobox of “{title}”, what is the value of “{label}”?", options, value, a,
        f"The infobox of “{title}” lists {label}: {value}.",
    )


def make_true_false(pool, rng):
    a = rng.choice(pool)
    title = get_title(a)
    sentences = good_sentences(get_abstract(a))
    if not sentences:
        return None
    sentence = rng.choice(sentences)
    if rng.random() < 0.5:
        return _question(
            "tf", f"True or False?\n\n“{sentence}”", ["True", "False"], "True", a,
            f"This sentence appears in the Wikipedia article “{title}”.",
        )
    if not _title_in(sentence, title):
        return None
    others = _other_titles(pool, title, 1, rng)
    if others is None or _title_in(sentence, others[0]):
        return None
    fake = re.sub(re.escape(title), others[0], sentence, flags=re.I)
    return _question(
        "tf", f"True or False?\n\n“{fake}”", ["True", "False"], "False", a,
        f"False: the original sentence is about “{title}”, not “{others[0]}”.",
    )


def build_label_index(pool):
    index = {}
    for a in pool:
        for label, value in extract_fields(a.get("infobox")):
            index.setdefault(label, []).append(value)
    return index


# --------------------------------------------------------------------------
# Quiz generation
# --------------------------------------------------------------------------
def generate_quiz(pool, n=10, kinds=None, seed=None):
    """Return up to n distinct questions, cycling through the chosen kinds."""
    kinds = list(kinds or QUESTION_KINDS.keys())
    rng = random.Random(seed)
    pool = [a for a in pool if usable(a)]
    if len(pool) < 10:
        raise ValueError("Need at least 10 usable articles to build a quiz.")
    label_index = build_label_index(pool) if "infobox" in kinds else {}

    quiz, seen, attempts = [], set(), 0
    while len(quiz) < n and attempts < n * 200:
        kind = kinds[len(quiz) % len(kinds)]
        attempts += 1
        if kind == "blank":
            q = make_blank(pool, rng)
        elif kind == "description":
            q = make_description(pool, rng)
        elif kind == "infobox":
            q = make_infobox(pool, rng, label_index)
        else:
            q = make_true_false(pool, rng)
        if q is None or q["prompt"] in seen:
            # if one kind keeps failing (e.g. no infobox data) drop it
            if attempts % 60 == 0 and len(kinds) > 1:
                kinds = [k for k in kinds if k != kind] or kinds
            continue
        seen.add(q["prompt"])
        quiz.append(q)
    return quiz
