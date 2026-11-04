"""
Wikipedia Quiz Generator - Open Source Day Project Challenge.
Data: Wikimedia Structured Wikipedia Dataset (Kaggle) only.

Run:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from quiz_engine import (
    QUESTION_KINDS,
    generate_quiz,
    load_articles,
    load_articles_from_bytes,
)

st.set_page_config(page_title="Wikipedia Quiz Generator", page_icon="❓", layout="centered")


@st.cache_data(show_spinner="Loading articles…")
def cached_load_path(path, limit, keyword):
    return load_articles(path, limit, keyword)


@st.cache_data(show_spinner="Loading articles…")
def cached_load_bytes(data, limit, keyword):
    return load_articles_from_bytes(data, limit, keyword)


def reset_quiz():
    for key in ("quiz", "idx", "results", "checked"):
        st.session_state.pop(key, None)


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Setup")
    st.caption("Use the Wikimedia Structured Wikipedia dataset from Kaggle (.json / .jsonl).")
    path = st.text_input("Path to dataset file", placeholder="e.g. data/enwiki_sample.jsonl")
    upload = st.file_uploader("…or upload a file", type=["json", "jsonl", "ndjson"])
    keyword = st.text_input("Topic filter (optional)", placeholder="e.g. river, physics, India")
    limit = st.slider("Articles to load", 200, 10000, 2000, step=200)
    kinds = st.multiselect(
        "Question types",
        options=list(QUESTION_KINDS),
        default=list(QUESTION_KINDS),
        format_func=QUESTION_KINDS.get,
    )
    n_questions = st.slider("Questions per quiz", 5, 20, 10)
    start = st.button("Start new quiz", type="primary", use_container_width=True)

st.title("❓ Wikipedia Quiz Generator")
st.caption("Trivia built from the Wikimedia Structured Wikipedia dataset.")

# ---------------------------------------------------------------- start a quiz
if start:
    reset_quiz()
    try:
        if upload is not None:
            articles = cached_load_bytes(upload.getvalue(), limit, keyword)
        elif path.strip():
            articles = cached_load_path(path.strip(), limit, keyword)
        else:
            st.warning("Give a file path or upload a dataset file first.")
            st.stop()
        if not kinds:
            st.warning("Pick at least one question type.")
            st.stop()
        quiz = generate_quiz(articles, n_questions, kinds)
        if not quiz:
            st.error("Could not build questions from this data. Try loading more articles.")
            st.stop()
        st.session_state.update(quiz=quiz, idx=0, results=[], checked=False)
    except FileNotFoundError:
        st.error("File not found. Check the path.")
        st.stop()
    except ValueError as e:
        st.error(str(e) + " Try a larger limit or a broader topic filter.")
        st.stop()

quiz = st.session_state.get("quiz")
if not quiz:
    st.info("Choose a dataset file in the sidebar and press **Start new quiz**.")
    st.stop()

idx, results = st.session_state.idx, st.session_state.results

# ---------------------------------------------------------------- results screen
if idx >= len(quiz):
    score = sum(r["correct"] for r in results)
    st.subheader(f"Final score: {score} / {len(quiz)}")
    st.progress(score / len(quiz))
    df = pd.DataFrame(results)
    df["type"] = df["kind"].map(QUESTION_KINDS)
    by_type = df.groupby("type")["correct"].mean().mul(100).round(0)
    st.markdown("**Accuracy by question type (%)**")
    st.bar_chart(by_type)
    wrong = [r for r in results if not r["correct"]]
    if wrong:
        st.markdown("**Review your mistakes**")
        for r in wrong:
            with st.expander(r["prompt"].splitlines()[0] + " …"):
                st.write(r["prompt"])
                st.write(f"Your answer: **{r['chosen']}**  |  Correct: **{r['answer']}**")
                st.caption(r["explanation"])
                if r["source_url"]:
                    st.link_button("Open article", r["source_url"])
    else:
        st.success("Perfect score!")
    if st.button("Play again"):
        reset_quiz()
        st.rerun()
    st.stop()

# ---------------------------------------------------------------- question screen
q = quiz[idx]
st.progress(idx / len(quiz))
st.markdown(f"**Question {idx + 1} of {len(quiz)}** · {QUESTION_KINDS[q['kind']]}")
st.write(q["prompt"])
choice = st.radio("Your answer", q["options"], index=None, key=f"q{idx}",
                  disabled=st.session_state.checked)

if not st.session_state.checked:
    if st.button("Check answer", disabled=choice is None):
        correct = choice == q["answer"]
        results.append({**q, "chosen": choice, "correct": correct})
        st.session_state.checked = True
        st.rerun()
else:
    last = results[-1]
    if last["correct"]:
        st.success("Correct!")
    else:
        st.error(f"Not quite. The answer is: {q['answer']}")
    st.caption(q["explanation"])
    if q["source_url"]:
        st.link_button("Read the article", q["source_url"])
    label = "Finish" if idx + 1 == len(quiz) else "Next question"
    if st.button(label, type="primary"):
        st.session_state.idx += 1
        st.session_state.checked = False
        st.rerun()

st.caption(f"Score so far: {sum(r['correct'] for r in results)} / {len(results)}")
