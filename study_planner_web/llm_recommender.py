"""
study_planner/llm_recommender.py

사용자가 입력한 목표가 curricula.json에 없을 때, Anthropic API를 호출해
같은 형식의 커리큘럼을 생성한다.

주의: 이 모듈을 쓰려면
1) pip install anthropic
2) 환경변수 ANTHROPIC_API_KEY 에 본인 API 키를 설정
해야 한다. (console.anthropic.com에서 발급, 사용량만큼 과금)
"""

import json
import re

def _get_client():
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic 패키지가 설치되어 있지 않습니다. 'pip install anthropic'을 실행하세요."
        ) from e
    return Anthropic()


def build_prompt(goal_text: str) -> str:
    return f"""당신은 컴퓨터공학과 학생의 진로 학습 커리큘럼을 설계하는 전문가입니다.
목표: "{goal_text}"

이 목표를 달성하기 위한 학습 커리큘럼을 6~10단계로 설계하세요.
각 단계는 실제로 존재하는, 검증 가능한 학습 자료/사이트/서적만 언급하세요.
확실하지 않은 자격증명, 사이트명, 도서명은 만들어내지 말고 일반적인 카테고리로만 서술하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "description": "이 트랙에 대한 한 문장 설명",
  "steps": [
    {{"id": 1, "title": "단계 제목", "detail": "구체적 설명", "resources": ["자료1", "자료2"]}}
  ]
}}"""


def parse_llm_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    if "steps" not in data or not isinstance(data["steps"], list) or len(data["steps"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'steps' 목록이 없습니다:\n{data}")
    for step in data["steps"]:
        if "id" not in step or "title" not in step:
            raise ValueError(f"단계 형식이 올바르지 않습니다: {step}")

    data.setdefault("description", f"'{data.get('description', '')}' 자동 생성 트랙")
    return data


def generate_curriculum_via_llm(goal_text: str, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_prompt(goal_text)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_llm_response(full_text)


def build_daily_plan_prompt(context: dict) -> str:
    return f"""당신은 대학생 맞춤 학습 플래너 전문가입니다.

학생 정보:
- 학과: {context['department']}
- 학년: {context['year']}
- 목표 분야(취업 희망 직무): {context['target_field']}
- 계획을 세울 기간: 총 {context['days_remaining']}일

아래는 학생이 직접 제공한 과목별 정보(과목명, 비중, 시험범위/진도 등)입니다.
이 정보를 최우선 근거로 사용하세요. 여기 없는 세부사항(정확한 교재 챕터 번호 등)을 추측해서 확정적으로 쓰지 마세요:
---
{context['course_details']}
---

요구사항:
1. 정확히 {context['days_remaining']}일치 계획을 만드세요 (Day 1 ~ Day {context['days_remaining']}).
2. 위에 제공된 과목별 정보(범위, 비중)를 최대한 정확히 반영하세요.
3. 하루에 여러 과목을 섞어서 배분하세요 (한 과목만 몰아서 하지 않기).
4. 시험 범위가 있는 과목은 뒤로 갈수록 "선행학습 → 문제풀이 → 모의고사 → 총복습" 순으로 실전 대비 비중을 높이세요.
5. 확실하지 않은 책/사이트명을 지어내지 말고, 학생이 제공한 정보와 일반적으로 알려진 개념 이름만 사용하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "plan_title": "이 플랜에 대한 한 줄 제목",
  "days": [
    {{
      "day": 1,
      "subjects": [
        {{"subject": "과목명", "focus": "그 날 다룰 범위/주제", "tasks": ["할 일 1", "할 일 2"]}}
      ]
    }}
  ]
}}"""


def parse_daily_plan_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    if "days" not in data or not isinstance(data["days"], list) or len(data["days"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'days' 목록이 없습니다:\n{data}")
    for day in data["days"]:
        if "day" not in day or "subjects" not in day or not isinstance(day["subjects"], list):
            raise ValueError(f"날짜 항목 형식이 올바르지 않습니다: {day}")
        for subj in day["subjects"]:
            if "subject" not in subj or "focus" not in subj or "tasks" not in subj:
                raise ValueError(f"과목 항목 형식이 올바르지 않습니다: {subj}")

    data.setdefault("plan_title", "맞춤 학습 플랜")
    return data


def generate_daily_plan(context: dict, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_daily_plan_prompt(context)

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_daily_plan_response(full_text)


def build_quiz_prompt(context: dict) -> str:
    return f"""당신은 대학생을 위한 시험 대비 문제 출제 전문가입니다.

아래는 학생이 이번 주(또는 최근)에 공부한 내용입니다. 이 내용에서만 문제를 출제하세요.
여기 없는 내용을 새로 만들어서 물어보지 마세요:
---
{context['study_content']}
---

주제/과목: {context['topic']}

요구사항:
1. 객관식 문제 정확히 {context['num_questions']}개를 만드세요.
2. 각 문제는 보기 4개, 그 중 정답 1개로 구성하세요.
3. 단순 암기보다는 개념을 제대로 이해했는지 확인하는 문제 위주로 만드세요.
4. 오답 보기도 그럴듯하게 만들어서 대충 찍어도 맞히기 어렵게 하세요.
5. 각 문제마다 정답인 이유를 간단히 설명하세요.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "quiz_title": "이 퀴즈에 대한 한 줄 제목",
  "questions": [
    {{
      "question": "문제 내용",
      "options": ["보기1", "보기2", "보기3", "보기4"],
      "correct_index": 0,
      "explanation": "정답인 이유"
    }}
  ]
}}"""


def parse_quiz_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    if "questions" not in data or not isinstance(data["questions"], list) or len(data["questions"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'questions' 목록이 없습니다:\n{data}")
    for q in data["questions"]:
        if "question" not in q or "options" not in q or "correct_index" not in q or "explanation" not in q:
            raise ValueError(f"문제 항목 형식이 올바르지 않습니다: {q}")
        if not isinstance(q["options"], list) or len(q["options"]) < 2:
            raise ValueError(f"보기가 부족합니다: {q}")
        if not (0 <= q["correct_index"] < len(q["options"])):
            raise ValueError(f"correct_index가 보기 범위를 벗어납니다: {q}")

    data.setdefault("quiz_title", "주간 미니테스트")
    return data


def generate_quiz(context: dict, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_quiz_prompt(context)

    max_tokens = min(8000, 800 + context["num_questions"] * 500)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_quiz_response(full_text)


def build_trend_prompt(context: dict) -> str:
    if context.get("interest_hint"):
        interest_line = f"- 관심 힌트: {context['interest_hint']}"
    else:
        interest_line = "- 관심 힌트: 특별히 없음, 컴퓨터공학 전반 기준으로 판단"

    return f"""당신은 컴퓨터공학 계열 진로/기술 트렌드 분석 전문가입니다.

학생 정보:
- 학과: {context['department']}
- 학년: {context['year']}
{interest_line}

이 학생은 아직 구체적인 목표가 없어서 막막한 상태입니다. 웹 검색을 통해 최근 채용 시장과 기술 트렌드를 조사한 뒤, 이 학생에게 맞는 방향을 추천하세요.

요구사항:
1. 웹 검색으로 최근(가능한 한 최신) 채용 동향, 기술 트렌드, 수요가 높은 직무를 확인하세요.
2. 확인한 정보에 근거해서만 추천하고, 근거 없는 트렌드를 지어내지 마세요.
3. 서로 다른 성격의 방향 3개를 추천하세요 (예: 특정 기술 분야, 특정 직무, 신흥 분야 등 겹치지 않게).
4. 각 추천마다 왜 지금 유망한지 검색으로 확인한 근거를 간단히 밝히세요.

검색과 판단을 마친 뒤, 반드시 아래 JSON 형식으로만 최종 응답하세요. JSON 앞뒤에 다른 설명이나 코드블록 마크다운을 붙이지 마세요:

{{
  "analysis": "현재 시장 상황에 대한 2~3문장 요약",
  "recommendations": [
    {{"title": "추천 방향 이름", "reason": "이 학생에게 맞는 이유", "evidence": "검색으로 확인한 트렌드 근거"}}
  ]
}}"""


def parse_trend_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    if "recommendations" not in data or not isinstance(data["recommendations"], list) or len(data["recommendations"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'recommendations' 목록이 없습니다:\n{data}")
    for rec in data["recommendations"]:
        if "title" not in rec or "reason" not in rec or "evidence" not in rec:
            raise ValueError(f"추천 항목 형식이 올바르지 않습니다: {rec}")

    data.setdefault("analysis", "")
    return data


def generate_trend_recommendations(context: dict, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_trend_prompt(context)

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
        messages=[{"role": "user", "content": prompt}],
    )

    # 출처 인용(citation)이 붙으면 최종 답변이 여러 개의 text 블록으로 쪼개져서 온다.
    # "마지막 검색 도구 사용 이후에 나온 text 블록들"을 전부 이어붙여야 완전한 최종 답변이 된다.
    # (그 이전 블록들은 "~를 검색해보겠습니다" 같은 중간 설명이라 제외)
    content = response.content
    last_tool_idx = -1
    for idx, block in enumerate(content):
        if getattr(block, "type", None) in ("server_tool_use", "web_search_tool_result"):
            last_tool_idx = idx

    final_blocks = content[last_tool_idx + 1:]
    text_parts = [block.text for block in final_blocks if getattr(block, "type", None) == "text"]
    full_text = "".join(text_parts)

    return parse_trend_response(full_text)
