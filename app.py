import json
import os
import random

import streamlit as st

st.set_page_config(
    page_title="WikiQuiz AI",
    page_icon="🧠",
    layout="centered",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "quiz_data.json")

st.title("🧠 WikiQuiz AI")
st.subheader("Learn. Think. Challenge Yourself.")
st.write("Test your knowledge with questions based on Wikipedia article summaries.")

@st.cache_data
def load_questions():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("quiz_data.json must contain a list of questions.")
    return data

try:
    all_questions = load_questions()
except FileNotFoundError:
    st.error("quiz_data.json is missing. Add it to the same GitHub folder as app.py.")
    st.stop()
except (json.JSONDecodeError, ValueError) as error:
    st.error(f"Could not read quiz_data.json: {error}")
    st.stop()

if not all_questions:
    st.error("No questions were found in quiz_data.json.")
    st.stop()

with st.sidebar:
    st.header("Quiz setup")
    difficulty = st.selectbox("Choose difficulty", ["All", "Easy", "Medium", "Hard"])
    filtered_questions = [
        question for question in all_questions
        if difficulty == "All" or question.get("difficulty", "").title() == difficulty
    ]
    st.caption(f"{len(filtered_questions)} questions available")

    if filtered_questions:
        question_count = st.slider(
            "Number of questions",
            min_value=1,
            max_value=len(filtered_questions),
            value=min(5, len(filtered_questions)),
        )
    else:
        question_count = 0

if not filtered_questions:
    st.warning("There are no questions for this difficulty. Please choose another one.")
    st.stop()

if st.button("Start a new quiz", type="primary", use_container_width=True):
    st.session_state.quiz_questions = random.sample(filtered_questions, question_count)
    st.session_state.quiz_submitted = False
    st.session_state.quiz_answers = {}

quiz = st.session_state.get("quiz_questions")

if not quiz:
    st.info("Choose your difficulty and click **Start a new quiz**.")
    st.stop()

st.progress(0 if not st.session_state.get("quiz_submitted", False) else 1)
st.caption(f"{len(quiz)} questions · {difficulty} difficulty")

with st.form("wiki_quiz_form"):
    answers = {}
    for index, question in enumerate(quiz):
        st.markdown(f"### Question {index + 1}")
        st.write(question.get("question", "Question text unavailable"))
        options = question.get("options", [])
        answers[index] = st.radio(
            "Select one answer",
            options,
            index=None,
            key=f"wiki_answer_{index}",
        )
        st.divider()

    submitted = st.form_submit_button("Submit answers", type="primary")

if submitted:
    st.session_state.quiz_submitted = True
    st.session_state.quiz_answers = answers

if st.session_state.get("quiz_submitted", False):
    saved_answers = st.session_state.quiz_answers
    score = sum(
        saved_answers.get(index) == question.get("answer")
        for index, question in enumerate(quiz)
    )
    percentage = round(score / len(quiz) * 100)
    st.success("Quiz completed!")
    col1, col2 = st.columns(2)
    col1.metric("Your score", f"{score}/{len(quiz)}")
    col2.metric("Percentage", f"{percentage}%")
    st.progress(percentage / 100)

    st.markdown("### Answer review")
    for index, question in enumerate(quiz):
        correct_answer = question.get("answer")
        chosen_answer = saved_answers.get(index)
        if chosen_answer == correct_answer:
            st.success(f"Question {index + 1}: Correct")
        else:
            st.error(f"Question {index + 1}: Incorrect")
            st.write(f"Your answer: {chosen_answer or 'Not answered'}")
            st.write(f"Correct answer: {correct_answer}")

    if score == len(quiz):
        st.balloons()
        st.success("Perfect score! Well done.")

    if st.button("Play again"):
        for key in ("quiz_questions", "quiz_submitted", "quiz_answers"):
            st.session_state.pop(key, None)
        st.rerun()

st.caption("Questions are generated from the Wikimedia Structured Contents dataset.")
