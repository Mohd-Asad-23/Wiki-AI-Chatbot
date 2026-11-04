import json
import os
import random
import re

import streamlit as st

st.set_page_config(page_title="WikiQuiz AI", page_icon="🧠", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "quiz_data.json")

st.title("🧠 WikiQuiz AI")
st.subheader("Learn. Think. Challenge Yourself.")
st.write("Explore Wikipedia knowledge through article-based quizzes.")

@st.cache_data
def load_articles():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    articles = []
    for item in data:
        raw_question = item.get("question", "")
        parts = raw_question.split("\n", 1)
        abstract = parts[1].strip() if len(parts) > 1 else ""
        title = item.get("answer", "").strip()
        if title and len(abstract) >= 50:
            articles.append({
                "title": title,
                "abstract": abstract,
                "difficulty": item.get("difficulty", "Medium").title(),
            })
    return articles

def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if 45 <= len(part.strip()) <= 260]

def build_reading_questions(articles, count, difficulty):
    pool = [
        article for article in articles
        if difficulty == "All" or article["difficulty"] == difficulty
    ]
    if len(pool) < 4:
        return []

    generated = []
    attempts = 0
    while len(generated) < count and attempts < count * 30:
        attempts += 1
        article = random.choice(pool)
        facts = sentences(article["abstract"])
        if not facts:
            continue

        correct_fact = random.choice(facts)
        distractors = []
        for other in pool:
            if other["title"] == article["title"]:
                continue
            distractors.extend(sentences(other["abstract"]))

        distractors = list(dict.fromkeys(
            fact for fact in distractors if fact != correct_fact
        ))
        if len(distractors) < 3:
            continue

        options = random.sample(distractors, 3) + [correct_fact]
        random.shuffle(options)
        generated.append({
            "title": article["title"],
            "passage": article["abstract"],
            "question": "Which statement is supported by the passage?",
            "options": options,
            "answer": correct_fact,
            "explanation": f"This statement is taken from the Wikipedia summary for {article['title']}.",
        })
    return generated

try:
    articles = load_articles()
except FileNotFoundError:
    st.error("quiz_data.json is missing. Keep it in the same GitHub folder as app.py.")
    st.stop()
except (json.JSONDecodeError, ValueError) as error:
    st.error(f"Could not read quiz_data.json: {error}")
    st.stop()

if not articles:
    st.error("No usable article summaries were found in quiz_data.json.")
    st.stop()

with st.sidebar:
    st.header("Quiz setup")
    mode = st.selectbox(
        "Question style",
        ["Reading comprehension", "Identify the Wikipedia article"],
    )
    difficulty = st.selectbox("Difficulty", ["All", "Easy", "Medium", "Hard"])
    available = [
        article for article in articles
        if difficulty == "All" or article["difficulty"] == difficulty
    ]
    st.caption(f"{len(available)} articles available")
    count = st.slider("Number of questions", 1, max(1, min(10, len(available))), min(5, max(1, len(available))))
    start = st.button("Start new quiz", type="primary", use_container_width=True)

if start:
    if mode == "Reading comprehension":
        quiz = build_reading_questions(articles, count, difficulty)
    else:
        source = [
            item for item in json.load(open(DATA_FILE, encoding="utf-8"))
            if difficulty == "All" or item.get("difficulty", "").title() == difficulty
        ]
        quiz = random.sample(source, min(count, len(source))) if source else []

    st.session_state.quiz = quiz
    st.session_state.mode = mode
    st.session_state.submitted = False
    st.session_state.answers = {}

quiz = st.session_state.get("quiz")
if not quiz:
    st.info("Choose a question style and difficulty, then click **Start new quiz**.")
    st.stop()

st.markdown(f"**Question style:** {st.session_state.mode}")
with st.form("quiz_form"):
    answers = {}
    for index, question in enumerate(quiz):
        st.markdown(f"### Question {index + 1}")
        if st.session_state.mode == "Reading comprehension":
            st.caption(f"Article: {question['title']}")
            with st.expander("Read the Wikipedia passage", expanded=True):
                st.write(question["passage"])
            st.write(question["question"])
        else:
            st.write(question["question"])
        answers[index] = st.radio(
            "Choose one answer",
            question["options"],
            index=None,
            key=f"answer_{index}",
        )
        st.divider()
    submitted = st.form_submit_button("Submit quiz", type="primary")

if submitted:
    st.session_state.submitted = True
    st.session_state.answers = answers

if st.session_state.get("submitted", False):
    saved = st.session_state.answers
    score = sum(saved.get(i) == question["answer"] for i, question in enumerate(quiz))
    percentage = round(score / len(quiz) * 100)
    st.success("Quiz completed!")
    col1, col2 = st.columns(2)
    col1.metric("Your score", f"{score}/{len(quiz)}")
    col2.metric("Percentage", f"{percentage}%")
    st.progress(percentage / 100)

    st.markdown("### Answer review")
    for index, question in enumerate(quiz):
        chosen = saved.get(index)
        if chosen == question["answer"]:
            st.success(f"Question {index + 1}: Correct")
        else:
            st.error(f"Question {index + 1}: Incorrect")
            st.write(f"Your answer: {chosen or 'Not answered'}")
            st.write(f"Correct answer: {question['answer']}")
        if question.get("explanation"):
            st.caption(question["explanation"])

    if score == len(quiz):
        st.balloons()
        st.success("Perfect score!")

    if st.button("Play again"):
        for key in ("quiz", "mode", "submitted", "answers"):
            st.session_state.pop(key, None)
        st.rerun()

st.caption("Built from article summaries in the Wikimedia Structured Contents dataset.")
