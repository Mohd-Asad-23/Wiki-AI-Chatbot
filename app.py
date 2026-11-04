import json
import os
import random
import re
import time

import streamlit as st

st.set_page_config(page_title="WikiQuiz AI", page_icon="🧠", layout="centered")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "quiz_data.json")

st.title("🧠 WikiQuiz AI")
st.subheader("Learn. Think. Challenge Yourself.")
st.write("Create quizzes from Wikipedia knowledge, with an optional Gemini AI mode.")

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
    random.shuffle(pool)

    # Use each article only once in a quiz to avoid repeated topics.
    for article in pool:
        if len(generated) >= count:
            break

        facts = sentences(article["abstract"])
        if not facts:
            continue

        correct_fact = random.choice(facts)
        distractors = []
        for other in pool:
            if other["title"] != article["title"]:
                distractors.extend(sentences(other["abstract"]))

        # Keep answer choices distinct and avoid repeating the correct answer.
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

def generate_with_gemini(articles, topic, difficulty, count, api_key):
    from google import genai
    from google.genai import types

    matching = [
        a for a in articles
        if topic.lower() in a["title"].lower() or topic.lower() in a["abstract"].lower()
    ]
    if not matching:
        available_topics = ", ".join(a["title"] for a in articles[:12])
        raise ValueError(
            f"No matching article was found for '{topic}'. "
            f"Try a topic related to these available articles: {available_topics}."
        )

    source_articles = matching[:12]
    context = "\n\n".join(
        f"Article: {a['title']}\nSummary: {a['abstract']}" for a in source_articles[:12]
    )

    prompt = f"""
You are a careful educational quiz writer. Create exactly {count} multiple-choice questions.
Topic requested: {topic}
Difficulty: {difficulty}

Use ONLY the source summaries below. Do not invent facts or use outside knowledge.
Make questions that test understanding, concepts, cause/effect, comparisons, or applications.
Avoid simple "which article is this?" questions.
Each question must have exactly four concise options and one unambiguous correct answer.
Return valid JSON only, as an array of objects with these keys:
"question", "options", "answer", "explanation", "source_title".
The "options" value must be an array of four strings. The "answer" must exactly match one option.
If the source material is insufficient for the requested topic, create questions only from supported information.

SOURCE SUMMARIES:
{context}
"""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.5,
            max_output_tokens=5000,
        ),
    )
    generated = json.loads(response.text)
    if not isinstance(generated, list):
        raise ValueError("Gemini returned an unexpected response format.")

    valid = []
    for item in generated:
        options = item.get("options", [])
        answer = item.get("answer")
        if (
            isinstance(item.get("question"), str)
            and isinstance(options, list)
            and len(options) == 4
            and all(isinstance(option, str) and option.strip() for option in options)
            and len(set(options)) == 4
            and isinstance(answer, str)
            and answer in options
        ):
            valid.append({
                "question": item["question"],
                "options": options,
                "answer": answer,
                "explanation": item.get("explanation", "Generated from the supplied Wikipedia summaries."),
                "title": item.get("source_title", "Wikipedia source"),
            })
    if not valid:
        raise ValueError("Gemini did not return valid questions. Try another topic.")
    return valid

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
        ["Gemini AI quiz", "Reading comprehension", "Identify the Wikipedia article"],
    )
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "All"])
    topic = st.text_input("Topic for Gemini", placeholder="e.g. sports, geography, science")
    count = st.slider("Number of questions", 1, 10, 5)
    start = st.button("Generate quiz", type="primary", use_container_width=True)

if start:
    try:
        if mode == "Gemini AI quiz":
            api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
            if not api_key:
                st.error("Gemini API key is not configured yet. Add GEMINI_API_KEY in Streamlit app secrets.")
                st.stop()
            if not topic.strip():
                st.error("Enter a topic for your Gemini quiz.")
                st.stop()
            transient_error = None
            with st.spinner("Gemini is creating your questions..."):
                for attempt in range(3):
                    try:
                        quiz = generate_with_gemini(
                            articles, topic.strip(), difficulty, count, api_key
                        )
                        transient_error = None
                        break
                    except Exception as error:
                        error_text = str(error).lower()
                        is_temporary = any(
                            marker in error_text
                            for marker in ("503", "unavailable", "429", "resource_exhausted", "500", "504", "deadline")
                        )
                        if not is_temporary:
                            raise
                        transient_error = error
                        if attempt < 2:
                            time.sleep(2 ** (attempt + 1))

            if transient_error is not None:
                quiz = build_reading_questions(articles, count, "All")
                if quiz:
                    mode = "Reading comprehension"
                    st.warning(
                        "Gemini is temporarily busy after 3 attempts. "
                        "We've switched to the built-in reading-comprehension quiz so you can continue."
                    )
                else:
                    raise RuntimeError(
                        "Gemini is temporarily unavailable, and the built-in fallback quiz "
                        "could not be created. Please try again in a few minutes."
                    ) from transient_error
        elif mode == "Reading comprehension":
            quiz = build_reading_questions(articles, count, difficulty)
        else:
            with open(DATA_FILE, encoding="utf-8") as file:
                raw_data = json.load(file)
            source = [
                item for item in raw_data
                if difficulty == "All" or item.get("difficulty", "").title() == difficulty
            ]
            quiz = random.sample(source, min(count, len(source))) if source else []

        if not quiz:
            st.error("Could not create a quiz from the available data. Try another difficulty.")
            st.stop()
        st.session_state.quiz = quiz
        st.session_state.mode = mode
        st.session_state.submitted = False
        st.session_state.answers = {}
    except Exception as error:
        st.error(f"Quiz generation failed: {error}")
        st.stop()

quiz = st.session_state.get("quiz")
if not quiz:
    st.info("Choose a question style and click **Generate quiz**.")
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
        elif st.session_state.mode == "Identify the Wikipedia article":
            st.write(question.get("question", ""))
        else:
            st.write(question["question"])
            st.caption(f"Source: {question.get('title', 'Wikipedia')}")
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

st.caption("Wikipedia summaries provide the source material. Gemini AI generates the AI quiz questions.")
