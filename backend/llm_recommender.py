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
from datetime import datetime, timedelta

def _get_client():
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic 패키지가 설치되어 있지 않습니다. 'pip install anthropic'을 실행하세요."
        ) from e
    return Anthropic()


def build_prompt(goal_text: str) -> str:
    return f"""당신은 전공에 관계없이 모든 대학생의 진로 학습 커리큘럼을 설계하는 전문가입니다.
목표: "{goal_text}"

목표의 분야가 무엇이든(전공 지식, 체육/예술 실기, 자격증, 공무원 시험 등) 그 분야의 특성에 맞게
이 목표를 달성하기 위한 학습 커리큘럼을 6~10단계로 설계하세요.
각 단계는 실제로 존재하는, 검증 가능한 학습 자료/사이트/서적/훈련 방법만 언급하세요.
확실하지 않은 자격증명, 사이트명, 도서명은 만들어내지 말고 일반적인 카테고리로만 서술하세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "description": "이 트랙에 대한 한 문장 설명",
  "steps": [
    {{"id": 1, "title": "단계 제목", "detail": "구체적 설명", "resources": ["자료1", "자료2"]}}
  ]
}}"""


def parse_llm_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
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
- 학습 과목: {context['subject']}
- 계획을 세울 기간: 총 {context['days_remaining']}일

아래는 학생이 직접 제공한 이 과목의 상세 정보(비중, 시험범위/진도 등)입니다.
이 정보를 최우선 근거로 사용하세요. 여기 없는 세부사항(정확한 교재 챕터 번호 등)을 추측해서 확정적으로 쓰지 마세요:
---
{context['course_details']}
---

요구사항:
1. 정확히 {context['days_remaining']}일치 계획을 만드세요 (Day 1 ~ Day {context['days_remaining']}).
2. 위에 제공된 과목 정보(범위, 비중)를 최대한 정확히 반영하세요.
3. 이 계획은 "{context['subject']}" 한 과목에 대한 것입니다. 모든 날짜의 "subject" 필드는
   항상 정확히 "{context['subject']}"로 고정하세요 — 다른 이름으로 바꾸거나 세부 단원명으로
   대체하지 마세요(세부 단원/주제는 "topic" 필드에 쓰세요).
4. 시험 범위가 있다면 뒤로 갈수록 "선행학습 → 문제풀이 → 모의고사 → 총복습" 순으로 실전 대비 비중을 높이세요.
5. 확실하지 않은 책/사이트명을 지어내지 말고, 학생이 제공한 정보와 일반적으로 알려진 개념 이름만 사용하세요.
6. "{context['subject']}"에 어울리는 이모지를 하나 정해서, 플랜 전체에서 항상 같은 이모지를 쓰세요.
7. "concepts"는 완전한 문장이 아니라 그날 다룰 핵심 용어/개념을 짧은 키워드로 나열하세요
   (예: "abstract class", "abstract method"). "~를 학습한다" 같은 서술형 문장은 쓰지 마세요.
8. 직접 코드를 짜보거나 손으로 만들어보는 게 도움이 되는 주제라면 "practice"에 구체적인 실습 과제를
   적으세요. 클래스 구조나 코드 골격처럼 여러 줄로 보여주는 게 더 명확하면 줄바꿈(\\n)을 사용해
   여러 줄로 작성하세요. 실습이 필요 없는 주제라면 "practice" 필드 자체를 넣지 마세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "plan_title": "이 플랜에 대한 한 줄 제목",
  "days": [
    {{
      "day": 1,
      "subjects": [
        {{
          "subject": "과목명",
          "emoji": "그 과목을 대표하는 이모지 1개",
          "topic": "그 날 다룰 핵심 주제 (짧은 제목)",
          "concepts": ["핵심 용어1", "핵심 용어2"],
          "practice": "직접 해볼 실습 과제 (선택, 없으면 이 필드를 아예 넣지 마세요)"
        }}
      ]
    }}
  ]
}}"""


def parse_daily_plan_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    if "days" not in data or not isinstance(data["days"], list) or len(data["days"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'days' 목록이 없습니다:\n{data}")

    subject_emoji = {}
    for day in data["days"]:
        if "day" not in day or "subjects" not in day or not isinstance(day["subjects"], list):
            raise ValueError(f"날짜 항목 형식이 올바르지 않습니다: {day}")
        for subj in day["subjects"]:
            if "subject" not in subj or "topic" not in subj or "concepts" not in subj:
                raise ValueError(f"과목 항목 형식이 올바르지 않습니다: {subj}")
            if not isinstance(subj["concepts"], list) or len(subj["concepts"]) == 0:
                raise ValueError(f"'concepts'가 비어 있습니다: {subj}")
            subj.setdefault("emoji", "📘")
            subj.setdefault("practice", None)

            # 모델이 이모지를 매번 다르게 골라도, 같은 과목은 화면에서 항상 같은 이모지로 보이게 고정한다.
            first_emoji = subject_emoji.setdefault(subj["subject"], subj["emoji"])
            subj["emoji"] = first_emoji

    data.setdefault("plan_title", "맞춤 학습 플랜")
    return data


def _attach_dates(plan: dict, start_date: str) -> None:
    start = datetime.strptime(start_date, "%Y-%m-%d")
    for day in plan["days"]:
        current = start + timedelta(days=day["day"] - 1)
        day["date"] = f"{current.month}월 {current.day}일"


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

    plan = parse_daily_plan_response(full_text)
    _attach_dates(plan, context["start_date"])
    return plan


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

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

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
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
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

    # 코드가 포함된 문제(질문 지문 자체가 여러 줄 코드인 경우)는 문항 하나가 훨씬 길어지므로
    # 문항당 배정량을 넉넉하게 잡는다 — 예전엔 800+500*N이라 코드 문제 5개에서도 잘렸었다.
    max_tokens = min(16000, 1500 + context["num_questions"] * 800)

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
        interest_line = f"- 관심 힌트: 특별히 없음, {context['department']} 전공 전반 기준으로 판단"

    return f"""당신은 전공에 관계없이 다양한 분야의 진로/채용 트렌드 분석 전문가입니다.

학생 정보:
- 학과: {context['department']}
- 학년: {context['year']}
{interest_line}

이 학생은 아직 구체적인 목표가 없어서 막막한 상태입니다. 웹 검색을 통해 이 학과·전공과 관련된
최근 채용 시장, 산업/직무 트렌드를 조사한 뒤, 이 학생에게 맞는 방향을 추천하세요. IT/기술
분야로 한정하지 말고, 이 학과 졸업생들이 실제로 진출하는 분야를 폭넓게 고려하세요.

요구사항:
1. 웹 검색으로 이 학과·전공과 관련된 최근(가능한 한 최신) 채용 동향, 산업 트렌드, 수요가 높은
   직무/진로를 확인하세요.
2. 확인한 정보에 근거해서만 추천하고, 근거 없는 트렌드를 지어내지 마세요.
3. 서로 다른 성격의 방향 3개를 추천하세요 (예: 특정 분야, 특정 직무, 신흥 분야 등 겹치지 않게).
4. 각 추천마다 왜 지금 유망한지 검색으로 확인한 근거를 간단히 밝히세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

검색과 판단을 마친 뒤, 반드시 아래 JSON 형식으로만 최종 응답하세요. JSON 앞뒤에 다른 설명이나 코드블록 마크다운을 붙이지 마세요:

{{
  "analysis": "현재 시장 상황에 대한 2~3문장 요약",
  "recommendations": [
    {{"title": "추천 방향 이름", "reason": "이 학생에게 맞는 이유", "evidence": "검색으로 확인한 트렌드 근거"}}
  ]
}}"""


def parse_trend_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
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


def build_certification_prompt(goal_text: str) -> str:
    return f"""당신은 채용 시장과 자격증/역량 요건에 정통한 커리어 어드바이저입니다.
목표(직무/분야): "{goal_text}"

이 목표에 종사하는 사람들이 실제로 갖추고 있는 자격증과 핵심 역량을 정리하세요.
확실하지 않은 자격증명이나 역량을 지어내지 말고, 실제로 존재하고 검증 가능한 것만 언급하세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "certifications": [
    {{"name": "자격증 이름", "reason": "이 직무에 왜 도움이 되는지"}}
  ],
  "core_skills": [
    {{"name": "핵심 역량 이름", "reason": "왜 중요한지"}}
  ]
}}"""


def parse_certification_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    for key in ("certifications", "core_skills"):
        if key not in data or not isinstance(data[key], list) or len(data[key]) == 0:
            raise ValueError(f"LLM 응답에 유효한 '{key}' 목록이 없습니다:\n{data}")
        for item in data[key]:
            if "name" not in item or "reason" not in item:
                raise ValueError(f"항목 형식이 올바르지 않습니다: {item}")

    return data


def generate_certifications(goal_text: str, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_certification_prompt(goal_text)

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_certification_response(full_text)


def build_study_list_prompt(context: dict) -> str:
    return f"""당신은 대학생의 강의자료를 분석해 예습/복습 계획을 짜주는 학습 코치입니다.

과목: {context['subject']}

아래는 강의계획서 또는 강의자료(PPT/PDF)에서 추출한 텍스트입니다. 이 내용만 근거로 사용하고,
여기 없는 내용을 새로 지어내지 마세요:
---
{context['material_text']}
---

요구사항:
1. 이 자료를 바탕으로 "예습 리스트"(수업 전에 미리 훑어보면 좋은 항목)와 "복습 리스트"(수업 후
   확실히 익혀야 할 항목)를 나눠서 만드세요.
2. 각 리스트는 3~8개 항목으로 구성하세요.
3. 각 항목은 자료에 나온 구체적인 주제/개념 이름을 사용하고, 왜 예습 또는 복습이 필요한지 간단히
   설명하세요.
4. 자료에 없는 챕터 번호, 교재명, 페이지 등을 추측해서 확정적으로 쓰지 마세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

반드시 아래 JSON 형식으로만 응답하세요. 다른 설명 텍스트, 코드블록 마크다운(```)은 절대 포함하지 마세요:

{{
  "study_title": "이 자료에 대한 한 줄 제목",
  "preview_items": [
    {{"title": "예습 항목 제목", "detail": "구체적 설명"}}
  ],
  "review_items": [
    {{"title": "복습 항목 제목", "detail": "구체적 설명"}}
  ]
}}"""


def parse_study_list_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    for key in ("preview_items", "review_items"):
        if key not in data or not isinstance(data[key], list) or len(data[key]) == 0:
            raise ValueError(f"LLM 응답에 유효한 '{key}' 목록이 없습니다:\n{data}")
        for item in data[key]:
            if "title" not in item or "detail" not in item:
                raise ValueError(f"항목 형식이 올바르지 않습니다: {item}")

    data.setdefault("study_title", "강의자료 분석 결과")
    return data


def generate_study_list(context: dict, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_study_list_prompt(context)

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_study_list_response(full_text)


def build_lecture_analysis_prompt(context: dict) -> str:
    return f"""당신은 이 과목을 실제로 가르치는 교수입니다. 학생이 올린 강의자료를 교수의
시각에서 설명하고, 시험에 나올 만한 부분을 예상해주세요.

과목: {context['subject']}

아래는 강의자료(PPT/PDF)에서 추출한 텍스트입니다. 이 내용에만 근거하세요:
---
{context['material_text']}
---

**중요**: 아래 JSON 필드를 반드시 이 순서대로("analysis_title" → "subject_emoji" → "summary" →
"key_points" → "expected_questions" → "code_snippets" → "explanation") 작성하세요.
"explanation"이 가장 길고 분량이 예측하기 어려우니 항상 맨 마지막에 쓰고, 나머지 필드를 먼저
전부 완성하세요 — 이렇게 해야 응답이 길어져도 시험 대비에 더 중요한 정보(요약/핵심포인트/
예상문제/코드리뷰)가 먼저 확실히 완성됩니다.

요구사항:
0. "subject_emoji": "{context['subject']}"을(를) 대표하는 이모지 1개.
1. "summary": 이 자료 전체를 3~5문장으로 압축한 핵심 요약.
2. "key_points": 시험에 나올 가능성이 높은 핵심 포인트를 3~7개 골라, 자료 안에서 반복되거나
   강조되거나 실습과 연결된 부분 등 실제 근거를 들어 왜 중요한지 설명하세요. 코드가 있다면
   그 코드에서 다뤄지는 개념(예: 특정 메서드, 상속 구조, 연산 로직)도 최소 1개 포함하세요.
3. "expected_questions": 이 자료를 바탕으로 실제 시험에 나올 법한 예상 문제를 3~6개
   만드세요. 객관식이 아니라 서술형/개념 설명형으로 만들고, 왜 이 문제가 나올 것 같은지와
   답변에 꼭 들어가야 할 핵심 키워드를 같이 적으세요. **자료에 코드가 있다면 그 코드를 직접
   이해했는지 확인하는 문제(예: 실행 결과 예측, 특정 부분 수정, 빈칸 채우기, 코드가 왜 이렇게
   동작하는지 설명)를 최소 1~2개 포함하세요.**
4. "code_snippets": 자료 안에 프로그래밍 코드(Java, Python, C++ 등)가 있다면 **빠짐없이
   전부** 이 배열에 담으세요. 코드가 없는 자료라면 빈 배열 `[]`로 두세요. 각 항목은:
   - "title": 이 코드가 무엇에 대한 코드인지 짧은 제목
   - "language": 프로그래밍 언어 (예: "java", "python", "cpp")
   - "code": 원본 코드를 그대로. **들여쓰기, 줄바꿈, 세미콜론, 괄호까지 한 글자도 바꾸거나
     생략하지 말고 원본 그대로** 옮기세요 — 학생이 그대로 복사해서 써도 되는 수준이어야
     합니다. 확실히 안 보이는 글자를 추측해서 지어내지 마세요.
   - "review": 이 코드에 대한 리뷰. 무엇을 하는 코드인지, 왜 이렇게 작성했는지(설계 의도),
     실행하면 어떤 결과가 나오는지, 시험에 나온다면 어떤 부분이 헷갈릴 만한지 설명하세요.
5. "explanation": 교수가 학생에게 직접 설명하듯이 이 자료의 핵심 개념을 설명하세요. 하나의
   거대한 문단으로 몰아쓰지 말고, 자연스러운 소주제 4~8개로 나눠서 각각 "emoji"(그 소주제를
   대표하는 이모지 1개), "heading"(짧은 소제목), "body"(그 소주제에 대한 설명)로 구성하세요.
   **각 body는 반드시 1~2문장으로만 짧게 쓰세요 — 길게 늘어놓지 마세요.** 코드 이야기가
   나올 때도 코드 원문을 여기 다시 옮겨 적지 말고 "아래 코드 리뷰 참고"처럼 개념 위주로만
   짧게 언급하세요 — 코드 원문과 줄 단위 리뷰는 위 4번 "code_snippets"에 이미 있습니다.

확실하지 않은 내용을 지어내지 말고, 자료에 실제로 없는 내용을 "시험에 나올 것"이라고
단정하지 마세요 — 자료 안에서 강조·반복되거나 실습과 연결된 부분을 근거로만 예상하세요.

**JSON 문자열 값 안에서는 강조용으로 큰따옴표(")를 쓰지 마세요** — 대신 작은따옴표(')나 「」를
쓰세요. 큰따옴표가 문자열 값 안에 그대로 들어가면 JSON 파싱이 깨집니다.
**배열이나 객체의 마지막 항목 뒤에는 쉼표(,)를 붙이지 마세요** (trailing comma) — 마지막
항목과 닫는 괄호(}} 또는 ]) 사이에는 쉼표 없이 바로 이어져야 합니다.

반드시 아래 JSON 형식으로만, 필드 순서도 그대로 지켜서 응답하세요. 다른 설명 텍스트,
코드블록 마크다운(```)은 절대 포함하지 마세요(단, "code" 필드 안의 코드 자체는 원본 그대로
넣으세요):

{{
  "analysis_title": "이 자료에 대한 한 줄 제목",
  "subject_emoji": "과목을 대표하는 이모지 1개",
  "summary": "핵심 요약",
  "key_points": [
    {{"title": "포인트 제목", "reason": "왜 중요한지/예상 근거"}}
  ],
  "expected_questions": [
    {{"question": "예상 문제", "reason": "왜 나올 것 같은지", "answer_direction": "답변에 들어가야 할 핵심 키워드/방향"}}
  ],
  "code_snippets": [
    {{"title": "코드 제목", "language": "java", "code": "원본 코드 그대로", "review": "코드 리뷰"}}
  ],
  "explanation": [
    {{"emoji": "소주제를 대표하는 이모지 1개", "heading": "소주제 제목", "body": "그 소주제에 대한 교수 입장에서의 짧은 설명 (1~2문장)"}}
  ]
}}"""


def parse_lecture_analysis_response(text: str) -> dict:
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    # 모델이 배열/객체의 마지막 항목 뒤에 쉼표를 남기는 경우가 있다(trailing comma) —
    # JSON 표준은 이를 허용하지 않고 json.loads도 strict=False로는 못 잡으므로, 파싱 전에
    # ", }"나 ", ]" 형태를 미리 정리한다.
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)

    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    # 필드 순서상 앞쪽(summary/key_points/expected_questions)은 응답이 중간에 짧게 끊겨도
    # 거의 항상 완성되어 있으므로 엄격히 검증한다. 뒤쪽(code_snippets/explanation)은 응답이
    # 길어질수록 잘리기 쉬운 자리라, 아예 없거나 비어 있어도 에러 대신 빈 값으로 채워서
    # 나머지 결과라도 그대로 보여준다.
    if "summary" not in data or not isinstance(data["summary"], str) or not data["summary"].strip():
        raise ValueError(f"LLM 응답에 유효한 'summary'가 없습니다:\n{data}")

    if "key_points" not in data or not isinstance(data["key_points"], list) or len(data["key_points"]) == 0:
        raise ValueError(f"LLM 응답에 유효한 'key_points' 목록이 없습니다:\n{data}")
    for point in data["key_points"]:
        if "title" not in point or "reason" not in point:
            raise ValueError(f"핵심 포인트 형식이 올바르지 않습니다: {point}")

    if (
        "expected_questions" not in data
        or not isinstance(data["expected_questions"], list)
        or len(data["expected_questions"]) == 0
    ):
        raise ValueError(f"LLM 응답에 유효한 'expected_questions' 목록이 없습니다:\n{data}")
    for q in data["expected_questions"]:
        if "question" not in q or "reason" not in q:
            raise ValueError(f"예상 문제 형식이 올바르지 않습니다: {q}")
        q.setdefault("answer_direction", "")

    if not isinstance(data.get("code_snippets"), list):
        data["code_snippets"] = []
    data["code_snippets"] = [
        s for s in data["code_snippets"] if isinstance(s, dict) and "title" in s and "code" in s
    ]
    for snippet in data["code_snippets"]:
        snippet.setdefault("language", "")
        snippet.setdefault("review", "")

    if not isinstance(data.get("explanation"), list):
        data["explanation"] = []
    data["explanation"] = [
        section
        for section in data["explanation"]
        if isinstance(section, dict) and "heading" in section and "body" in section
    ]
    for section in data["explanation"]:
        section.setdefault("emoji", "📌")

    data.setdefault("analysis_title", "강의자료 심층 분석")
    data.setdefault("subject_emoji", "📘")
    return data


def generate_lecture_analysis(context: dict, model: str = "claude-sonnet-5") -> dict:
    client = _get_client()
    prompt = build_lecture_analysis_prompt(context)

    response = client.messages.create(
        model=model,
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}],
    )

    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_lecture_analysis_response(full_text)
