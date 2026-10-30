# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에게 제공하는 가이드입니다.

## 저장소 개요

이 저장소에는 **같은 앱(전공 무관 대학생 맞춤형 학습 커리큘럼 추천 프로그램)의 세 가지 세대**가
서로를 대체하지 않고 나란히 존재합니다. `backend/`의 프롬프트는 특정 전공에 종속되지 않도록
일반화되어 있으므로(예: 체육학과 목표로도 실제 검증됨), 새 프롬프트를 작성/수정할 때 "컴퓨터공학과"
같은 특정 전공을 기본값으로 가정하지 마세요:

- `main.py`, `llm_recommender.py`, `requirements.txt` (저장소 루트) — 원조 터미널/CLI 버전.
- `study_planner_web/` — Streamlit 웹 버전. CLI와 동일한 `curricula.json`/`progress.json` 로직에
  XP/레벨업(`data/xp.json`), 일별 플랜 생성기, 퀴즈 생성기, "트렌드" 추천기(Claude의 웹 검색
  도구 사용)가 추가되어 있습니다. 모든 UI와 로직이 `app.py` 한 파일에 들어 있습니다.
- `backend/` + `frontend/` — **현재 실제로 개발 중인 버전.** `backend/`는 *동일한*
  `llm_recommender.py` 로직을 감싼 얇은 FastAPI 래퍼이고(`study_planner_web/`에서 복사해와
  일별 플랜/퀴즈/트렌드 생성기를 추가한 버전), `frontend/`는 이를 REST로 호출하는
  React + Vite + Tailwind SPA입니다.

작업할 때는 사용자가 실제로 어느 세대를 말하는지 먼저 확인하세요 — `backend/`와
`study_planner_web/` 둘 다 `llm_recommender.py`라는 같은 이름의 파일을 갖고 있지만 내용이
갈라져 있고(`study_planner_web` 쪽에는 주석이 더 많고, `backend` 쪽은 주석이 빠짐), `main.py`도
저장소 루트(CLI)와 개념적으로 `backend/main.py`(FastAPI) 양쪽에 존재합니다 — 엉뚱한 파일을
고치지 않도록 주의하세요. Claude 프롬프트/파싱 공통 로직을 고쳐야 한다면, 세 세대 사이에
공유되는 패키지가 없으므로 현재는 `backend/llm_recommender.py`와
`study_planner_web/llm_recommender.py`에 각각 따로 반영해야 합니다.

별다른 지시가 없다면 새 기능 작업은 `backend/` + `frontend/`를 대상으로 한다고 가정하세요.

전체 기능 로드맵(어디까지 만들었고 다음에 뭘 만들지)은 `ROADMAP.md`를 참고하세요.

## 커맨드

### 프론트엔드 (`frontend/`)
```
npm install       # 의존성 설치
npm run dev        # Vite 개발 서버, http://localhost:5173
npm run build       # 프로덕션 빌드
npm run lint        # oxlint
npm run preview      # 프로덕션 빌드 미리보기
```
`frontend/`에는 테스트 설정이 없습니다.

### 백엔드 (`backend/`)
```
pip install -r requirements.txt
export ANTHROPIC_API_KEY="..."
uvicorn main:app --reload --port 8000
```
`backend/`에는 테스트 설정이 없습니다.

### Streamlit 버전 (`study_planner_web/`)
```
pip install -r requirements.txt
streamlit run app.py
```

### CLI 버전 (저장소 루트)
```
pip install -r requirements.txt
python main.py
```

## 아키텍처

### backend/frontend (현재 버전)

- `backend/main.py`는 FastAPI 앱으로, Claude 호출 엔드포인트(`/api/curriculum`,
  `/api/daily-plan`, `/api/quiz`, `/api/trend`, `/api/study-list`, `/api/certifications`,
  `/api/lecture-analysis`)는
  `backend/llm_recommender.py`의 동명 함수를 호출하고 실패 시 HTTP 500으로 재발생시키는 얇은
  try/except 래퍼입니다. 파일 처리 엔드포인트 `/api/extract-material`은 1순위로
  `backend/slide_vision.py`를 통해 PDF/PPT 슬라이드를 이미지로 렌더링해 Claude Vision에게
  보여주고, 표·다이어그램·그래프 안의 요소·관계까지 상세한 텍스트로 옮겨 적게 합니다(응답에
  `used_vision: true`). PDF는 PyMuPDF(`fitz`)로 바로 렌더링하고, PPTX는 LibreOffice(`soffice`,
  `SOFFICE_CANDIDATES`에서 경로 탐색)로 먼저 PDF 변환 후 렌더링합니다 — LibreOffice가 없거나
  변환/Vision 호출이 실패하면 예외를 조용히 삼키고 `text_extraction.py`의 순수 텍스트 추출로
  대체합니다(`used_vision: false`). `text_extraction.py`의 PPTX 추출(순수 텍스트 fallback
  경로)은 슬라이드 도형을 재귀적으로 순회하면서 표(`shape.has_table`)와 그룹 도형
  (`MSO_SHAPE_TYPE.GROUP`) 안까지 들어가서 텍스트를 뽑습니다 — 이 둘을 빼먹으면(과거에 실제로
  그랬음) 표나 다이어그램이 많은 실제 강의자료에서 내용이 통째로 누락됩니다. 진행 상황/XP/
  활동 기록/과목별 커리큘럼
  엔드포인트(`/api/progress`, `/api/progress/toggle`, `/api/xp`, `/api/xp/add`, `/api/activity`,
  `/api/custom-curriculum*`)는 `backend/storage.py`를 감싸는 순수 CRUD입니다. CORS는
  `http://localhost:5173`(Vite 개발 서버)로 고정되어 있습니다.
  `/api/custom-curriculum/import-daily-plan`은 `DailyPlanTab`이 플랜 생성 직후 자동으로 호출해서
  플랜의 각 (날짜, 과목, 주제)를 그 과목의 체크리스트 항목("Day N (날짜) · 주제")으로 넣어줍니다
  — 제목이 완전히 같은 항목이 이미 있으면 건너뛰어서 같은 플랜을 다시 생성해도 중복이 안 쌓입니다.
  **주의**: `/api/curriculum`(AI 커리큘럼 생성)과 `/api/progress`/`/api/progress/toggle`은
  React UI에서 더 이상 호출하지 않습니다 — "과목별 커리큘럼" 탭이 AI 자동 생성 방식에서
  사용자가 직접 과목·항목을 입력하는 `/api/custom-curriculum*` 방식으로 바뀌었기 때문입니다
  (2026-08-30). 백엔드에는 일부러 남겨뒀으니(다른 용도로 재사용하거나 API로 직접 테스트할 수
  있게) 사용자가 명시적으로 삭제해달라고 하기 전엔 지우지 마세요.
- `backend/llm_recommender.py`에 모든 Claude 프롬프팅 로직이 들어 있습니다. 기능(커리큘럼,
  일별 플랜, 퀴즈, 트렌드, 예습/복습 리스트, 자격증·역량 추천, 강의자료 교수 시점 분석)별로
  `build_*_prompt` /
  `parse_*_response` / `generate_*` 세 함수가 한 세트를 이룹니다. 모든 프롬프트는 엄격한
  JSON 출력(마크다운 코드펜스 금지)을 요구하고, 모든 파서는 정규식으로 코드펜스를 제거한 뒤
  `json.loads(cleaned, strict=False)`로 파싱하고 필수 키를 직접 검증합니다.
  **`strict=False`가 중요합니다** — 모델이 긴 설명 문단을 여러 줄로 쓰라는 지시를 따르다가
  JSON 문자열 안에 `\n`으로 이스케이프하지 않고 실제 개행문자를 그대로 넣는 경우가 있는데,
  기본(strict) 모드는 이런 제어문자를 오류로 처리해 파싱 자체가 실패합니다(실제로 발생한
  버그, 2026-08-30 수정). 새 `parse_*_response` 함수를 추가할 때도 반드시 이 옵션을
  유지하세요 — `generate_lecture_analysis`의 `code_snippets`(원본 코드를 들여쓰기·줄바꿈
  그대로 담는 필드)처럼 응답에 실제 개행이 많이 섞이는 필드가 있으면 이 옵션이 특히
  중요합니다. `code_snippets`는 산문 설명(`explanation`)과 분리되어 있습니다 — 프롬프트가
  "코드를 explanation에 다시 옮기지 말고 code_snippets에만 원본 그대로 담으라"고 명시하는데,
  이는 코드가 산문 안에 섞이면 들여쓰기가 깨지기 쉽고 화면에서 모노스페이스로 따로 보여주기도
  어렵기 때문입니다. 트렌드 생성기는 Claude의
  `web_search_20250305` 서버 도구를 사용하는데, 최종 답변을 마지막
  `server_tool_use`/`web_search_tool_result` 블록 *이후*에 나온 text 블록들만 모아서
  재조립해야 합니다(그 이전 블록들은 "~를 검색해보겠습니다" 같은 모델의 중간 설명이라 답변이
  아닙니다). 주의: `generate_curriculum_via_llm`은 결과를 캐싱하지 않습니다 — CLI/Streamlit
  버전과 달리 `backend/main.py`는 `curricula.json`에 쓰지 않으므로, 같은 목표로 다시 호출하면
  Claude를 다시 호출해 매번 새로 생성합니다.
- `backend/storage.py`는 단계 완료 체크(`backend/data/progress.json`), XP
  (`backend/data/xp.json`), 활동 기록(`backend/data/activity_log.json`), 사용자가 직접 쓰는
  과목별 커리큘럼(`backend/data/custom_curriculum.json`)을 저장하는 락 없는 JSON 파일
  저장소입니다. 저장소 루트의 `data/progress.json`(CLI/Streamlit용)과는 별개의 파일이니
  혼동하지 마세요. 레벨 계산은 `total_xp // 150 + 1`, 항목 체크 시 ±20 XP, 퀴즈 정답 1개당
  +10 XP입니다. XP가 실제로 바뀌는 이벤트(항목 완료, 퀴즈 채점)와 콘텐츠 생성 이벤트(일별
  플랜, 강의자료 분석)는 `log_activity`로 활동 기록에 남습니다 — 항목 체크 *해제*는 새 기록을
  남기는 대신, `remove_last_activity_by_title`로 그 항목의 "완료" 기록 중 가장 최근 것 하나를
  활동 기록에서 지웁니다(제목이 완전히 같은 걸로 매칭). 그래서 체크했다 바로 취소해도 대시보드
  "최근 활동"에 흔적이 안 남습니다 — 체크 해제 후 XP만 깎고 기록은 그대로 두면 "체크했다
  취소했는데 대시보드엔 계속 완료로 남아있다"는 혼란스러운 상태가 되기 때문에 이렇게
  처리합니다(실제로 이 문제가 있었음, 2026-08-30에 수정). `GET /api/activity?days=N`으로 최근
  N일 기록을 최신순으로 가져올 수 있습니다. `custom_curriculum.json`은
  `{과목명: [{id, title, done}]}` 형태이며, id는 과목
  안에서만 유일(과목별로 1부터 증가)합니다.
- React 프론트엔드에는 공용 API 클라이언트나 base URL 설정이 없습니다. 각 컴포넌트/`App.jsx`가
  각자 `http://127.0.0.1:8000/api/...`를 인라인으로 하드코딩해 `fetch()`합니다. 백엔드의
  포트/호스트가 바뀌면 이 파일들을 모두 수정해야 합니다.
- `frontend/src/App.jsx`는 라우터 없이 `active` 상태(`dashboard` / `track` / `daily` /
  `material` / `quiz` / `trend`)만으로 탭을 전환하는 단일 페이지 컴포넌트이며,
  `frontend/src/components/`의 컴포넌트들을 렌더링합니다. `<div key={active}>`로 감싸져 있어서
  탭을 바꿀 때마다 이전 탭 컴포넌트는 완전히 unmount됩니다 — 그래서 각 탭이 들고 있는 생성
  결과(플랜/퀴즈/예습복습 리스트)는 로컬 `useState`만으로는 탭을 나갔다 오면 사라집니다(실제
  발생했던 버그, 아래 `usePersistedState` 참고). XP/레벨은 마운트 시 `GET /api/xp`로 가져와
  `xp` state에 저장하고, `refreshXp` 함수를 `onXpChange` prop으로 `TrackCurriculumTab`/
  `QuizTab`에 내려줘서 XP가 바뀔 때마다(항목 체크, 퀴즈 채점) 다시 불러옵니다. 레벨이 오르면
  화면 상단에 3초짜리 토스트가 뜹니다. "seed 전달 후 즉시 소비" 패턴이 두 곳에 있습니다:
  트렌드 탭에서 추천 항목을 선택하면 `subjectSeed`를 설정하고 Track 탭으로 전환하며
  (`onSelectGoal` prop — 커리어 방향 추천을 "과목명"으로 욱여넣는 것이라 완벽한 개념적 매칭은
  아니지만, 최소한 새 과목 이름 입력칸에 미리 채워주는 용도로 재사용), 강의자료 탭에서
  "미니테스트 만들기"를 누르면 `quizSeed`를 설정해 Quiz 탭에 `initialTopic`/`initialContent`로
  넘깁니다. 두 탭 모두 마운트 시 seed가 있으면 우선 반영하고, `onSeedConsumed` prop으로 부모의
  seed 상태를 바로 비웁니다 — 그래야 다음에 다시 그 탭에 들어올 때 seed가 아니라 저장된 값을
  복원합니다(그래서 이 두 탭에는 `key`로 강제 리마운트시키는 트릭을 쓰지 않습니다 — 부모의
  `<div key={active}>`가 탭 진입 시 이미 새 인스턴스를 만들어주므로 불필요).
- `frontend/src/lib/usePersistedState.js`가 tab 전환/새로고침에도 살아남아야 하는 상태를
  `localStorage`에 저장합니다. `usePersistedState(key, initialValue)`는 일반 `useState`처럼
  쓰되 값이 바뀔 때마다 자동으로 저장하고, 마운트 시 저장된 값이 있으면 그걸로 복원합니다.
  `loadPersisted`/`savePersisted`는 (Quiz 탭처럼) seed 우선순위 같은 커스텀 로직이 필요할 때
  직접 씁니다. `DailyPlanTab`(폼 입력 전체 + `plan`), `MaterialTab`(`subject`/`materialText`/
  `studyList`), `QuizTab`(폼 입력 + `quiz`/`answers`/`result`/`xpAwarded`)이 이 방식을 씁니다.
  브라우저 저장소라 이 브라우저에서만 유지되고 여러 기기/사용자 간에는 공유되지 않습니다.
  `TrackCurriculumTab`(과목별 커리큘럼)만 예외 — 여긴 백엔드(`backend/data/
  custom_curriculum.json`)에 저장해서, 브라우저를 바꿔도(같은 서버에 붙는 한) 안 사라집니다.
- 스타일링은 Tailwind v4이며 설정이 `tailwind.config.js`가 아니라
  `frontend/src/index.css`의 `@theme` 블록에 있습니다. 커스텀 다크 팔레트
  (`ink`/`panel`/`panel-border`/`blue`/`blue-bright`/`emerald`/`coral`/`text-primary`/
  `text-muted`)와 `Inter`(sans), `JetBrains Mono`(mono) 폰트를 사용합니다.
- 코드 문법 강조는 `highlight.js`(코어 + 필요한 언어만 개별 등록: java/python/cpp/c/
  javascript/csharp/sql — 전체 임포트가 아니라 `highlight.js/lib/core` + 개별
  `highlight.js/lib/languages/*`)와 `atom-one-dark` 테마 CSS를 씁니다. 테마 자체 배경색은
  `index.css`의 `.hljs { background: transparent !important; }`로 지워서 우리 다크 배경
  위에서 보이게 합니다. `MaterialTab.jsx`의 코드 리뷰 블록에서만 사용 중 — 새 언어를 강조
  대상에 추가하려면 `hljs.registerLanguage`를 더 등록하세요.

### 데이터 모델

- CLI/Streamlit(`data/curricula.json`, `study_planner_web/data/curricula.json`)은 목표 이름 →
  `{description, steps: [{id, title, detail, resources}]}` 형태로 매핑되고, 없는 목표는
  `generate_curriculum_via_llm`으로 즉석에서 생성되어 이 파일에 캐싱됩니다(write-through
  캐시). **`backend/`는 이 캐싱을 하지 않습니다** — `/api/curriculum`은 매번 Claude를 새로
  호출합니다.
- 진행 상황(완료한 step id)과 XP는 세 세대가 각자 다른 파일을 씁니다: CLI는 저장소 루트
  `data/progress.json`(XP 없음), Streamlit은 `study_planner_web/data/progress.json` +
  `study_planner_web/data/xp.json`, `backend/`는 `backend/data/progress.json` +
  `backend/data/xp.json`(둘 다 `backend/storage.py`가 관리). 서로 공유되지 않으니 세 버전을
  같이 테스트할 때 진행 상황이 안 맞아도 정상입니다.
- 레벨 계산식은 세 버전 모두 `total_xp // 150 + 1`로 동일합니다.
- 모든 Claude 호출은 환경변수 `ANTHROPIC_API_KEY`가 필요하며 `"claude-sonnet-5"` 모델을
  사용합니다. 모든 생성 함수는 이 문자열을 기본값으로 하는 `model` 키워드 인자를 받습니다 —
  모델을 바꿀 때는 다른 곳에 하드코딩하지 말고 이 인자를 이용하세요.
