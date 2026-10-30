"""
study_planner_web/app.py

터미널 메뉴 대신 브라우저 화면으로 보는 커리큘럼 추천 프로그램.
로직은 기존 CLI 버전(main.py)과 동일하게: curricula.json을 읽어 목표별 단계를 보여주고,
체크박스로 완료 표시를 하면 progress.json에 즉시 저장한다.

실행법:
1) pip install -r requirements.txt
2) streamlit run app.py
"""

import json
import os

import streamlit as st

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULA_PATH = os.path.join(BASE_DIR, "data", "curricula.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "data", "progress.json")
XP_PATH = os.path.join(BASE_DIR, "data", "xp.json")
XP_PER_LEVEL = 150
XP_PER_STEP = 20
XP_PER_QUIZ_CORRECT = 10


def load_curricula():
    with open(CURRICULA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    if not os.path.exists(PROGRESS_PATH):
        return {}
    with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress):
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def save_curricula(curricula):
    with open(CURRICULA_PATH, "w", encoding="utf-8") as f:
        json.dump(curricula, f, ensure_ascii=False, indent=2)


def load_xp():
    if not os.path.exists(XP_PATH):
        return {"total_xp": 0}
    with open(XP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_xp(xp_state):
    with open(XP_PATH, "w", encoding="utf-8") as f:
        json.dump(xp_state, f, ensure_ascii=False, indent=2)


def compute_level_info(total_xp):
    """총 XP로부터 (레벨, 현재 레벨 안에서의 XP, 레벨업까지 필요한 XP)를 계산."""
    level = total_xp // XP_PER_LEVEL + 1
    xp_into_level = total_xp % XP_PER_LEVEL
    return level, xp_into_level, XP_PER_LEVEL


def add_xp(amount):
    """XP를 더하거나(완료 체크) 빼고(체크 해제), 레벨이 올랐으면 축하 효과를 띄운다."""
    xp_state = st.session_state.xp_state
    old_level, _, _ = compute_level_info(xp_state["total_xp"])
    xp_state["total_xp"] = max(0, xp_state["total_xp"] + amount)
    save_xp(xp_state)
    new_level, _, _ = compute_level_info(xp_state["total_xp"])
    if new_level > old_level:
        st.balloons()


st.set_page_config(page_title="학습 커리큘럼 추천", page_icon="🧭", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@600;700&display=swap');

html, body, [class*="css"] {
  font-family: 'Inter', sans-serif;
}
h1, h2, h3 {
  font-family: 'Inter', sans-serif !important;
  font-weight: 800 !important;
  letter-spacing: -0.02em;
}
.mission-subtitle {
  font-family: 'JetBrains Mono', monospace;
  color: #4EDEA3;
  font-size: 0.8rem;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.mission-rule {
  border: none;
  height: 2px;
  background: linear-gradient(to right, #4EDEA3, #0566D9);
  margin: 0.4rem 0 1.4rem 0;
}
.stButton > button, div[data-testid="stFormSubmitButton"] > button {
  background-color: #0566D9;
  color: #FFFFFF;
  border: none;
  border-radius: 9999px;
  font-weight: 700;
  box-shadow: 0 0 15px rgba(5, 102, 217, 0.35);
}
.stButton > button:hover, div[data-testid="stFormSubmitButton"] > button:hover {
  background-color: #2E7FEA;
  color: #FFFFFF;
  box-shadow: 0 0 20px rgba(5, 102, 217, 0.5);
}
div[data-testid="stProgress"] > div > div > div {
  background-color: #4EDEA3;
  box-shadow: 0 0 10px rgba(78, 222, 163, 0.5);
}
div[data-testid="stExpander"] {
  background: rgba(24, 28, 30, 0.6);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(5, 102, 217, 0.25);
  border-radius: 14px;
}
div[data-testid="stExpander"] summary {
  font-family: 'JetBrains Mono', monospace;
  font-weight: 700;
  letter-spacing: 0.03em;
}
button[data-baseweb="tab"] {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
div[data-testid="stMetric"] {
  background: rgba(24, 28, 30, 0.6);
  border: 1px solid rgba(78, 222, 163, 0.3);
  border-radius: 14px;
  padding: 0.8rem 1rem;
}
</style>
""", unsafe_allow_html=True)

curricula = load_curricula()

if "progress" not in st.session_state:
    st.session_state.progress = load_progress()

if "xp_state" not in st.session_state:
    st.session_state.xp_state = load_xp()

st.markdown('<div class="mission-subtitle">STUDY_PLANNER // QUEST LOG</div>', unsafe_allow_html=True)
st.title("🧭 학습 커리큘럼 추천")
st.markdown('<hr class="mission-rule">', unsafe_allow_html=True)

if "pending_select_goal" in st.session_state:
    st.session_state.selected_goal_radio = st.session_state.pop("pending_select_goal")

tab_track, tab_daily, tab_quiz, tab_trend = st.tabs(
    ["트랙별 커리큘럼", "일별 맞춤 플랜", "주간 미니테스트", "막막할 때"]
)

with tab_track:
    with st.sidebar:
        level, xp_into_level, xp_needed = compute_level_info(st.session_state.xp_state["total_xp"])
        st.markdown(f"### 🏅 레벨 {level}")
        st.progress(xp_into_level / xp_needed, text=f"{xp_into_level} / {xp_needed} XP")
        st.divider()

        st.header("목표 선택")
        goal_names = list(curricula.keys())
        selected_goal = st.radio(
            "목표를 고르세요", goal_names, label_visibility="collapsed", key="selected_goal_radio"
        )

        st.divider()
        st.subheader("새 목표 추가 (AI 생성)")
        st.caption("DB에 없는 목표를 입력하면 AI가 새로 만들어줍니다. (API 비용 발생)")
        new_goal_text = st.text_input("목표 입력", key="new_goal_input", label_visibility="collapsed")

        if st.button("AI로 커리큘럼 생성", use_container_width=True):
            goal_stripped = new_goal_text.strip()
            if not goal_stripped:
                st.warning("목표를 입력해주세요.")
            elif goal_stripped in curricula:
                st.info(f"'{goal_stripped}'는 이미 있는 목표입니다. 위 목록에서 선택하세요.")
            else:
                with st.spinner("AI가 커리큘럼을 만드는 중입니다... (몇 초 정도 걸릴 수 있어요)"):
                    try:
                        from llm_recommender import generate_curriculum_via_llm
                        generated = generate_curriculum_via_llm(goal_stripped)
                        curricula[goal_stripped] = generated
                        save_curricula(curricula)
                        st.session_state.pending_select_goal = goal_stripped
                        st.success(f"'{goal_stripped}' 트랙 생성 완료!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"생성 실패: {e}")
                        st.caption("ANTHROPIC_API_KEY 환경변수와 anthropic 패키지 설치 여부를 확인하세요.")

    goal_data = curricula[selected_goal]
    steps = goal_data["steps"]
    completed_ids = set(st.session_state.progress.get(selected_goal, []))

    st.subheader(selected_goal)
    st.write(goal_data["description"])

    progress_ratio = len(completed_ids) / len(steps) if steps else 0
    st.progress(progress_ratio, text=f"{len(completed_ids)}/{len(steps)} 완료")

    st.divider()

    for step in steps:
        checkbox_key = f"{selected_goal}_{step['id']}"
        is_checked = step["id"] in completed_ids

        checked_now = st.checkbox(
            f"**{step['id']}. {step['title']}**",
            value=is_checked,
            key=checkbox_key,
        )

        with st.expander("자세히 보기", expanded=False):
            st.write(step["detail"])
            if step.get("resources"):
                st.write("**추천 자료:** " + ", ".join(step["resources"]))

        if checked_now != is_checked:
            if checked_now:
                completed_ids.add(step["id"])
                add_xp(XP_PER_STEP)
            else:
                completed_ids.discard(step["id"])
                add_xp(-XP_PER_STEP)
            st.session_state.progress[selected_goal] = sorted(completed_ids)
            save_progress(st.session_state.progress)
            st.rerun()

with tab_daily:
    st.caption(
        "학과·학년·목표 분야·과목별 상세 정보(강의계획서, 시험범위, 비중 등)를 입력하면 "
        "AI가 하루 단위로 여러 과목을 섞은 학습 계획을 만들어줍니다. "
        "(API 비용 발생, 결과는 저장되지 않고 화면에만 표시됩니다)"
    )

    uploaded_pdf = st.file_uploader(
        "강의계획서 PDF 업로드 (선택, 올리면 아래 '과목별 정보' 칸에 자동으로 채워집니다)",
        type=["pdf"],
        key="syllabus_pdf_uploader",
    )

    if uploaded_pdf is not None and st.session_state.get("last_pdf_name") != uploaded_pdf.name:
        try:
            from pypdf import PdfReader
            reader = PdfReader(uploaded_pdf)
            extracted_text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
            if not extracted_text:
                st.warning("PDF에서 텍스트를 찾지 못했습니다. 스캔된 이미지 PDF일 수 있어요. 직접 입력해주세요.")
            else:
                st.session_state.course_details = extracted_text
                st.success(f"'{uploaded_pdf.name}'에서 텍스트를 추출해 아래 칸에 채웠습니다. 필요하면 직접 수정하세요.")
            st.session_state.last_pdf_name = uploaded_pdf.name
        except Exception as e:
            st.error(f"PDF 텍스트 추출 실패: {e}")

    with st.form("daily_plan_form"):
        department = st.text_input("학과", placeholder="예: 컴퓨터공학과")
        year = st.text_input("학년", placeholder="예: 2학년 2학기 복학 예정")
        target_field = st.text_input("목표 분야(희망 직무)", placeholder="예: 정보보안")
        course_details = st.text_area(
            "과목별 정보 (과목명, 비중, 시험범위/진도를 자유롭게 적어주세요. PDF를 올렸다면 자동으로 채워져 있습니다)",
            placeholder=(
                "예:\n"
                "시스템프로그래밍 - 비중 25% - 중간고사 범위: 1~7주차 (컴퓨터시스템, Linux/GCC/GDB, "
                "정수/비트, 부동소수점, 어셈블리, Control Flow, Stack)\n"
                "논리회로 - 비중 25% - 중간고사 범위: 1~5장 + Flip-Flop\n"
                "C++ - 비중 25% - 새 진도 없음, 시험형 타임어택 문제 위주\n"
                "Java - 비중 25% - 개념 위주 서술형 시험 대비"
            ),
            height=150,
            key="course_details",
        )
        days_remaining = st.number_input("계획을 세울 기간 (일)", min_value=1, max_value=20, value=12)
        submitted = st.form_submit_button("일별 플랜 생성하기")

    if submitted:
        if not department.strip() or not year.strip() or not target_field.strip() or not course_details.strip():
            st.warning("학과, 학년, 목표 분야, 과목별 정보를 모두 입력해주세요.")
        else:
            context = {
                "department": department.strip(),
                "year": year.strip(),
                "target_field": target_field.strip(),
                "course_details": course_details.strip(),
                "days_remaining": int(days_remaining),
            }
            with st.spinner(f"AI가 {int(days_remaining)}일치 계획을 만드는 중입니다... (시간이 좀 걸릴 수 있어요)"):
                try:
                    from llm_recommender import generate_daily_plan
                    plan = generate_daily_plan(context)
                    st.session_state.generated_daily_plan = plan
                except Exception as e:
                    st.error(f"생성 실패: {e}")
                    st.caption("ANTHROPIC_API_KEY 환경변수와 anthropic 패키지 설치 여부를 확인하세요.")

    if "generated_daily_plan" in st.session_state:
        plan = st.session_state.generated_daily_plan
        st.divider()
        st.subheader(plan["plan_title"])
        for day in plan["days"]:
            with st.expander(f"DAY {day['day']:02d}", expanded=False):
                for subj in day["subjects"]:
                    st.markdown(f"**{subj['subject']}** — {subj['focus']}")
                    for task in subj["tasks"]:
                        st.write(f"- {task}")
                    st.write("")

with tab_quiz:
    st.caption(
        "이번 주에 공부한 내용(개념, 노트, 배운 것)을 입력하면 AI가 객관식 미니테스트를 만들어줍니다. "
        "(API 비용 발생, 결과는 저장되지 않고 화면에만 표시됩니다)"
    )

    with st.form("quiz_gen_form"):
        quiz_topic = st.text_input("주제/과목", placeholder="예: 논리회로 2장")
        study_content = st.text_area(
            "이번 주에 공부한 내용을 입력하세요",
            placeholder="예: 2진수/8진수/16진수 진법변환, 2의 보수, BCD 코드, Gray Code 개념과 변환 방법",
            height=150,
        )
        num_questions = st.number_input("문항 수", min_value=1, max_value=10, value=5)
        quiz_submitted = st.form_submit_button("미니테스트 생성하기")

    if quiz_submitted:
        if not quiz_topic.strip() or not study_content.strip():
            st.warning("주제와 공부한 내용을 모두 입력해주세요.")
        else:
            context = {
                "topic": quiz_topic.strip(),
                "study_content": study_content.strip(),
                "num_questions": int(num_questions),
            }
            with st.spinner("AI가 문제를 만드는 중입니다... (몇 초 정도 걸릴 수 있어요)"):
                try:
                    from llm_recommender import generate_quiz
                    quiz = generate_quiz(context)
                    st.session_state.generated_quiz = quiz
                    # 새 퀴즈를 만들면 이전 채점 결과와 XP 지급 여부를 초기화
                    st.session_state.pop("quiz_result", None)
                    st.session_state.quiz_xp_awarded = False
                except Exception as e:
                    st.error(f"생성 실패: {e}")
                    st.caption("ANTHROPIC_API_KEY 환경변수와 anthropic 패키지 설치 여부를 확인하세요.")

    if "generated_quiz" in st.session_state:
        quiz = st.session_state.generated_quiz
        st.divider()
        st.subheader(quiz["quiz_title"])

        with st.form("quiz_take_form"):
            user_answers = []
            for i, q in enumerate(quiz["questions"]):
                st.markdown(f"**{i + 1}. {q['question']}**")
                answer = st.radio(
                    f"quiz_q_{i}",
                    options=list(range(len(q["options"]))),
                    format_func=lambda idx, opts=q["options"]: opts[idx],
                    key=f"quiz_answer_{i}",
                    label_visibility="collapsed",
                )
                user_answers.append(answer)
                st.write("")
            grade_submitted = st.form_submit_button("채점하기")

        if grade_submitted:
            score = 0
            results = []
            for i, q in enumerate(quiz["questions"]):
                is_correct = user_answers[i] == q["correct_index"]
                if is_correct:
                    score += 1
                results.append(is_correct)
            st.session_state.quiz_result = {"score": score, "total": len(quiz["questions"]), "results": results}
            if not st.session_state.get("quiz_xp_awarded", False):
                add_xp(score * XP_PER_QUIZ_CORRECT)
                st.session_state.quiz_xp_awarded = True

        if "quiz_result" in st.session_state:
            result = st.session_state.quiz_result
            st.divider()
            st.metric("점수", f"{result['score']} / {result['total']}")
            for i, q in enumerate(quiz["questions"]):
                is_correct = result["results"][i]
                icon = "✅" if is_correct else "❌"
                st.markdown(f"{icon} **{i + 1}. {q['question']}**")
                st.write(f"정답: {q['options'][q['correct_index']]}")
                st.caption(q["explanation"])

with tab_trend:
    st.caption(
        "아직 구체적인 목표가 없어도 괜찮습니다. 학과·학년을 입력하면 AI가 실제 웹 검색으로 "
        "최신 채용/기술 트렌드를 확인한 뒤 방향을 추천해줍니다. (API 비용 발생, 웹 검색 추가 비용 포함)"
    )

    with st.form("trend_form"):
        trend_department = st.text_input("학과", placeholder="예: 컴퓨터공학과", key="trend_department")
        trend_year = st.text_input("학년", placeholder="예: 2학년 2학기 복학 예정", key="trend_year")
        interest_hint = st.text_input(
            "관심 있는 분야 (선택, 없으면 비워두세요)",
            placeholder="예: 백엔드 쪽이 좀 끌린다, AI 관련이 궁금하다 등",
        )
        trend_submitted = st.form_submit_button("트렌드 기반 추천받기")

    if trend_submitted:
        if not trend_department.strip() or not trend_year.strip():
            st.warning("학과와 학년을 입력해주세요.")
        else:
            context = {
                "department": trend_department.strip(),
                "year": trend_year.strip(),
                "interest_hint": interest_hint.strip(),
            }
            with st.spinner("AI가 최신 트렌드를 검색하고 분석하는 중입니다... (시간이 좀 걸릴 수 있어요)"):
                try:
                    from llm_recommender import generate_trend_recommendations
                    trend_result = generate_trend_recommendations(context)
                    st.session_state.trend_result = trend_result
                except Exception as e:
                    st.error(f"생성 실패: {e}")
                    st.caption("ANTHROPIC_API_KEY 환경변수와 anthropic 패키지 설치 여부를 확인하세요.")

    if "trend_result" in st.session_state:
        trend_result = st.session_state.trend_result
        st.divider()
        if trend_result.get("analysis"):
            st.write(trend_result["analysis"])

        for i, rec in enumerate(trend_result["recommendations"]):
            with st.container():
                st.subheader(rec["title"])
                st.write(rec["reason"])
                st.caption(f"근거: {rec['evidence']}")

                if st.button(f"이 방향으로 커리큘럼 만들기", key=f"trend_make_{i}"):
                    title_stripped = rec["title"].strip()
                    if title_stripped in curricula:
                        st.info(f"'{title_stripped}'는 이미 '트랙별 커리큘럼' 탭에 있습니다. 그쪽에서 확인하세요.")
                    else:
                        with st.spinner("AI가 커리큘럼을 만드는 중입니다..."):
                            try:
                                from llm_recommender import generate_curriculum_via_llm
                                generated = generate_curriculum_via_llm(title_stripped)
                                curricula[title_stripped] = generated
                                save_curricula(curricula)
                                st.session_state.pending_select_goal = title_stripped
                                st.success(f"'{title_stripped}' 트랙이 생성됐습니다. '트랙별 커리큘럼' 탭에서 확인하세요.")
                            except Exception as e:
                                st.error(f"생성 실패: {e}")
                st.divider()
