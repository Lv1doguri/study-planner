import { useEffect, useState } from "react";
import { ClipboardCheck, Sparkles } from "lucide-react";
import { loadPersisted } from "../lib/usePersistedState";
import { API_BASE } from "../lib/api";

const STORAGE_KEY = "studyplanner:quiz";
const DEFAULT_STATE = {
  topic: "",
  studyContent: "",
  numQuestions: 5,
  quiz: null,
  answers: {},
  result: null,
  xpAwarded: false,
};

const inputClass =
  "w-full bg-ink border border-panel-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-blue";

const labelClass =
  "block text-xs font-mono uppercase tracking-wide text-text-muted mb-1";

const primaryButtonClass =
  "bg-blue hover:bg-blue-bright text-white font-bold rounded-full px-5 py-2 transition-all shadow-[0_0_15px_rgba(5,102,217,0.35)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

const successButtonClass =
  "bg-emerald hover:opacity-90 text-ink font-bold rounded-full px-5 py-2 transition-all hover:scale-[1.02] active:scale-[0.98]";

function EmptyState() {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <ClipboardCheck className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">
        위 정보를 입력하고 생성하면, 여기에 문제가 나타납니다.
      </p>
    </div>
  );
}

function QuestionText({ text }) {
  // 문제 지문에 코드가 섞여 있으면(빈 줄로 구분된 코드 블록) 줄바꿈이 살아있는
  // 모노스페이스 블록으로 따로 보여준다 — 그냥 <p>에 넣으면 줄바꿈이 다 사라져서
  // 코드가 한 줄로 붙어 보인다.
  const parts = text.split("\n\n");
  if (parts.length < 2) {
    return <p className="font-semibold text-sm leading-relaxed whitespace-pre-wrap">{text}</p>;
  }

  const [intro, ...rest] = parts;
  return (
    <div>
      <p className="font-semibold text-sm leading-relaxed mb-2">{intro}</p>
      <pre className="bg-ink border border-panel-border rounded-lg p-3 text-xs font-mono text-text-primary overflow-x-auto whitespace-pre mb-2">
        <code>{rest.join("\n\n")}</code>
      </pre>
    </div>
  );
}

export default function QuizTab({
  initialTopic = "",
  initialContent = "",
  initialNumQuestions = null,
  onXpChange,
  onSeedConsumed,
}) {
  // 강의자료/과목별 커리큘럼 탭에서 넘어온 seed가 있으면 그걸 우선하고, 없으면 서버에 저장해둔
  // 내용을 복원한다 — backend/data/quiz_state.json에 저장해서 같은 와이파이의 다른 기기에서
  // 접속해도 같은 문제를 이어서 볼 수 있다.
  const hasSeed = Boolean(initialTopic || initialContent);

  const [topic, setTopic] = useState(hasSeed ? initialTopic : "");
  const [studyContent, setStudyContent] = useState(hasSeed ? initialContent : "");
  const [numQuestions, setNumQuestions] = useState(
    hasSeed && initialNumQuestions ? initialNumQuestions : DEFAULT_STATE.numQuestions
  );

  const [quiz, setQuiz] = useState(null);
  const [loading, setLoading] = useState(false);
  const [answers, setAnswers] = useState({});
  const [result, setResult] = useState(null);
  const [xpAwarded, setXpAwarded] = useState(false);
  const [error, setError] = useState("");
  // seed로 들어온 경우 서버 상태로 덮어쓸 필요가 없으니 처음부터 "복원 완료"로 취급한다.
  const [hydrated, setHydrated] = useState(hasSeed);

  // 마운트 시 한 번만 seed를 부모에 알려 소비 처리한다 (재마운트 없이도 이후엔 seed가 비워짐).
  // seed가 없으면 서버에 저장된 마지막 상태를 불러온다.
  useEffect(() => {
    if (hasSeed) {
      onSeedConsumed?.();
      return;
    }

    const loadState = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/quiz-state`);
        const data = response.ok ? await response.json() : {};
        let state = data.state;

        // 예전 버전은 이 브라우저의 localStorage에만 저장했다. 서버에 아직 없고 이 브라우저에
        // 옛날 데이터가 남아있으면 한 번만 서버로 옮긴다.
        if (!state) {
          const legacy = loadPersisted(STORAGE_KEY, null);
          if (legacy && (legacy.topic || legacy.quiz)) {
            state = {
              topic: legacy.topic,
              study_content: legacy.studyContent,
              num_questions: legacy.numQuestions,
              quiz: legacy.quiz,
              answers: legacy.answers,
              result: legacy.result,
              xp_awarded: legacy.xpAwarded,
            };
            await fetch(`${API_BASE}/api/quiz-state`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(state),
            });
            localStorage.removeItem(STORAGE_KEY);
          }
        }

        if (state) {
          setTopic(state.topic || "");
          setStudyContent(state.study_content || "");
          setNumQuestions(state.num_questions || DEFAULT_STATE.numQuestions);
          setQuiz(state.quiz || null);
          setAnswers(state.answers || {});
          setResult(state.result || null);
          setXpAwarded(Boolean(state.xp_awarded));
        }
      } catch {
        // 서버에서 못 불러와도 새로 생성하는 건 그대로 가능하니 조용히 넘어간다
      } finally {
        setHydrated(true);
      }
    };

    loadState();
  }, []);

  useEffect(() => {
    if (!hydrated) return; // 서버에서 아직 복원 중이면 빈 초기값으로 덮어쓰지 않는다

    fetch(`${API_BASE}/api/quiz-state`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic,
        study_content: studyContent,
        num_questions: Number(numQuestions) || DEFAULT_STATE.numQuestions,
        quiz,
        answers,
        result,
        xp_awarded: xpAwarded,
      }),
    }).catch(() => {
      // 저장 실패해도 화면 사용에는 지장 없음
    });
  }, [topic, studyContent, numQuestions, quiz, answers, result, xpAwarded, hydrated]);

  const handleGenerate = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");
    setQuiz(null);
    setAnswers({});
    setResult(null);
    setXpAwarded(false);

    try {
      const response = await fetch(`${API_BASE}/api/quiz`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          study_content: studyContent,
          num_questions: Number(numQuestions),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "퀴즈 생성에 실패했습니다.");
      }

      setQuiz(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGrade = async () => {
    if (!quiz) return;

    let score = 0;

    const results = quiz.questions.map((q, i) => {
      const correct = answers[i] === q.correct_index;

      if (correct) {
        score += 1;
      }

      return correct;
    });

    setResult({
      score,
      total: quiz.questions.length,
      results,
    });

    if (!xpAwarded) {
      setXpAwarded(true);
      try {
        const response = await fetch(`${API_BASE}/api/xp/add`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ amount: score * 10, label: `퀴즈: ${topic}` }),
        });

        if (response.ok) {
          onXpChange?.();
        }
      } catch {
        // XP 반영에 실패해도 채점 결과 자체는 그대로 보여준다
      }
    }
  };

  return (
    <div>
      <p className="text-text-muted text-sm mb-4">
        이번 주 공부한 내용을 입력하면 AI가 객관식 문제를 만들어줍니다.
      </p>

      <form onSubmit={handleGenerate} className="space-y-4 mb-6">
        <div>
          <label className={labelClass}>주제/과목</label>
          <input
            className={inputClass}
            placeholder="예: 논리회로 2장"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            required
          />
        </div>

        <div>
          <label className={labelClass}>공부한 내용</label>
          <textarea
            className={inputClass}
            rows={4}
            placeholder="2진수/8진수/16진수 변환, 2의 보수 ..."
            value={studyContent}
            onChange={(e) => setStudyContent(e.target.value)}
            required
          />
        </div>

        <div>
          <label className={labelClass}>문항 수</label>
          <input
            type="number"
            className={inputClass}
            value={numQuestions}
            onChange={(e) => setNumQuestions(e.target.value)}
            min={1}
            max={20}
            required
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className={primaryButtonClass}
        >
          {loading ? (
            <span className="flex items-center gap-1.5">
              <Sparkles size={14} className="animate-pulse" />
              AI 생성 중...
            </span>
          ) : (
            "미니테스트 생성하기"
          )}
        </button>
      </form>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4 text-sm">
          <p className="font-bold mb-1">생성 실패</p>
          <p>{error}</p>
        </div>
      )}

      {quiz ? (
        <div>
          <h3 className="font-bold text-lg mb-3">
            {quiz.quiz_title}
          </h3>

          <div className="space-y-4 mb-4">
            {quiz.questions.map((q, i) => (
              <div
                key={i}
                className="bg-panel border border-panel-border rounded-xl p-4 hover:border-blue transition-colors"
              >
                <div className="mb-2">
                  <QuestionText text={`${i + 1}. ${q.question}`} />
                </div>

                <div className="space-y-1">
                  {q.options.map((opt, j) => (
                    <label
                      key={j}
                      className="flex items-center gap-2 text-sm cursor-pointer"
                    >
                      <input
                        type="radio"
                        name={`q-${i}`}
                        checked={answers[i] === j}
                        onChange={() =>
                          setAnswers((prev) => ({
                            ...prev,
                            [i]: j,
                          }))
                        }
                        className="accent-blue"
                      />

                      {opt}
                    </label>
                  ))}
                </div>

                {result && (
                  <p
                    className={`text-xs mt-2 ${
                      result.results[i]
                        ? "text-emerald"
                        : "text-coral"
                    }`}
                  >
                    {result.results[i] ? "✅ 정답" : "❌ 오답"} —{" "}
                    {q.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>

          <button
            onClick={handleGrade}
            className={successButtonClass}
          >
            채점하기
          </button>

          {result && (
            <p className="mt-3 font-mono text-sm">
              점수:{" "}
              <span className="text-emerald font-bold">
                {result.score} / {result.total}
              </span>
            </p>
          )}
        </div>
      ) : (
        !loading && <EmptyState />
      )}
    </div>
  );
}