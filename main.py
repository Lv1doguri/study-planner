"""
study_planner/main.py

목표(예: '보안')를 선택하면 해당 커리큘럼을 순서대로 보여주고,
완료한 단계를 체크하면 다음에 실행했을 때도 기억하는 CLI 프로그램.

구조:
- data/curricula.json : 목표별 커리큘럼 데이터 (내용을 수정/추가하려면 이 파일만 편집하면 됨)
- data/progress.json  : 사용자가 완료 체크한 기록 (프로그램이 자동 생성/갱신)
"""

import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRICULA_PATH = os.path.join(BASE_DIR, "data", "curricula.json")
PROGRESS_PATH = os.path.join(BASE_DIR, "data", "progress.json")


def load_curricula():
    with open(CURRICULA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_progress():
    # 진도 파일이 없으면(첫 실행) 빈 상태로 시작
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


def find_or_generate_curriculum(goal_text, curricula):
    """DB에 정확히 일치하는 목표가 있으면 그걸 쓰고, 없으면 LLM으로 생성해 DB에 저장(캐싱)한다."""
    goal_text = goal_text.strip()

    for key in curricula:
        if key == goal_text:
            return key, curricula

    print(f"\n'{goal_text}'는 등록된 트랙에 없습니다. AI로 새로 생성을 시도합니다...")
    try:
        from llm_recommender import generate_curriculum_via_llm
        generated = generate_curriculum_via_llm(goal_text)
    except Exception as e:
        print(f"생성 실패: {e}")
        print("ANTHROPIC_API_KEY 환경변수 설정 여부와 'pip install anthropic' 설치 여부를 확인하세요.")
        return None, curricula

    curricula[goal_text] = generated
    save_curricula(curricula)
    print(f"'{goal_text}' 트랙을 새로 생성해 저장했습니다. (다음부터는 API 재호출 없이 바로 조회됩니다)")
    return goal_text, curricula


def list_goals(curricula):
    print("\n=== 선택 가능한 목표 ===")
    for i, goal in enumerate(curricula.keys(), 1):
        print(f"{i}. {goal} - {curricula[goal]['description']}")


def show_curriculum(goal, curricula, progress):
    steps = curricula[goal]["steps"]
    completed_ids = set(progress.get(goal, []))

    print(f"\n=== '{goal}' 커리큘럼 ({len(completed_ids)}/{len(steps)} 완료) ===")
    for step in steps:
        mark = "[x]" if step["id"] in completed_ids else "[ ]"
        print(f"{mark} {step['id']}. {step['title']}")
        print(f"      - {step['detail']}")
        if step.get("resources"):
            print(f"      추천 자료: {', '.join(step['resources'])}")


def mark_complete(goal, step_id, curricula, progress):
    valid_ids = {s["id"] for s in curricula[goal]["steps"]}
    if step_id not in valid_ids:
        print(f"'{goal}' 트랙에 {step_id}번 단계가 없습니다.")
        return progress

    completed = set(progress.get(goal, []))
    completed.add(step_id)
    progress[goal] = sorted(completed)
    save_progress(progress)
    print(f"{step_id}번 단계를 완료로 표시했습니다.")
    return progress


def choose_goal(curricula):
    goals = list(curricula.keys())
    while True:
        raw = input("목표 번호를 입력하세요 (숫자): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(goals):
            return goals[int(raw) - 1]
        print("올바른 번호를 입력해주세요.")


def main():
    curricula = load_curricula()
    progress = load_progress()

    while True:
        print("\n========== 학습 커리큘럼 추천 프로그램 ==========")
        print("1. 목표 목록 보기")
        print("2. 커리큘럼 보기")
        print("3. 단계 완료 체크")
        print("4. 종료")
        print("5. 새 목표 입력하기 (DB에 없으면 AI가 생성, API 키 필요)")
        choice = input("선택: ").strip()

        if choice == "1":
            list_goals(curricula)

        elif choice == "2":
            list_goals(curricula)
            goal = choose_goal(curricula)
            show_curriculum(goal, curricula, progress)

        elif choice == "3":
            list_goals(curricula)
            goal = choose_goal(curricula)
            show_curriculum(goal, curricula, progress)
            raw_id = input("완료한 단계 번호를 입력하세요: ").strip()
            if raw_id.isdigit():
                progress = mark_complete(goal, int(raw_id), curricula, progress)
            else:
                print("숫자를 입력해주세요.")

        elif choice == "4":
            print("프로그램을 종료합니다.")
            break

        elif choice == "5":
            goal_text = input("목표를 자유롭게 입력하세요 (예: 클라우드 엔지니어): ").strip()
            if not goal_text:
                print("빈 값은 입력할 수 없습니다.")
                continue
            goal, curricula = find_or_generate_curriculum(goal_text, curricula)
            if goal is not None:
                show_curriculum(goal, curricula, progress)

        else:
            print("1~5 중에서 선택해주세요.")


if __name__ == "__main__":
    main()
