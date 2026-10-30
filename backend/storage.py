"""
backend/storage.py

React/FastAPI 버전의 진행 상황(단계 완료 체크), XP, 활동 기록, 사용자가 직접 작성하는
과목별 커리큘럼을 저장하는 단순 JSON 파일 저장소. 로컬 1인 사용을 가정하므로 동시 요청에
대한 락은 걸지 않는다.
"""

import json
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PROGRESS_PATH = os.path.join(DATA_DIR, "progress.json")
XP_PATH = os.path.join(DATA_DIR, "xp.json")
ACTIVITY_LOG_PATH = os.path.join(DATA_DIR, "activity_log.json")
CUSTOM_CURRICULUM_PATH = os.path.join(DATA_DIR, "custom_curriculum.json")
DAILY_PLANS_PATH = os.path.join(DATA_DIR, "daily_plans.json")
MATERIALS_PATH = os.path.join(DATA_DIR, "materials.json")
QUIZ_STATE_PATH = os.path.join(DATA_DIR, "quiz_state.json")
QUIZ_BANK_PATH = os.path.join(DATA_DIR, "quiz_bank.json")

XP_PER_LEVEL = 150
XP_PER_STEP = 20
XP_PER_QUIZ_CORRECT = 10


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_progress() -> dict:
    if not os.path.exists(PROGRESS_PATH):
        return {}
    with open(PROGRESS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_progress(progress: dict):
    _ensure_data_dir()
    with open(PROGRESS_PATH, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def load_xp_state() -> dict:
    if not os.path.exists(XP_PATH):
        return {"total_xp": 0}
    with open(XP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_xp_state(xp_state: dict):
    _ensure_data_dir()
    with open(XP_PATH, "w", encoding="utf-8") as f:
        json.dump(xp_state, f, ensure_ascii=False, indent=2)


def compute_level_info(total_xp: int):
    """총 XP로부터 (레벨, 현재 레벨 안에서의 XP, 레벨업까지 필요한 XP)를 계산."""
    level = total_xp // XP_PER_LEVEL + 1
    xp_into_level = total_xp % XP_PER_LEVEL
    return level, xp_into_level, XP_PER_LEVEL


def add_xp(amount: int) -> dict:
    xp_state = load_xp_state()
    xp_state["total_xp"] = max(0, xp_state["total_xp"] + amount)
    save_xp_state(xp_state)
    return xp_state


def load_activity_log() -> list:
    if not os.path.exists(ACTIVITY_LOG_PATH):
        return []
    with open(ACTIVITY_LOG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_activity_log(entries: list):
    _ensure_data_dir()
    with open(ACTIVITY_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def log_activity(activity_type: str, title: str, xp_delta: int = 0) -> dict:
    """오늘/어제 활동 피드에 쓸 이벤트 하나를 기록에 추가한다."""
    entries = load_activity_log()
    entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "type": activity_type,
        "title": title,
        "xp_delta": xp_delta,
    }
    entries.append(entry)
    save_activity_log(entries)
    return entry


def remove_last_activity_by_title(title: str):
    """체크 해제처럼 완료를 취소할 때, 그에 대응하는 '완료' 기록 한 건을 활동 피드에서 지운다
    (가장 최근 것 하나만 — 같은 제목으로 과거에 완료했던 다른 기록까지 지우지 않기 위해)."""
    entries = load_activity_log()
    for i in range(len(entries) - 1, -1, -1):
        if entries[i]["title"] == title:
            entries.pop(i)
            break
    save_activity_log(entries)


def add_xp_with_activity(amount: int, activity_type: str, title: str) -> dict:
    xp_state = add_xp(amount)
    log_activity(activity_type, title, xp_delta=amount)
    return xp_state


def set_step_completed(goal: str, step_id: int, completed: bool) -> dict:
    """단계 완료 상태를 갱신하고, 상태가 실제로 바뀐 경우에만 XP를 가감하고 기록을 남긴다."""
    progress = load_progress()
    completed_ids = set(progress.get(goal, []))
    was_completed = step_id in completed_ids

    if completed:
        completed_ids.add(step_id)
    else:
        completed_ids.discard(step_id)
    progress[goal] = sorted(completed_ids)
    save_progress(progress)

    if completed and not was_completed:
        add_xp_with_activity(XP_PER_STEP, "step_completed", f"{goal} · {step_id}번 단계 완료")
    elif not completed and was_completed:
        add_xp(-XP_PER_STEP)

    return progress


def load_custom_curriculum() -> dict:
    """사용자가 직접 작성하는 과목별 커리큘럼: {과목명: [{id, title, done}]}"""
    if not os.path.exists(CUSTOM_CURRICULUM_PATH):
        return {}
    with open(CUSTOM_CURRICULUM_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_custom_curriculum(data: dict):
    _ensure_data_dir()
    with open(CUSTOM_CURRICULUM_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_custom_subject(subject: str) -> dict:
    data = load_custom_curriculum()
    data.setdefault(subject, [])
    save_custom_curriculum(data)
    return data


def remove_custom_subject(subject: str) -> dict:
    data = load_custom_curriculum()
    data.pop(subject, None)
    save_custom_curriculum(data)
    return data


def add_custom_item(subject: str, title: str) -> dict:
    data = load_custom_curriculum()
    items = data.setdefault(subject, [])
    new_id = max((item["id"] for item in items), default=0) + 1
    items.append({"id": new_id, "title": title, "done": False, "content": ""})
    save_custom_curriculum(data)
    return data


def update_custom_item(subject: str, item_id: int, title=None, done=None) -> dict:
    data = load_custom_curriculum()
    items = data.get(subject, [])
    for item in items:
        if item["id"] != item_id:
            continue
        if title is not None:
            item["title"] = title
        if done is not None and done != item["done"]:
            item["done"] = done
            if done:
                item["completed_at"] = datetime.now().isoformat(timespec="seconds")
                add_xp_with_activity(XP_PER_STEP, "step_completed", f"{subject} · {item['title']} 완료")
            else:
                item["completed_at"] = None
                add_xp(-XP_PER_STEP)
                remove_last_activity_by_title(f"{subject} · {item['title']} 완료")
        break
    save_custom_curriculum(data)
    return data


def get_recently_completed_items(days: int = 7) -> list:
    """최근 N일 안에 체크 완료되고 공부 내용(content)이 있는 항목들을 과목명과 함께 모은다.
    "이번 주 미니테스트" 카드처럼, 최근에 실제로 공부하고 체크한 내용 기반으로 퀴즈를
    만들 때 쓴다."""
    cutoff = datetime.now() - timedelta(days=days)
    data = load_custom_curriculum()

    results = []
    for subject, items in data.items():
        for item in items:
            if not item.get("done") or not item.get("content"):
                continue
            completed_at = item.get("completed_at")
            if not completed_at:
                continue
            try:
                when = datetime.fromisoformat(completed_at)
            except ValueError:
                continue
            if when >= cutoff:
                results.append({"subject": subject, **item})

    return results


def remove_custom_item(subject: str, item_id: int) -> dict:
    data = load_custom_curriculum()
    items = data.get(subject, [])
    data[subject] = [item for item in items if item["id"] != item_id]
    save_custom_curriculum(data)
    return data


def reorder_custom_items(subject: str, item_ids: list) -> dict:
    """드래그로 바꾼 순서(item_ids)대로 그 과목의 항목 배열을 다시 정렬한다.
    요청에 없는 id가 있으면(동시 편집 등) 잃어버리지 않도록 원래 순서 그대로 맨 뒤에 붙인다."""
    data = load_custom_curriculum()
    items = data.get(subject, [])
    items_by_id = {item["id"]: item for item in items}

    reordered = [items_by_id[i] for i in item_ids if i in items_by_id]
    missing = [item for item in items if item["id"] not in item_ids]
    data[subject] = reordered + missing

    save_custom_curriculum(data)
    return data


def _build_item_content(subj: dict) -> str:
    """플랜의 한 과목 항목(concepts/practice)을 미니테스트 생성용 텍스트로 합친다."""
    parts = []
    concepts = subj.get("concepts") or []
    if concepts:
        parts.append("핵심 개념: " + ", ".join(concepts))
    practice = subj.get("practice")
    if practice:
        parts.append("실습 내용:\n" + practice)
    return "\n\n".join(parts)


def import_daily_plan_items(plan: dict) -> dict:
    """일별 플랜의 각 날짜·과목 항목을 과목별 커리큘럼에 체크리스트 항목으로 넣는다.
    같은 제목의 항목이 이미 그 과목에 있으면(재생성한 경우) 새로 추가하지 않고, 그 항목에
    아직 공부 내용(content)이 없으면 채워 넣기만 한다 — 이 content가 있어야 나중에 그 항목을
    기반으로 미니테스트를 바로 만들 수 있다."""
    data = load_custom_curriculum()

    for day in plan.get("days", []):
        day_num = day.get("day")
        date_str = day.get("date", "")
        for subj in day.get("subjects", []):
            subject_name = subj.get("subject")
            topic = subj.get("topic", "")
            if not subject_name or not topic:
                continue

            title = f"Day {day_num} ({date_str}) · {topic}"
            content = _build_item_content(subj)
            # concepts/practice/emoji는 미니테스트용 content와 별개로 그대로 보관한다 — 일별
            # 플랜 탭에서 보이던 것과 똑같은 형태(개념 목록 + 실습 블록)로 과목별 커리큘럼에서도
            # 펼쳐볼 수 있게 하기 위함이다.
            emoji = subj.get("emoji", "")
            concepts = subj.get("concepts") or []
            practice = subj.get("practice") or ""
            items = data.setdefault(subject_name, [])

            existing = next((item for item in items if item["title"] == title), None)
            if existing is not None:
                # 이 기능(concepts/practice 보관)이 생기기 전에 이미 임포트된 항목은 아직
                # 이 필드들이 없을 수 있다 — 같은 플랜을 다시 생성하면 그때 채워 넣는다.
                if not existing.get("content") and content:
                    existing["content"] = content
                if not existing.get("concepts") and concepts:
                    existing["concepts"] = concepts
                if not existing.get("practice") and practice:
                    existing["practice"] = practice
                if not existing.get("emoji") and emoji:
                    existing["emoji"] = emoji
                continue

            new_id = max((item["id"] for item in items), default=0) + 1
            items.append(
                {
                    "id": new_id,
                    "title": title,
                    "done": False,
                    "content": content,
                    "emoji": emoji,
                    "concepts": concepts,
                    "practice": practice,
                }
            )

    save_custom_curriculum(data)
    return data


# 일별 플랜/강의자료 분석/미니테스트 결과는 원래 브라우저 localStorage에만 저장되어 기기마다
# 따로 보였다. 같은 와이파이의 다른 기기에서 접속해도 같은 내용을 보고 싶다는 요청으로
# 이 셋도 과목별 커리큘럼처럼 서버 파일에 저장한다.


def load_daily_plans() -> dict:
    """과목별로 저장된 일별 플랜: {과목명: 플랜 데이터}"""
    if not os.path.exists(DAILY_PLANS_PATH):
        return {}
    with open(DAILY_PLANS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_daily_plan(subject: str, plan: dict) -> dict:
    data = load_daily_plans()
    data[subject] = plan
    _ensure_data_dir()
    with open(DAILY_PLANS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def delete_daily_plan(subject: str) -> dict:
    data = load_daily_plans()
    data.pop(subject, None)
    _ensure_data_dir()
    with open(DAILY_PLANS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def load_materials() -> dict:
    """과목/주제별로 쌓인 교수 시점 분석 기록: {과목명: [{id, created_at, ...분석 결과 필드}]}
    강의자료는 보통 주차/챕터별로 여러 개 올라오므로, 새 과목으로 다시 분석해도 이전 결과를
    덮어쓰지 않고 계속 쌓인다(기출문제 모음과 같은 패턴)."""
    if not os.path.exists(MATERIALS_PATH):
        return {}
    with open(MATERIALS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 예전 버전은 과목당 결과를 하나만({"study_list":..., "lecture_analysis":...}) 저장했다.
    # 리스트가 아니라 그 옛날 형태로 남아있으면 한 번만 새 형태(리스트)로 바꿔서 저장해둔다
    # (예습·복습 리스트 기능은 없어졌으므로 study_list는 옮기지 않는다).
    changed = False
    for subject, value in list(data.items()):
        if isinstance(value, dict):
            legacy_analysis = value.get("lecture_analysis")
            data[subject] = (
                [{"id": 1, "created_at": datetime.now().isoformat(timespec="seconds"), **legacy_analysis}]
                if legacy_analysis
                else []
            )
            changed = True
    if changed:
        _save_materials(data)

    return data


def _save_materials(data: dict):
    _ensure_data_dir()
    with open(MATERIALS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_material_analysis(subject: str, analysis: dict) -> int:
    """새로 생성된 교수 시점 분석을 그 과목의 목록에 추가한다. 새로 생긴 항목의 id를
    반환한다 — 프론트가 나중에 이 id로 개별 삭제할 수 있다."""
    data = load_materials()
    items = data.setdefault(subject, [])
    new_id = max((item["id"] for item in items), default=0) + 1
    items.append({"id": new_id, "created_at": datetime.now().isoformat(timespec="seconds"), **analysis})
    _save_materials(data)
    return new_id


def delete_material_item(subject: str, item_id: int) -> dict:
    data = load_materials()
    items = data.get(subject, [])
    data[subject] = [item for item in items if item["id"] != item_id]
    _save_materials(data)
    return data


def load_quiz_state():
    """마지막으로 생성/채점한 미니테스트 상태(항상 하나만 유지) — 기기가 바뀌어도 이어볼 수
    있게 한다. 저장된 게 없으면 None."""
    if not os.path.exists(QUIZ_STATE_PATH):
        return None
    with open(QUIZ_STATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_quiz_state(state: dict):
    _ensure_data_dir()
    with open(QUIZ_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# 과목/주제별로 지금까지 생성된 미니테스트를 전부 쌓아두는 "기출문제 모음". 미니테스트를
# 만들 때마다(주제 = 과목) 자동으로 여기에 하나씩 쌓이고, 나중에 다시 풀어볼 수 있다.
# 오답노트는 이 안에서 마지막 결과가 틀린 문제만 걸러서 보여주는 것이라 별도 파일을 두지
# 않는다.


def load_quiz_bank() -> dict:
    """{과목명: [{id, quiz_title, created_at, questions, answers, result}]}"""
    if not os.path.exists(QUIZ_BANK_PATH):
        return {}
    with open(QUIZ_BANK_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_quiz_bank(data: dict):
    _ensure_data_dir()
    with open(QUIZ_BANK_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_quiz_to_bank(subject: str, quiz_title: str, questions: list) -> int:
    """새로 생성된 퀴즈를 그 과목의 기출문제 목록에 추가한다(아직 채점 전이라 answers/result는
    비어있다). 새로 생긴 항목의 id를 반환한다 — 프론트가 나중에 채점 결과를 이 id로 갱신한다."""
    data = load_quiz_bank()
    items = data.setdefault(subject, [])
    new_id = max((item["id"] for item in items), default=0) + 1
    items.append(
        {
            "id": new_id,
            "quiz_title": quiz_title,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "questions": questions,
            "answers": {},
            "result": None,
        }
    )
    _save_quiz_bank(data)
    return new_id


def update_quiz_bank_result(subject: str, quiz_id: int, answers: dict, result: dict) -> dict:
    """처음 채점하거나(기출문제 모음에서) 다시 풀었을 때 그 기록의 답/결과 전체를 갱신한다."""
    data = load_quiz_bank()
    for item in data.get(subject, []):
        if item["id"] == quiz_id:
            item["answers"] = answers
            item["result"] = result
            break
    _save_quiz_bank(data)
    return data


def update_quiz_bank_question(subject: str, quiz_id: int, question_index: int, answer_index: int, correct: bool) -> dict:
    """오답노트에서 문제 하나만 다시 풀었을 때, 그 문제가 속한 원래 기록의 해당 문제 결과만
    갱신한다 — 맞히면 그 문제는 다음부터 오답노트에서 빠진다."""
    data = load_quiz_bank()
    for item in data.get(subject, []):
        if item["id"] != quiz_id:
            continue
        total = len(item["questions"])
        if item.get("result") is None:
            item["result"] = {"score": 0, "total": total, "results": [False] * total}
        results = item["result"]["results"]
        while len(results) < total:
            results.append(False)
        results[question_index] = correct
        item["result"]["score"] = sum(1 for r in results if r)
        item.setdefault("answers", {})[str(question_index)] = answer_index
        break
    _save_quiz_bank(data)
    return data


def delete_quiz_from_bank(subject: str, quiz_id: int) -> dict:
    data = load_quiz_bank()
    items = data.get(subject, [])
    data[subject] = [item for item in items if item["id"] != quiz_id]
    _save_quiz_bank(data)
    return data
