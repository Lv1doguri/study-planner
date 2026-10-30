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

# anthropic 패키지가 없어도 나머지 프로그램은 쓸 수 있도록 임포트를 지연시킴
def _get_client():
    try:
        from anthropic import Anthropic
    except ImportError as e:
        raise RuntimeError(
            "anthropic 패키지가 설치되어 있지 않습니다. 'pip install anthropic'을 실행하세요."
        ) from e
    return Anthropic()  # ANTHROPIC_API_KEY 환경변수를 자동으로 읽음


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
    """LLM이 반환한 텍스트에서 JSON 부분만 뽑아 파싱한다.
    코드블록(```json ... ```)으로 감싸서 응답하는 경우가 많아 그 부분을 먼저 제거한다."""
    cleaned = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM 응답을 JSON으로 파싱하지 못했습니다: {e}\n원본 응답:\n{text}")

    # 최소한의 형식 검증 (필수 키가 없으면 이후 로직에서 조용히 깨지는 것을 방지)
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

    # content는 여러 블록일 수 있으므로 text 타입만 모아 합친다
    text_parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
    full_text = "\n".join(text_parts)

    return parse_llm_response(full_text)
