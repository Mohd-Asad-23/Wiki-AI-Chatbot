import json
import os
import random
import re

import streamlit as st

st.set_page_config(page_title="WikiQuiz AI", page_icon="🧠", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "quiz_data.json")
GEMINI_MODEL = "gemini-3.5-flash-lite"

# ----------------------------- DESIGN ---------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');
:root { --ink:#172033; --muted:#68758a; --blue:#4263eb; --pale:#f4f7ff; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:linear-gradient(180deg,#f7f9ff 0%,#ffffff 48%,#f8faff 100%); color:var(--ink); }
.block-container { max-width:1050px; padding-top:2rem; padding-bottom:4rem; }
.hero { padding:2.1rem 2.2rem; border-radius:24px; color:white; background:linear-gradient(120deg,#172554 0%,#2846a5 55%,#5875ed 100%); margin-bottom:1.5rem; box-shadow:0 14px 38px rgba(35,62,145,.16); }
.hero-kicker { text-transform:uppercase; letter-spacing:2px; font-size:.76rem; font-weight:800; opacity:.8; }
.hero h1 { font-family:'Space Grotesk',sans-serif; color:white; font-size:2.5rem; line-height:1.15; margin:.45rem 0; }
.hero p { color:#e5eaff; font-size:1.02rem; margin:0; }
.panel { background:white; border:1px solid #e7ebf5; border-radius:18px; padding:1.2rem 1.35rem; box-shadow:0 5px 20px rgba(31,48,90,.045); margin-bottom:1rem; }
.small-label { color:#64748b; font-size:.76rem; font-weight:800; text-transform:uppercase; letter-spacing:1.2px; }
.question-card { background:white; border:1px solid #e4e9f3; border-radius:18px; padding:1.35rem; margin:.7rem 0 1rem; }
div.stButton > button, div.stFormSubmitButton > button { border-radius:12px; font-weight:700; min-height:2.8rem; }
div[data-testid="stMetric"] { background:#f5f7ff; border:1px solid #e6eaff; border-radius:15px; padding:1rem; }
div[data-testid="stProgress"] > div { border-radius:20px; }
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">Wikipedia-powered learning</div>
  <h1>WikiQuiz AI</h1>
  <p>Explore what you know. Challenge what you don't. Learn something new.</p>
</div>
""", unsafe_allow_html=True)


# ----------------------------- DATA -----------------------------------
@st.cache_data
def load_articles():
    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    articles = []
    for item in data:
        raw_question = item.get("question", "")
        parts = raw_question.split("\n", 1)
        abstract = parts[1].strip() if len(parts) > 1 else ""
        title = str(item.get("answer", "")).strip()
        if title and len(abstract) >= 50:
            articles.append({
                "title": title,
                "abstract": abstract,
                "difficulty": str(item.get("difficulty", "Medium")).title(),
            })
    return articles


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [part.strip() for part in parts if 45 <= len(part.strip()) <= 260]


# Expand short, common topic names into their full forms. Matching uses
# whole words, never accidental substrings (for example "ai" in "remain").
TOPIC_ALIASES = {
    "ai": ["artificial intelligence"],
    "ml": ["machine learning"],
    "cs": ["computer science"],
    "isro": ["indian space research organisation", "indian space research organization"],
    "iss": ["international space station"],
}


def find_topic_articles(articles, topic):
    cleaned = re.sub(r"[^a-z0-9 ]", " ", topic.lower()).strip()
    terms = [cleaned] + TOPIC_ALIASES.get(cleaned, [])
    matches = []
    for article in articles:
        title = article["title"].lower()
        abstract = article["abstract"].lower()
        for term in terms:
            # Exact phrase / whole-word matching prevents false positives.
            pattern = r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])"
            if re.search(pattern, title) or re.search(pattern, abstract):
                matches.append(article)
                break
    return matches


def build_reading_questions(articles, count, difficulty):
    pool = [
        article for article in articles
        if difficulty == "All" or article["difficulty"] == difficulty
    ]
    if len(pool) < 4:
        return []

    random.shuffle(pool)
    generated = []
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
        distractors = list(dict.fromkeys(f for f in distractors if f != correct_fact))
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
            "explanation": f"This statement is supported by the Wikipedia summary for {article['title']}.",
        })
    return generated


def generate_with_gemini(source_articles, topic, difficulty, count, api_key):
    from google import genai
    from google.genai import types

    context = "\n\n".join(
        f"ARTICLE TITLE: {a['title']}\nARTICLE SUMMARY: {a['abstract']}"
        for a in source_articles[:10]
    )
    prompt = f"""
You are an expert quiz setter. Create exactly {count} high-quality multiple-choice
questions about the topic: "{topic}".
Difficulty: {difficulty}.

STRICT TOPIC RULES:
- Every question must test the requested topic "{topic}" directly.
- Use only the source articles below. Do not introduce other topics or outside facts.
- If a source only mentions the topic in passing, do not make a question from it.
- Do not create generic questions that could fit any subject.
- Do not ask "which article is this?".
- Questions must test concepts, understanding, implications, or specific facts.
- Every question must have exactly 4 distinct options and one correct answer.
- Make distractors plausible but clearly incorrect based on the source.
- Explanations must briefly justify the correct answer using the source.
Return JSON only: an array with keys "question", "options", "answer",
"explanation", and "source_title". The answer must exactly match one option.

SOURCE ARTICLES:
{context}
"""
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.25,
            max_output_tokens=3000,
        ),
    )
    generated = json.loads(response.text or "[]")
    if not isinstance(generated, list):
        raise ValueError("Gemini returned an unexpected response format.")

    valid = []
    for item in generated:
        if not isinstance(item, dict):
            continue
        options = item.get("options", [])
        answer = item.get("answer")
        question_text = item.get("question")
        if (
            isinstance(question_text, str) and question_text.strip()
            and isinstance(options, list) and len(options) == 4
            and all(isinstance(option, str) and option.strip() for option in options)
            and len(set(options)) == 4
            and isinstance(answer, str) and answer in options
        ):
            valid.append({
                "question": question_text.strip(),
                "options": options,
                "answer": answer,
                "explanation": item.get("explanation", "Based on the selected Wikipedia source."),
                "title": item.get("source_title", source_articles[0]["title"]),
            })

    if len(valid) != count:
        raise ValueError(
            f"Gemini returned {len(valid)} valid questions out of {count}. "
            "Please try a smaller number of questions."
        )
    return valid


# ----------------------------- LOAD -----------------------------------
try:
    articles = load_articles()
except FileNotFoundError:
    st.error("quiz_data.json is missing. Keep it in the same folder as app.py.")
    st.stop()
except (json.JSONDecodeError, ValueError) as error:
    st.error(f"Could not read quiz_data.json: {error}")
    st.stop()

if not articles:
    st.error("No usable Wikipedia summaries were found.")
    st.stop()


# ----------------------------- QUIZ SETUP -----------------------------
st.markdown('<div class="panel"><div class="small-label">Build your quiz</div>', unsafe_allow_html=True)
left, middle, right = st.columns([1.5, 1, 1])
with left:
    mode = st.selectbox(
        "Quiz mode",
        ["Gemini AI quiz", "Reading comprehension", "Identify the Wikipedia article"],
    )
    topic = st.text_input(
        "Your topic",
        placeholder="Try: artificial intelligence, geography, space...",
        disabled=(mode != "Gemini AI quiz"),
    )
with middle:
    difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard", "All"])
with right:
    count = st.selectbox("Questions", [3, 5, 7, 10], index=1)
st.markdown('</div>', unsafe_allow_html=True)

if mode == "Gemini AI quiz":
    st.caption("Gemini uses matching Wikipedia summaries only. If your topic is not in the current dataset, the app will tell you instead of giving unrelated questions.")
    if topic.strip():
        matched = find_topic_articles(articles, topic.strip())
        if matched:
            st.success(f"Topic match found: {len(matched)} relevant source article(s).")
        else:
            st.warning("This topic is not currently covered by the available Wikipedia dataset. Try a topic shown in the article list or add more source data.")
            with st.expander("See available article topics"):
                st.write(", ".join(sorted(article["title"] for article in articles)))

generate = st.button("✨ Generate my quiz", type="primary", use_container_width=True)

if generate:
    try:
        if mode == "Gemini AI quiz":
            if not topic.strip():
                st.error("Please enter a topic first.")
                st.stop()

            matched_articles = find_topic_articles(articles, topic.strip())
            if not matched_articles:
                st.error("No matching source articles found. I won't generate unrelated questions. Try a topic from the available article list.")
                st.stop()

            api_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", ""))
            if not api_key:
                st.error("Gemini API key is not configured. Add GEMINI_API_KEY in Streamlit Secrets.")
                st.stop()

            # Apply difficulty selection before sending the source to Gemini.
            if difficulty != "All":
                difficulty_matches = [a for a in matched_articles if a["difficulty"] == difficulty]
                if difficulty_matches:
                    matched_articles = difficulty_matches

            with st.spinner("Creating topic-focused questions with Gemini..."):
                quiz = generate_with_gemini(
                    matched_articles, topic.strip(), difficulty, count, api_key
                )

        elif mode == "Reading comprehension":
            quiz = build_reading_questions(articles, count, difficulty)
        else:
            with open(DATA_FILE, encoding="utf-8") as file:
                raw_data = json.load(file)
            source = [
                item for item in raw_data
                if difficulty == "All" or str(item.get("difficulty", "")).title() == difficulty
            ]
            quiz = random.sample(source, min(count, len(source))) if source else []

        if not quiz:
            st.error("Not enough source material for this selection. Try another difficulty or fewer questions.")
            st.stop()

        st.session_state.quiz = quiz
        st.session_state.mode = mode
        st.session_state.submitted = False
        st.session_state.answers = {}
        st.session_state.topic = topic.strip() if mode == "Gemini AI quiz" else ""
        st.rerun()

    except Exception as error:
        st.error(f"Quiz generation failed: {error}")
        st.info("Gemini did not switch to another quiz mode. Your selected topic has been kept.")
        st.stop()


# ----------------------------- QUIZ VIEW ------------------------------
quiz = st.session_state.get("quiz")
if not quiz:
    st.markdown("""
    <div class="panel" style="text-align:center;padding:2.3rem 1.5rem;">
      <div style="font-size:2.4rem;">🎯</div>
      <h3 style="margin:.5rem 0;">Your next challenge starts here</h3>
      <p style="color:#68758a;">Choose a mode, enter a topic, and generate your quiz.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown(
    f'<div class="panel"><div class="small-label">Your quiz</div><h3 style="margin:.25rem 0;">{st.session_state.mode}</h3><span style="color:#68758a;">{len(quiz)} questions · {st.session_state.get("topic") or "Wikipedia knowledge"}</span></div>',
    unsafe_allow_html=True,
)

if not st.session_state.get("submitted", False):
    with st.form("quiz_form"):
        answers = {}
        for index, question in enumerate(quiz):
            st.markdown(f'<div class="question-card"><div class="small-label">QUESTION {index + 1} OF {len(quiz)}</div></div>', unsafe_allow_html=True)
            if st.session_state.mode == "Reading comprehension":
                with st.expander(f"Read passage: {question['title']}", expanded=(index == 0)):
                    st.write(question["passage"])
            elif st.session_state.mode == "Identify the Wikipedia article":
                st.write(question.get("question", ""))
            else:
                st.write(question["question"])
                st.caption(f"Source: {question.get('title', 'Wikipedia')}")
            answers[index] = st.radio(
                "Choose your answer",
                question["options"],
                index=None,
                key=f"answer_{index}",
                label_visibility="collapsed",
            )
            st.divider()
        submitted = st.form_submit_button("Submit answers", type="primary", use_container_width=True)

    if submitted:
        st.session_state.submitted = True
        st.session_state.answers = answers
        st.rerun()

else:
    saved = st.session_state.answers
    score = sum(saved.get(i) == question["answer"] for i, question in enumerate(quiz))
    percentage = round(score / len(quiz) * 100)
    st.markdown("### Your result")
    a, b, c = st.columns(3)
    a.metric("Score", f"{score}/{len(quiz)}")
    b.metric("Accuracy", f"{percentage}%")
    c.metric("Correct", f"{score} answers")
    st.progress(percentage / 100)

    if percentage >= 80:
        st.success("Excellent work! You have a strong understanding of this topic.")
    elif percentage >= 50:
        st.info("Good effort. Review the explanations and try again.")
    else:
        st.warning("Keep practising. Read the explanations and give it another try.")

    st.markdown("### Answer review")
    for index, question in enumerate(quiz):
        chosen = saved.get(index)
        if chosen == question["answer"]:
            st.success(f"Q{index + 1}. Correct")
        else:
            st.error(f"Q{index + 1}. Incorrect")
            st.write(f"Your answer: {chosen or 'Not answered'}")
            st.write(f"Correct answer: {question['answer']}")
        if question.get("explanation"):
            st.caption(question["explanation"])
        st.divider()

    if st.button("↻ Create another quiz", type="primary", use_container_width=True):
        for key in ("quiz", "mode", "submitted", "answers", "topic"):
            st.session_state.pop(key, None)
        st.rerun()

st.caption("Source material: Wikipedia article summaries · AI question generation: Gemini")
