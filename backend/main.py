"""
backend/main.py

Streamlit 앱에서 쓰던 llm_recommender.py의 AI 로직을 그대로 재사용해서
React 프론트엔드가 호출할 수 있는 REST API로 감싼다.

실행법:
1) pip install -r requirements.txt
2) export ANTHROPIC_API_KEY="발급받은키"
3) uvicorn main:app --reload --port 8000
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from llm_recommender import (
    generate_certifications,
    generate_curriculum_via_llm,
    generate_daily_plan,
    generate_lecture_analysis,
    generate_quiz,
    generate_study_list,
    generate_trend_recommendations,
)
from storage import (
    add_custom_item,
    add_custom_subject,
    add_material_analysis,
    add_quiz_to_bank,
    add_xp,
    add_xp_with_activity,
    compute_level_info,
    delete_daily_plan,
    delete_material_item,
    delete_quiz_from_bank,
    get_recently_completed_items,
    import_daily_plan_items,
    load_activity_log,
    load_custom_curriculum,
    load_daily_plans,
    load_materials,
    load_progress,
    load_quiz_bank,
    load_quiz_state,
    load_xp_state,
    log_activity,
    remove_custom_item,
    remove_custom_subject,
    reorder_custom_items,
    save_daily_plan,
    save_quiz_state,
    set_step_completed,
    update_custom_item,
    update_quiz_bank_question,
    update_quiz_bank_result,
)
from slide_vision import describe_slides_with_vision, render_slides_to_images
from text_extraction import extract_text

app = FastAPI(title="StudyQuest API")

# 로컬 개발 중인 React(Vite) 서버에서의 요청만 허용. 같은 와이파이의 다른 기기에서
# 접속할 때는 Vite가 사설 IP(192.168.x.x/10.x.x.x/172.16~31.x.x) 주소로 열리므로,
# 정확한 IP를 미리 알 수 없어 도메인 하나만 허용하는 대신 사설 대역 + 5173 포트를
# 정규식으로 허용한다(전체 오리진 허용은 아님).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_origin_regex=r"^http://(127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}):5173$",
    allow_methods=["*"],
    allow_headers=["*"],
)


class CurriculumRequest(BaseModel):
    goal: str


class DailyPlanRequest(BaseModel):
    department: str
    year: str
    subject: str
    course_details: str
    days_remaining: int
    start_date: str


class QuizRequest(BaseModel):
    topic: str
    study_content: str
    num_questions: int


class TrendRequest(BaseModel):
    department: str
    year: str
    interest_hint: str = ""


class StudyListRequest(BaseModel):
    subject: str
    material_text: str


class LectureAnalysisRequest(BaseModel):
    subject: str
    material_text: str


class CertificationRequest(BaseModel):
    goal: str


class ProgressToggleRequest(BaseModel):
    goal: str
    step_id: int
    completed: bool


class XpAddRequest(BaseModel):
    amount: int
    label: str = ""


class SubjectRequest(BaseModel):
    subject: str


class CustomItemCreateRequest(BaseModel):
    subject: str
    title: str


class CustomItemUpdateRequest(BaseModel):
    subject: str
    item_id: int
    title: Optional[str] = None
    done: Optional[bool] = None


class CustomItemDeleteRequest(BaseModel):
    subject: str
    item_id: int


class CustomItemReorderRequest(BaseModel):
    subject: str
    item_ids: List[int]


class DailyPlanImportRequest(BaseModel):
    plan_title: str = ""
    days: list


class DailyPlanUpsertRequest(BaseModel):
    subject: str
    plan: dict


class MaterialAddRequest(BaseModel):
    subject: str
    analysis: dict


class MaterialDeleteRequest(BaseModel):
    subject: str
    item_id: int


class QuizStateRequest(BaseModel):
    topic: str = ""
    study_content: str = ""
    num_questions: int = 5
    quiz: Optional[dict] = None
    answers: dict = {}
    result: Optional[dict] = None
    xp_awarded: bool = False


class QuizBankResultRequest(BaseModel):
    subject: str
    quiz_id: int
    answers: dict
    result: dict


class QuizBankQuestionRequest(BaseModel):
    subject: str
    quiz_id: int
    question_index: int
    answer_index: int
    correct: bool


class QuizBankDeleteRequest(BaseModel):
    subject: str
    quiz_id: int


def _xp_response() -> dict:
    xp_state = load_xp_state()
    level, xp_into_level, xp_needed = compute_level_info(xp_state["total_xp"])
    return {
        "total_xp": xp_state["total_xp"],
        "level": level,
        "xp_into_level": xp_into_level,
        "xp_needed": xp_needed,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/curriculum")
def create_curriculum(req: CurriculumRequest):
    try:
        return generate_curriculum_via_llm(req.goal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/daily-plan")
def create_daily_plan(req: DailyPlanRequest):
    try:
        plan = generate_daily_plan(req.model_dump())
        log_activity("daily_plan_generated", plan.get("plan_title", "일별 플랜 생성"))
        save_daily_plan(req.subject, plan)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/daily-plans")
def get_daily_plans():
    return {"plans": load_daily_plans()}


@app.put("/api/daily-plans")
def put_daily_plan(req: DailyPlanUpsertRequest):
    """AI를 다시 부르지 않고 이미 갖고 있는 플랜을 그대로 저장한다 — 브라우저 localStorage에만
    있던 예전 데이터를 서버로 옮길 때 쓴다."""
    return {"plans": save_daily_plan(req.subject, req.plan)}


@app.delete("/api/daily-plans")
def delete_daily_plans(req: SubjectRequest):
    return {"plans": delete_daily_plan(req.subject)}


@app.post("/api/quiz")
def create_quiz(req: QuizRequest):
    try:
        quiz = generate_quiz(req.model_dump())
        # 생성된 퀴즈를 그 과목(topic)의 "기출문제 모음"에 자동으로 쌓는다. bank_id를 응답에
        # 실어서 보내면, 프론트가 나중에 채점 결과를 이 id로 서버에 반영할 수 있다.
        bank_id = add_quiz_to_bank(req.topic, quiz.get("quiz_title", req.topic), quiz["questions"])
        quiz["bank_id"] = bank_id
        return quiz
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/quiz-bank")
def get_quiz_bank():
    return {"bank": load_quiz_bank()}


@app.put("/api/quiz-bank/result")
def put_quiz_bank_result(req: QuizBankResultRequest):
    return {"bank": update_quiz_bank_result(req.subject, req.quiz_id, req.answers, req.result)}


@app.put("/api/quiz-bank/question")
def put_quiz_bank_question(req: QuizBankQuestionRequest):
    return {
        "bank": update_quiz_bank_question(
            req.subject, req.quiz_id, req.question_index, req.answer_index, req.correct
        )
    }


@app.delete("/api/quiz-bank")
def delete_quiz_bank_item(req: QuizBankDeleteRequest):
    return {"bank": delete_quiz_from_bank(req.subject, req.quiz_id)}


@app.post("/api/trend")
def create_trend(req: TrendRequest):
    try:
        return generate_trend_recommendations(req.model_dump())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/extract-material")
async def extract_material(file: UploadFile = File(...)):
    file_bytes = await file.read()

    # 1순위: 슬라이드를 이미지로 렌더링해 Claude Vision으로 분석 — 표/다이어그램/그래프까지 읽는다.
    # LibreOffice가 없거나 변환/API 호출이 실패하면 조용히 아래 순수 텍스트 추출로 넘어간다.
    try:
        images = render_slides_to_images(file.filename, file_bytes)
        vision_text = describe_slides_with_vision(images)
        if vision_text:
            return {"extracted_text": vision_text, "used_vision": True}
    except Exception:
        pass

    try:
        text = extract_text(file.filename, file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"파일에서 텍스트를 추출하지 못했습니다: {e}")

    if not text:
        raise HTTPException(
            status_code=400,
            detail="파일에서 텍스트를 찾지 못했습니다. 스캔된 이미지 파일일 수 있습니다.",
        )

    return {"extracted_text": text, "used_vision": False}


@app.post("/api/study-list")
def create_study_list(req: StudyListRequest):
    try:
        result = generate_study_list(req.model_dump())
        log_activity("study_list_generated", result.get("study_title", "강의자료 분석"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/lecture-analysis")
def create_lecture_analysis(req: LectureAnalysisRequest):
    try:
        result = generate_lecture_analysis(req.model_dump())
        log_activity("lecture_analysis_generated", result.get("analysis_title", "강의자료 심층 분석"))
        # 강의자료는 보통 주차/챕터별로 여러 개 올라오므로, 같은 과목이어도 덮어쓰지 않고
        # 계속 쌓는다(기출문제 모음과 같은 패턴). material_id를 응답에 실어 보내면 프론트가
        # 나중에 이 항목만 개별 삭제할 수 있다.
        material_id = add_material_analysis(req.subject, result)
        result["material_id"] = material_id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/materials")
def get_materials():
    return {"materials": load_materials()}


@app.put("/api/materials")
def put_material(req: MaterialAddRequest):
    """AI를 다시 부르지 않고 이미 갖고 있는 분석 결과를 그대로 목록에 추가한다 — 브라우저
    localStorage에만 있던 예전 데이터를 서버로 옮길 때 쓴다."""
    add_material_analysis(req.subject, req.analysis)
    return {"materials": load_materials()}


@app.delete("/api/materials")
def delete_materials(req: MaterialDeleteRequest):
    return {"materials": delete_material_item(req.subject, req.item_id)}


@app.get("/api/quiz-state")
def get_quiz_state():
    return {"state": load_quiz_state()}


@app.post("/api/quiz-state")
def post_quiz_state(req: QuizStateRequest):
    save_quiz_state(req.model_dump())
    return {"status": "ok"}


@app.post("/api/certifications")
def create_certifications(req: CertificationRequest):
    try:
        return generate_certifications(req.goal)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/xp")
def get_xp():
    return _xp_response()


@app.post("/api/xp/add")
def post_xp_add(req: XpAddRequest):
    if req.label:
        add_xp_with_activity(req.amount, "quiz_graded", req.label)
    else:
        add_xp(req.amount)
    return _xp_response()


@app.get("/api/progress")
def get_progress(goal: str):
    progress = load_progress()
    return {"completed_step_ids": progress.get(goal, [])}


@app.post("/api/progress/toggle")
def post_progress_toggle(req: ProgressToggleRequest):
    progress = set_step_completed(req.goal, req.step_id, req.completed)
    return {
        "completed_step_ids": progress.get(req.goal, []),
        "xp": _xp_response(),
    }


@app.get("/api/activity")
def get_activity(days: int = 14):
    cutoff = datetime.now() - timedelta(days=days)
    entries = load_activity_log()
    recent = [e for e in entries if datetime.fromisoformat(e["timestamp"]) >= cutoff]
    recent.sort(key=lambda e: e["timestamp"], reverse=True)
    return {"activities": recent}


@app.get("/api/custom-curriculum")
def get_custom_curriculum():
    return {"subjects": load_custom_curriculum()}


@app.post("/api/custom-curriculum/subject")
def post_custom_subject(req: SubjectRequest):
    return {"subjects": add_custom_subject(req.subject)}


@app.delete("/api/custom-curriculum/subject")
def delete_custom_subject(req: SubjectRequest):
    return {"subjects": remove_custom_subject(req.subject)}


@app.post("/api/custom-curriculum/item")
def post_custom_item(req: CustomItemCreateRequest):
    return {"subjects": add_custom_item(req.subject, req.title)}


@app.patch("/api/custom-curriculum/item")
def patch_custom_item(req: CustomItemUpdateRequest):
    subjects = update_custom_item(req.subject, req.item_id, title=req.title, done=req.done)
    return {"subjects": subjects, "xp": _xp_response()}


@app.delete("/api/custom-curriculum/item")
def delete_custom_item(req: CustomItemDeleteRequest):
    return {"subjects": remove_custom_item(req.subject, req.item_id)}


@app.post("/api/custom-curriculum/reorder-items")
def post_reorder_items(req: CustomItemReorderRequest):
    return {"subjects": reorder_custom_items(req.subject, req.item_ids)}


@app.get("/api/custom-curriculum/recent-completed")
def get_recent_completed(days: int = 7):
    return {"items": get_recently_completed_items(days)}


@app.post("/api/custom-curriculum/import-daily-plan")
def post_import_daily_plan(req: DailyPlanImportRequest):
    return {"subjects": import_daily_plan_items(req.model_dump())}