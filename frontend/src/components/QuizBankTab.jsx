import { useEffect, useState } from "react";
import { AlertTriangle, Archive, CheckCircle2, Trash2 } from "lucide-react";
import { API_BASE } from "../lib/api";

const successButtonClass =
  "bg-emerald hover:opacity-90 text-ink font-bold rounded-full px-5 py-2 text-sm transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

const outlineButtonClass =
  "border border-blue text-blue hover:bg-blue/10 font-bold rounded-full px-4 py-1.5 text-xs transition-all hover:scale-[1.02] active:scale-[0.98]";

const toggleButtonClass = (isActive) =>
  `px-4 py-2 rounded-full text-sm font-bold transition-all ${
    isActive ? "bg-blue text-white shadow-[0_0_15px_rgba(5,102,217,0.35)]" : "bg-panel text-text-muted hover:text-text-primary"
  }`;

function EmptyState({ text }) {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <Archive className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">{text}</p>
    </div>
  );
}

function QuestionText({ text }) {
  // 문제 지문에 코드가 섞여 있으면(빈 줄로 구분된 코드 블록) 줄바꿈이 살아있는 모노스페이스
  // 블록으로 따로 보여준다 — QuizTab의 QuestionText와 동일한 로직.
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

function BankQuizCard({ subject, item, open, onToggle, onDelete, onGraded }) {
  const [answers, setAnswers] = useState(item.answers || {});
  const [saving, setSaving] = useState(false);

  const handleGrade = async () => {
    let score = 0;
    const results = item.questions.map((q, i) => {
      const correct = answers[i] === q.correct_index;
      if (correct) score += 1;
      return correct;
    });
    const result = { score, total: item.questions.length, results };

    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/quiz-bank/result`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, quiz_id: item.id, answers, result }),
      });
      if (score > 0) {
        await fetch(`${API_BASE}/api/xp/add`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ amount: score * 10, label: `기출문제 복습: ${item.quiz_title}` }),
        });
      }
      onGraded(subject, item.id, answers, result);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-panel border border-panel-border rounded-xl overflow-hidden">
      <div className="w-full flex justify-between items-center px-4 py-3 gap-2">
        <button type="button" onClick={onToggle} className="flex-1 min-w-0 flex justify-between items-center text-left">
          <div className="min-w-0">
            <p className="font-semibold text-sm truncate">{item.quiz_title}</p>
            <p className="text-[11px] font-mono text-text-muted mt-0.5">
              {item.created_at?.slice(0, 16).replace("T", " ")}
              {item.result && (
                <span className="ml-2 text-emerald">
                  {item.result.score} / {item.result.total} 점
                </span>
              )}
            </p>
          </div>
          <span className="text-text-muted text-sm shrink-0 ml-2">{open ? "▲" : "▼"}</span>
        </button>
        <button type="button" onClick={onDelete} className="text-text-muted hover:text-coral transition-colors shrink-0" title="삭제">
          <Trash2 size={16} />
        </button>
      </div>

      {open && (
        <div className="px-4 pb-4 space-y-3 animate-[fadeIn_0.2s_ease-out]">
          {item.questions.map((q, i) => (
            <div key={i} className="bg-ink border border-panel-border rounded-xl p-4">
              <div className="mb-2">
                <QuestionText text={`${i + 1}. ${q.question}`} />
              </div>
              <div className="space-y-1">
                {q.options.map((opt, j) => (
                  <label key={j} className="flex items-center gap-2 text-sm cursor-pointer">
                    <input
                      type="radio"
                      name={`bank-${subject}-${item.id}-${i}`}
                      checked={answers[i] === j}
                      onChange={() => setAnswers((prev) => ({ ...prev, [i]: j }))}
                      className="accent-blue"
                    />
                    {opt}
                  </label>
                ))}
              </div>
              {item.result && (
                <p className={`text-xs mt-2 ${item.result.results[i] ? "text-emerald" : "text-coral"}`}>
                  {item.result.results[i] ? "✅ 정답" : "❌ 오답"} — {q.explanation}
                </p>
              )}
            </div>
          ))}

          <button type="button" onClick={handleGrade} disabled={saving} className={successButtonClass}>
            {item.result ? "다시 채점하기" : "채점하기"}
          </button>
        </div>
      )}
    </div>
  );
}

function WrongQuestionCard({ subject, entry, onResolved }) {
  const [selected, setSelected] = useState(null);
  const [checked, setChecked] = useState(false);
  const [saving, setSaving] = useState(false);
  const correct = selected === entry.question.correct_index;

  const handleCheck = async () => {
    if (selected === null) return;
    setChecked(true);
    if (!correct) return;

    setSaving(true);
    try {
      await fetch(`${API_BASE}/api/quiz-bank/question`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          subject,
          quiz_id: entry.quizId,
          question_index: entry.questionIndex,
          answer_index: selected,
          correct: true,
        }),
      });
      await fetch(`${API_BASE}/api/xp/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: 10, label: `오답노트 복습: ${entry.quizTitle}` }),
      });
      onResolved();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-panel border border-panel-border rounded-xl p-4">
      <p className="text-[10px] font-mono uppercase tracking-wide text-text-muted mb-2">{entry.quizTitle}</p>
      <div className="mb-2">
        <QuestionText text={entry.question.question} />
      </div>
      <div className="space-y-1 mb-2">
        {entry.question.options.map((opt, j) => (
          <label key={j} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="radio"
              name={`wrong-${subject}-${entry.quizId}-${entry.questionIndex}`}
              checked={selected === j}
              onChange={() => {
                setSelected(j);
                setChecked(false);
              }}
              className="accent-blue"
            />
            {opt}
          </label>
        ))}
      </div>

      {checked && (
        <p className={`text-xs mb-2 ${correct ? "text-emerald" : "text-coral"}`}>
          {correct ? "✅ 정답! 오답노트에서 사라집니다." : "❌ 오답 — 다시 골라보세요."} — {entry.question.explanation}
        </p>
      )}

      <button type="button" onClick={handleCheck} disabled={selected === null || saving} className={outlineButtonClass}>
        정답 확인
      </button>
    </div>
  );
}

export default function QuizBankTab() {
  const [bank, setBank] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [view, setView] = useState("bank"); // "bank" | "wrong"
  const [openSubjects, setOpenSubjects] = useState({});
  const [openQuizzes, setOpenQuizzes] = useState({});

  const fetchBank = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await fetch(`${API_BASE}/api/quiz-bank`);
      if (!response.ok) throw new Error("기출문제를 불러오지 못했습니다.");
      const data = await response.json();
      setBank(data.bank || {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBank();
  }, []);

  const toggleSubject = (subj) => setOpenSubjects((prev) => ({ ...prev, [subj]: !prev[subj] }));
  const toggleQuiz = (key) => setOpenQuizzes((prev) => ({ ...prev, [key]: !prev[key] }));

  const handleDeleteQuiz = async (subject, quizId) => {
    setBank((prev) => ({
      ...prev,
      [subject]: prev[subject].filter((item) => item.id !== quizId),
    }));
    try {
      await fetch(`${API_BASE}/api/quiz-bank`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, quiz_id: quizId }),
      });
    } catch {
      // 서버 삭제가 실패해도 화면에서는 이미 지워진 채로 둔다
    }
  };

  const handleGraded = (subject, quizId, answers, result) => {
    setBank((prev) => ({
      ...prev,
      [subject]: prev[subject].map((item) => (item.id === quizId ? { ...item, answers, result } : item)),
    }));
  };

  const handleWrongResolved = (subject, quizId, questionIndex) => {
    setBank((prev) => ({
      ...prev,
      [subject]: prev[subject].map((item) => {
        if (item.id !== quizId || !item.result) return item;
        const results = [...item.result.results];
        results[questionIndex] = true;
        return { ...item, result: { ...item.result, results, score: results.filter(Boolean).length } };
      }),
    }));
  };

  const subjectNames = Object.keys(bank);

  // 오답노트: 채점된 문제 중 마지막 결과가 오답인 것만 과목별로 모은다.
  const wrongBySubject = {};
  for (const [subj, items] of Object.entries(bank)) {
    const wrongEntries = [];
    for (const item of items) {
      if (!item.result) continue;
      item.questions.forEach((q, i) => {
        if (item.result.results[i] === false) {
          wrongEntries.push({ quizId: item.id, quizTitle: item.quiz_title, questionIndex: i, question: q });
        }
      });
    }
    if (wrongEntries.length > 0) wrongBySubject[subj] = wrongEntries;
  }
  const wrongSubjectNames = Object.keys(wrongBySubject);

  return (
    <div>
      <h2 className="text-xl font-extrabold mb-1">기출문제 / 오답노트</h2>
      <p className="text-text-muted text-sm mb-4">
        지금까지 생성한 미니테스트가 과목별로 자동으로 쌓여요. 다시 풀어보거나, 오답노트에서 틀렸던
        문제만 모아 복습할 수 있습니다.
      </p>

      <div className="flex gap-2 mb-6">
        <button type="button" className={toggleButtonClass(view === "bank")} onClick={() => setView("bank")}>
          기출문제 모음
        </button>
        <button type="button" className={toggleButtonClass(view === "wrong")} onClick={() => setView("wrong")}>
          <span className="flex items-center gap-1.5">
            <AlertTriangle size={14} />
            오답노트
            {wrongSubjectNames.length > 0 && (
              <span className="bg-coral text-ink text-[10px] font-bold rounded-full px-1.5 py-0.5">
                {wrongSubjectNames.reduce((sum, s) => sum + wrongBySubject[s].length, 0)}
              </span>
            )}
          </span>
        </button>
      </div>

      {loading && <p className="text-text-muted text-sm">불러오는 중...</p>}
      {error && <p className="text-red-400 text-sm">{error}</p>}

      {!loading && !error && view === "bank" && (
        subjectNames.length === 0 ? (
          <EmptyState text="아직 생성한 미니테스트가 없어요. 미니테스트 탭에서 문제를 만들면 여기 자동으로 쌓입니다." />
        ) : (
          <div className="space-y-4">
            {subjectNames.map((subj) => (
              <div key={subj} className="bg-panel border border-panel-border rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleSubject(subj)}
                  className="w-full flex justify-between items-center px-4 py-3 text-left"
                >
                  <p className="font-bold text-sm">
                    {subj} <span className="text-text-muted font-mono text-xs">({bank[subj].length}개)</span>
                  </p>
                  <span className="text-text-muted text-sm">{openSubjects[subj] ? "▲" : "▼"}</span>
                </button>

                {openSubjects[subj] && (
                  <div className="px-4 pb-4 space-y-3">
                    {bank[subj]
                      .slice()
                      .reverse()
                      .map((item) => {
                        const key = `${subj}::${item.id}`;
                        return (
                          <BankQuizCard
                            key={key}
                            subject={subj}
                            item={item}
                            open={!!openQuizzes[key]}
                            onToggle={() => toggleQuiz(key)}
                            onDelete={() => handleDeleteQuiz(subj, item.id)}
                            onGraded={handleGraded}
                          />
                        );
                      })}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}

      {!loading && !error && view === "wrong" && (
        wrongSubjectNames.length === 0 ? (
          <EmptyState text="지금 오답노트가 비어있어요. 기출문제를 채점하고 틀린 문제가 있으면 여기 모입니다." />
        ) : (
          <div className="space-y-6">
            {wrongSubjectNames.map((subj) => (
              <div key={subj}>
                <p className="font-mono text-xs uppercase tracking-wide text-coral mb-3 flex items-center gap-2">
                  <CheckCircle2 size={14} />
                  {subj} ({wrongBySubject[subj].length}문제)
                </p>
                <div className="space-y-3">
                  {wrongBySubject[subj].map((entry) => (
                    <WrongQuestionCard
                      key={`${entry.quizId}-${entry.questionIndex}`}
                      subject={subj}
                      entry={entry}
                      onResolved={() => handleWrongResolved(subj, entry.quizId, entry.questionIndex)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  );
}
