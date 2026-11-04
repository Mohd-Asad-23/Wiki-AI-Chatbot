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
:root { --ink:#17213b; --muted:#71809b; --primary:#635bdb; --line:#e8eaf5; }
html, body, [class*="css"] { font-family:'DM Sans',sans-serif; }
.stApp { background:radial-gradient(ellipse at 8% 0%,#e9eaff 0%,transparent 32%),linear-gradient(180deg,#f7f8ff 0%,#fff 55%,#f8f9ff 100%); color:var(--ink); }
.block-container { max-width:1120px; padding-top:2.2rem; padding-bottom:4rem; }
.hero { position:relative; overflow:hidden; padding:2.8rem 2.7rem; border:1px solid rgba(255,255,255,.2); border-radius:28px; color:white; background:linear-gradient(115deg,#171b45 0%,#383b91 52%,#7166e8 100%); margin-bottom:1.3rem; box-shadow:0 22px 55px rgba(52,53,130,.20); }
.hero:after { content:""; position:absolute; width:290px; height:290px; border:1px solid rgba(255,255,255,.15); border-radius:50%; right:-65px; top:-115px; box-shadow:0 0 0 28px rgba(255,255,255,.035),0 0 0 58px rgba(255,255,255,.025); }
.hero-kicker { display:inline-block; text-transform:uppercase; letter-spacing:2px; font-size:.72rem; font-weight:800; color:#d9d7ff; background:rgba(255,255,255,.12); border:1px solid rgba(255,255,255,.18); padding:.42rem .75rem; border-radius:30px; }
.hero h1 { font-family:'Space Grotesk',sans-serif; color:white; font-size:clamp(2.4rem,5vw,3.5rem); line-height:1.08; margin:.85rem 0 .55rem; letter-spacing:-1.5px; }
.hero p { color:#e7e8ff; font-size:1.05rem; margin:0; max-width:620px; }
.panel { background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:22px; padding:1.45rem 1.55rem; box-shadow:0 9px 30px rgba(34,43,92,.055); margin-bottom:1.1rem; }
.small-label { color:#7a82a0; font-size:.72rem; font-weight:800; text-transform:uppercase; letter-spacing:1.35px; }
.question-card { background:linear-gradient(110deg,#f1f0ff,#fafaff); border:1px solid #e5e2ff; border-radius:15px; padding:1rem 1.2rem; margin:.7rem 0 .5rem; }
div[data-testid="stSelectbox"] label, div[data-testid="stTextInput"] label { font-weight:700; color:#313b59; }
div[data-testid="stSelectbox"] [data-baseweb="select"] > div, div[data-testid="stTextInput"] input { border-radius:12px; border-color:#dfe3f0; background:#fff; }
div.stButton > button, div.stFormSubmitButton > button { border-radius:13px; font-weight:800; min-height:2.9rem; border:0; transition:all .2s ease; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background:linear-gradient(110deg,#5149c9,#7969ed); box-shadow:0 7px 18px rgba(91,80,205,.2); }
div.stButton > button:hover, div.stFormSubmitButton > button:hover { transform:translateY(-1px); box-shadow:0 9px 22px rgba(70,75,145,.16); }
div[data-testid="stMetric"] { background:linear-gradient(145deg,#f3f2ff,#fff); border:1px solid #e5e3fa; border-radius:18px; padding:1rem 1.15rem; }
div[data-testid="stMetricLabel"] { color:#707b99; font-weight:700; }
div[data-testid="stMetricValue"] { color:#292b69; font-family:'Space Grotesk',sans-serif; }
div[data-testid="stProgress"] > div { border-radius:20px; height:10px; }
div[data-testid="stProgress"] > div > div { background:linear-gradient(90deg,#5149c9,#8b7cf6); border-radius:20px; }
div[data-testid="stRadio"] label { background:#fff; border:1px solid #e7e9f2; border-radius:12px; padding:.55rem .8rem; margin:.25rem 0; transition:border .15s ease; }
div[data-testid="stRadio"] label:hover { border-color:#aaa4ef; }
.stAlert { border-radius:14px; }
hr { border-color:#eceef6; }
/* Extra polish: information cards, quiz progress and small-screen layout */
.stat-strip { display:grid; grid-template-columns:repeat(3,1fr); gap:.8rem; margin:.2rem 0 1.25rem; }
.stat-tile { background:rgba(255,255,255,.88); border:1px solid #e8eaf5; border-radius:16px; padding:.9rem 1rem; box-shadow:0 5px 18px rgba(34,43,92,.035); }
.stat-tile strong { display:block; color:#292b69; font:700 1.25rem 'Space Grotesk',sans-serif; }
.stat-tile span { color:#7a82a0; font-size:.76rem; font-weight:700; }
.quiz-heading { background:linear-gradient(110deg,#27275f,#5c55c7); color:#fff; border-radius:18px; padding:1.2rem 1.4rem; margin:1rem 0; box-shadow:0 10px 25px rgba(70,65,160,.13); }
.quiz-heading h3 { color:#fff; margin:.25rem 0; }
.quiz-heading p { color:#e2e1ff; margin:0; font-size:.9rem; }
.question-card { display:flex; align-items:center; justify-content:space-between; gap:1rem; background:linear-gradient(110deg,#f1f0ff,#fafaff); border:1px solid #e5e2ff; border-radius:15px; padding:1rem 1.2rem; margin:1rem 0 .7rem; }
.question-card .small-label { color:#5c55c7; }
div[data-testid="stRadio"] > div { gap:.35rem; }
div[data-testid="stRadio"] label p { font-weight:500; }
@media (max-width:700px) {
 .block-container { padding:1rem .8rem 2.5rem; }
 .hero { padding:2rem 1.35rem; border-radius:21px; }
 .hero h1 { font-size:2.35rem; }
 .panel { padding:1.1rem; border-radius:18px; }
 .stat-strip { gap:.45rem; }
 .stat-tile { padding:.7rem .55rem; }
 .stat-tile strong { font-size:1rem; }
 .stat-tile span { font-size:.66rem; }
}
/* Guided quiz interaction */
.interaction-note { color:#78819e; font-size:.9rem; margin:.35rem 0 1rem; }
.progress-meta { display:flex; justify-content:space-between; color:#747d9b; font-size:.78rem; font-weight:800; letter-spacing:.7px; margin:.5rem 0 .55rem; }
.answer-hint { color:#858da7; font-size:.8rem; margin:.65rem 0 .35rem; }
.quiz-heading { padding:1.45rem 1.6rem; border-radius:20px; }
.question-topline { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.2rem 0 .75rem; }
.question-badge { display:inline-flex; align-items:center; padding:.42rem .75rem; border-radius:30px; background:#eeedff; color:#5149c9; font-size:.72rem; font-weight:900; letter-spacing:1px; }
.question-prompt { background:linear-gradient(135deg,#f6f5ff,#fbfbff); border:1px solid #e8e6fb; border-radius:18px; padding:1.25rem 1.35rem; margin:.35rem 0 1.1rem; }
.question-prompt h3 { color:#20264a; font:700 clamp(1.15rem,2.5vw,1.45rem) 'Space Grotesk',sans-serif; line-height:1.45; margin:.2rem 0; }
.source-chip { color:#767f9e; font-size:.78rem; font-weight:600; margin-top:.6rem; }
div[data-testid="stRadio"] > label { color:#626d8b; font-size:.82rem; font-weight:800; margin-bottom:.5rem; }
div[data-testid="stRadio"] > div { gap:.55rem; }
div[data-testid="stRadio"] > div > label { background:#fff; border:1.5px solid #e7e9f2; border-radius:14px; padding:.8rem 1rem; margin:0; min-height:52px; transition:all .18s ease; }
div[data-testid="stRadio"] > div > label:hover { border-color:#9d96ed; background:#faf9ff; }
div[data-testid="stRadio"] > div > label[data-checked="true"] { border-color:#7168df; background:#f2f0ff; }
div[data-testid="stRadio"] > div > label p { color:#303957; font-weight:600; line-height:1.4; }
div.stFormSubmitButton > button { min-height:3.1rem; }
div.stFormSubmitButton > button[kind="primary"] { background:linear-gradient(110deg,#5149c9,#7969ed); }
@media (max-width:700px) {
 .question-prompt { padding:1rem; }
 .question-topline { align-items:flex-start; }
 .quiz-heading { padding:1.15rem; }
}
footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="hero-kicker">✦ Wikipedia-powered learning</div>
  <h1>Learn smarter.<br>Quiz yourself.</h1>
  <p>Turn knowledge into a challenge. Explore topics, test your understanding, and discover something new with WikiQuiz AI.</p>
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

st.markdown(f"""
<div class="stat-strip">
  <div class="stat-tile"><strong>{len(articles)}+</strong><span>LEARNING TOPICS</span></div>
  <div class="stat-tile"><strong>3</strong><span>QUIZ EXPERIENCES</span></div>
  <div class="stat-tile"><strong>AI + YOU</strong><span>SMARTER PRACTICE</span></div>
</div>
""", unsafe_allow_html=True)


# ----------------------------- QUIZ SETUP -----------------------------
st.markdown('<div class="panel"><div class="small-label">✦ QUIZ STUDIO</div><h3 style="margin:.35rem 0 1rem;color:#20264a;">Create your learning challenge</h3>', unsafe_allow_html=True)
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
        st.session_state.question_index = 0
        for widget_key in list(st.session_state.keys()):
            if str(widget_key).startswith("interactive_answer_"):
                del st.session_state[widget_key]
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
    <div class="panel" style="text-align:center;padding:3rem 1.5rem;">
      <div style="display:inline-flex;width:66px;height:66px;align-items:center;justify-content:center;border-radius:20px;background:#eeedff;font-size:2rem;">🎯</div>
      <h3 style="margin:1rem 0 .35rem;color:#252957;">Ready when you are</h3>
      <p style="color:#71809b;margin:0;">Choose a quiz mode above, set your difficulty, and create your first challenge.</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown(
    f'<div class="quiz-heading"><div class="small-label" style="color:#d9d7ff;">YOUR CHALLENGE</div><h3>{st.session_state.mode}</h3><p>{len(quiz)} questions &nbsp;·&nbsp; {st.session_state.get("topic") or "Wikipedia knowledge"} &nbsp;·&nbsp; One question at a time</p></div>',
    unsafe_allow_html=True,
)

if not st.session_state.get("submitted", False):
    current_index = st.session_state.get("question_index", 0)
    current_index = max(0, min(current_index, len(quiz) - 1))
    current_question = quiz[current_index]
    saved_answers = st.session_state.get("answers", {})
    progress = (current_index + 1) / len(quiz)

    st.markdown(
        f'<div class="progress-meta"><span>YOUR PROGRESS</span><span>{current_index + 1} OF {len(quiz)}</span></div>',
        unsafe_allow_html=True,
    )
    st.progress(progress)
    st.markdown('<div class="interaction-note">Choose one answer, then continue. You can go back and change previous answers.</div>', unsafe_allow_html=True)

    with st.form(f"interactive_quiz_form_{current_index}"):
        st.markdown(
            f'<div class="question-topline"><span class="question-badge">QUESTION {current_index + 1:02d}</span><span class="small-label">CHOOSE ONE ANSWER</span></div>',
            unsafe_allow_html=True,
        )
        if st.session_state.mode == "Reading comprehension":
            with st.expander(f"📖 Read passage: {current_question['title']}", expanded=True):
                st.write(current_question["passage"])
        if st.session_state.mode == "Identify the Wikipedia article":
            prompt_text = current_question.get("question", "Identify this Wikipedia article.")
            st.markdown(
                f'<div class="question-prompt"><h3>Which Wikipedia article does this describe?</h3></div>',
                unsafe_allow_html=True,
            )
        else:
            prompt_text = current_question["question"]
            source_line = (
                f'<div class="source-chip">SOURCE · {current_question.get("title", "Wikipedia")}</div>'
                if st.session_state.mode == "Gemini AI quiz" else ""
            )
            st.markdown(
                f'<div class="question-prompt"><h3>{prompt_text}</h3>{source_line}</div>',
                unsafe_allow_html=True,
            )

        options = current_question["options"]
        previous_answer = saved_answers.get(current_index)
        default_index = options.index(previous_answer) if previous_answer in options else None
        selected_answer = st.radio(
            "YOUR ANSWER",
            options,
            index=default_index,
            key=f"interactive_answer_{current_index}",
        )
        st.markdown('<div class="answer-hint">You can change your answer before finishing the quiz.</div>', unsafe_allow_html=True)
        previous_col, next_col = st.columns([1, 2])
        with previous_col:
            previous_clicked = st.form_submit_button(
                "← Previous",
                disabled=(current_index == 0),
                use_container_width=True,
            )
        with next_col:
            next_label = "Finish quiz ✓" if current_index == len(quiz) - 1 else "Continue →"
            next_clicked = st.form_submit_button(
                next_label,
                type="primary",
                use_container_width=True,
            )

    if previous_clicked or next_clicked:
        saved_answers[current_index] = selected_answer
        st.session_state.answers = saved_answers
        if previous_clicked:
            st.session_state.question_index = max(0, current_index - 1)
        elif current_index == len(quiz) - 1:
            st.session_state.submitted = True
        else:
            st.session_state.question_index = current_index + 1
        st.rerun()

    answered_count = sum(1 for i in range(len(quiz)) if saved_answers.get(i))
    st.caption(f"{answered_count} of {len(quiz)} answers saved.")
else:
    saved = st.session_state.answers
    score = sum(saved.get(i) == question["answer"] for i, question in enumerate(quiz))
    percentage = round(score / len(quiz) * 100)
    st.markdown('<div class="small-label">QUIZ COMPLETE</div><h2 style="font-family:Space Grotesk,sans-serif;color:#252957;margin:.2rem 0 1rem;">Your performance</h2>', unsafe_allow_html=True)
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

    st.markdown("### Review your answers")
    st.caption("Open each question to see the answer and explanation.")
    for index, question in enumerate(quiz):
        chosen = saved.get(index)
        is_correct = chosen == question["answer"]
        label = "✓" if is_correct else "↗"
        with st.expander(f"{label}  Question {index + 1}: {question['question']}", expanded=not is_correct):
            if is_correct:
                st.success("Correct answer")
            else:
                st.error("Not quite — keep learning!")
                st.write(f"**Your answer:** {chosen or 'Not answered'}")
            st.write(f"**Correct answer:** {question['answer']}")
            if question.get("explanation"):
                st.info(question["explanation"])

    if st.button("↻ Create another quiz", type="primary", use_container_width=True):
        for key in ("quiz", "mode", "submitted", "answers", "topic", "question_index"):
            st.session_state.pop(key, None)
        for widget_key in list(st.session_state.keys()):
            if str(widget_key).startswith("interactive_answer_"):
                del st.session_state[widget_key]
        st.rerun()

st.caption("Source material: Wikipedia article summaries · AI question generation: Gemini")
