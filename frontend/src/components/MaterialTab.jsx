import { useEffect, useState } from "react";
import { Check, Copy, FileText, GraduationCap, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { loadPersisted, usePersistedState } from "../lib/usePersistedState";
import { API_BASE } from "../lib/api";
import hljs from "highlight.js/lib/core";
import java from "highlight.js/lib/languages/java";
import python from "highlight.js/lib/languages/python";
import cpp from "highlight.js/lib/languages/cpp";
import javascript from "highlight.js/lib/languages/javascript";
import csharp from "highlight.js/lib/languages/csharp";
import sql from "highlight.js/lib/languages/sql";
import "highlight.js/styles/atom-one-dark.css";

hljs.registerLanguage("java", java);
hljs.registerLanguage("python", python);
hljs.registerLanguage("cpp", cpp);
hljs.registerLanguage("c", cpp);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("csharp", csharp);
hljs.registerLanguage("sql", sql);

function highlightCode(code, language) {
  try {
    if (language && hljs.getLanguage(language)) {
      return hljs.highlight(code, { language }).value;
    }
    return hljs.highlightAuto(code).value;
  } catch {
    return code;
  }
}

const LANGUAGE_EMOJI = {
  java: "☕",
  python: "🐍",
  cpp: "⚙️",
  c: "⚙️",
  javascript: "📜",
  typescript: "📜",
  csharp: "🎯",
  sql: "🗄️",
};

const STORAGE_PREFIX = "studyplanner:material:";

const inputClass =
  "w-full bg-ink border border-panel-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-blue";

const labelClass =
  "block text-xs font-mono uppercase tracking-wide text-text-muted mb-1";

const successButtonClass =
  "bg-emerald hover:opacity-90 text-ink font-bold rounded-full px-5 py-2 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

const outlineButtonClass =
  "border border-blue text-blue hover:bg-blue/10 font-bold rounded-full px-5 py-2 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

// 예전 버전은 과목당 분석 결과를 하나만 저장했다(단일 값이거나, {subject: analysis} 형태).
// 서버(backend/data/materials.json)에 아직 아무것도 없을 때만 이 브라우저에 남아있는 값을
// 찾아서 한 번 서버로 옮긴다 — {과목명: 분석결과} 형태로 반환한다.
function getLocalMaterialsSnapshot() {
  const perSubject = loadPersisted(`${STORAGE_PREFIX}materialsBySubject`, null);
  if (perSubject && Object.keys(perSubject).length > 0) {
    // 더 예전 버전은 {subject: {studyList, lectureAnalysis}} 형태였다 — 있으면 분석 결과만 뽑는다.
    const flattened = {};
    for (const [subj, value] of Object.entries(perSubject)) {
      const analysis = value?.lectureAnalysis ?? value;
      if (analysis) flattened[subj] = analysis;
    }
    return flattened;
  }

  const legacyAnalysis = loadPersisted(`${STORAGE_PREFIX}lectureAnalysis`, null);
  const legacySubject = loadPersisted(`${STORAGE_PREFIX}subject`, "").trim();
  if (!legacySubject || !legacyAnalysis) return {};
  return { [legacySubject]: legacyAnalysis };
}

function EmptyState() {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <FileText className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">
        강의자료를 업로드하고 "교수 시점 분석"을 누르면, 여기에 과목별 분석 결과가 나타납니다.
      </p>
    </div>
  );
}

function CodeSnippetCard({ snippet }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(snippet.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 클립보드 권한이 없어도 코드는 화면에서 직접 드래그해서 복사할 수 있다
    }
  };

  const emoji = LANGUAGE_EMOJI[snippet.language?.toLowerCase()] || "💻";

  return (
    <div className="bg-panel border border-panel-border rounded-xl overflow-hidden">
      <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-panel-border">
        <p className="font-semibold text-sm flex items-center gap-1.5">
          <span>{emoji}</span>
          {snippet.title}
        </p>
        <div className="flex items-center gap-3 shrink-0">
          {snippet.language && (
            <span className="text-[10px] font-mono uppercase tracking-wide text-text-muted">
              {snippet.language}
            </span>
          )}
          <button
            type="button"
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-blue transition-colors"
            title="코드 복사"
          >
            {copied ? (
              <>
                <Check size={13} className="text-emerald" />
                복사됨
              </>
            ) : (
              <>
                <Copy size={13} />
                복사
              </>
            )}
          </button>
        </div>
      </div>

      <pre className="bg-ink p-4 overflow-x-auto text-xs font-mono leading-relaxed">
        <code
          className={`hljs language-${snippet.language || "plaintext"}`}
          dangerouslySetInnerHTML={{ __html: highlightCode(snippet.code, snippet.language) }}
        />
      </pre>

      {snippet.review && (
        <div className="px-4 py-3 border-t border-panel-border">
          <p className="text-xs text-text-muted leading-relaxed whitespace-pre-wrap">{snippet.review}</p>
        </div>
      )}
    </div>
  );
}

function buildQuizContentFromAnalysis(analysis) {
  const parts = [`[핵심 요약]\n${analysis.summary}`];

  if (analysis.key_points?.length) {
    parts.push(
      "[중요 포인트]\n" +
        analysis.key_points.map((p) => `- ${p.title}: ${p.reason}`).join("\n")
    );
  }

  if (analysis.expected_questions?.length) {
    parts.push(
      "[예상 문제와 근거]\n" +
        analysis.expected_questions.map((q) => `- ${q.question} (근거: ${q.reason})`).join("\n")
    );
  }

  if (analysis.code_snippets?.length) {
    parts.push(
      "[코드 리뷰]\n" +
        analysis.code_snippets
          .map((s) => `${s.title}\n${s.code}\n${s.review}`)
          .join("\n\n")
    );
  }

  return parts.join("\n\n");
}

function MaterialAnalysisCard({ item, open, onToggle, onDelete, onSendToQuiz }) {
  // 예전 버전은 explanation이 문자열 하나였다 — 그때 저장된 결과가 브라우저에 남아있어도
  // 깨지지 않도록 배열이 아니면 문단 하나짜리 배열로 취급한다.
  const explanationSections = Array.isArray(item.explanation)
    ? item.explanation
    : item.explanation
      ? [{ heading: "", body: item.explanation }]
      : [];

  return (
    <div className="bg-ink border border-panel-border rounded-xl overflow-hidden">
      <div className="w-full flex justify-between items-center px-4 py-3 gap-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex-1 min-w-0 flex justify-between items-center text-left"
        >
          <div className="min-w-0">
            <p className="font-semibold text-sm truncate flex items-center gap-1.5">
              <span>{item.subject_emoji || "📘"}</span>
              {item.analysis_title}
            </p>
            {item.created_at && (
              <p className="text-[11px] font-mono text-text-muted mt-0.5">
                {item.created_at.slice(0, 16).replace("T", " ")}
              </p>
            )}
          </div>
          <span className="text-text-muted text-sm shrink-0 ml-2">{open ? "▲" : "▼"}</span>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="text-text-muted hover:text-coral transition-colors shrink-0"
          title="이 분석 결과 삭제"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {open && (
        <div className="px-4 pb-4 space-y-4 animate-[fadeIn_0.2s_ease-out]">
          <div className="flex justify-end">
            <button
              type="button"
              className={successButtonClass}
              onClick={() => onSendToQuiz(item.analysis_title, buildQuizContentFromAnalysis(item))}
            >
              이 분석 내용으로 미니테스트 만들기
            </button>
          </div>

          <div className="bg-panel border border-blue/30 rounded-xl p-4">
            <p className="font-mono text-xs uppercase tracking-wide text-blue mb-2">
              핵심 요약
            </p>
            <p className="text-sm text-text-primary leading-relaxed">{item.summary}</p>
          </div>

          {explanationSections.length > 0 && (
            <div>
              <p className="font-mono text-xs uppercase tracking-wide text-blue mb-3">
                교수 입장에서 설명
              </p>
              <div className="space-y-3">
                {explanationSections.map((section, i) => (
                  <div key={i} className="border-l-2 border-blue/40 pl-3">
                    {section.heading && (
                      <p className="font-semibold text-sm mb-1 flex items-center gap-1.5">
                        {section.emoji && <span>{section.emoji}</span>}
                        {section.heading}
                      </p>
                    )}
                    <p className="text-sm text-text-muted leading-relaxed">{section.body}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Array.isArray(item.code_snippets) && item.code_snippets.length > 0 && (
            <div>
              <p className="font-mono text-xs uppercase tracking-wide text-coral mb-3">
                코드 리뷰
              </p>
              <div className="space-y-4">
                {item.code_snippets.map((snippet, i) => (
                  <CodeSnippetCard key={i} snippet={snippet} />
                ))}
              </div>
            </div>
          )}

          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-emerald mb-3">
              시험에 나올 가능성이 높은 포인트
            </p>
            <div className="space-y-2">
              {item.key_points.map((point, i) => (
                <div
                  key={i}
                  className="bg-panel border border-panel-border rounded-xl p-4 hover:border-blue transition-colors"
                >
                  <p className="font-semibold text-sm text-emerald">{point.title}</p>
                  <p className="text-sm text-text-muted leading-relaxed mt-1">{point.reason}</p>
                </div>
              ))}
            </div>
          </div>

          <div>
            <p className="font-mono text-xs uppercase tracking-wide text-coral mb-2">
              예상 문제
            </p>
            <div className="space-y-2">
              {item.expected_questions.map((q, i) => (
                <div
                  key={i}
                  className="bg-panel border border-panel-border rounded-xl p-4 hover:border-blue transition-colors"
                >
                  <p className="font-semibold text-sm leading-relaxed">
                    {i + 1}. {q.question}
                  </p>
                  <p className="text-xs text-text-muted leading-relaxed mt-1.5">
                    <span className="font-semibold">출제 근거:</span> {q.reason}
                  </p>
                  {q.answer_direction && (
                    <p className="text-xs text-text-muted leading-relaxed mt-1">
                      <span className="font-semibold">답변 방향:</span> {q.answer_direction}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MaterialTab({ onSendToQuiz }) {
  const [subject, setSubject] = usePersistedState(`${STORAGE_PREFIX}subject`, "");
  const [materialText, setMaterialText] = usePersistedState(`${STORAGE_PREFIX}materialText`, "");

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [usedVision, setUsedVision] = usePersistedState(`${STORAGE_PREFIX}usedVision`, false);

  // 과목/주제별로 결과를 저장한다 — 하나만 저장하면 다른 과목으로 새로 생성할 때 이전 결과가
  // 사라진다(DailyPlanTab의 plansBySubject와 같은 패턴). 서버(backend/data/materials.json)에
  // 저장해서 같은 와이파이의 다른 기기에서 접속해도 같은 결과가 보인다.
  // {과목명: [분석결과, ...]} — 강의자료는 보통 주차/챕터별로 여러 개 올라오므로 같은
  // 과목이어도 덮어쓰지 않고 계속 쌓인다(기출문제 모음과 같은 패턴).
  const [materialsBySubject, setMaterialsBySubject] = useState({});
  const trimmedSubject = subject.trim();
  const [openSubjects, setOpenSubjects] = useState(() =>
    trimmedSubject ? { [trimmedSubject]: true } : {}
  );
  const [openItems, setOpenItems] = useState({});

  useEffect(() => {
    const LEGACY_KEYS = [
      `${STORAGE_PREFIX}materialsBySubject`,
      `${STORAGE_PREFIX}studyList`,
      `${STORAGE_PREFIX}lectureAnalysis`,
    ];

    const loadMaterials = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/materials`);
        if (!response.ok) return;
        const data = await response.json();
        let materials = data.materials || {};

        // 예전 버전은 이 브라우저의 localStorage에만, 그것도 과목당 결과 하나만 저장했다.
        // 서버에 아직 아무것도 없고 이 브라우저에 옛날 데이터가 남아있으면, 한 번만 서버로
        // 옮겨서 다른 기기에서도 보이게 한다.
        if (Object.keys(materials).length === 0) {
          const legacy = getLocalMaterialsSnapshot();
          const legacyEntries = Object.entries(legacy);
          if (legacyEntries.length > 0) {
            for (const [subj, analysis] of legacyEntries) {
              await fetch(`${API_BASE}/api/materials`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject: subj, analysis }),
              });
            }
            const refreshed = await fetch(`${API_BASE}/api/materials`);
            materials = refreshed.ok ? (await refreshed.json()).materials || {} : {};
            LEGACY_KEYS.forEach((key) => localStorage.removeItem(key));
          }
        }

        setMaterialsBySubject(materials);
        setOpenSubjects((prev) => {
          if (Object.keys(prev).length > 0) return prev;
          const firstSubject = Object.keys(materials)[0];
          return firstSubject ? { [firstSubject]: true } : prev;
        });
      } catch {
        // 서버에서 못 불러와도 새로 생성하는 건 그대로 가능하니 조용히 넘어간다
      }
    };

    loadMaterials();
  }, []);

  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/api/extract-material`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "파일에서 텍스트를 추출하지 못했습니다.");
      }

      setMaterialText(data.extracted_text);
      setUsedVision(Boolean(data.used_vision));
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleAnalyze = async () => {
    setAnalysisLoading(true);
    setAnalysisError("");

    try {
      const response = await fetch(`${API_BASE}/api/lecture-analysis`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          subject,
          material_text: materialText,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "교수 시점 분석에 실패했습니다.");
      }

      // 저장소(backend/data/materials.json)에 쌓인 항목은 "id" 필드를 쓰는데, 방금 생성
      // 응답은 "material_id"로 온다 — 화면에서 곧바로 펼쳐 보여주려면 형태를 맞춰줘야 한다.
      const newItem = { ...data, id: data.material_id };
      setMaterialsBySubject((prev) => ({
        ...prev,
        [trimmedSubject]: [...(prev[trimmedSubject] || []), newItem],
      }));
      setOpenSubjects((prev) => ({ ...prev, [trimmedSubject]: true }));
      if (newItem.id) {
        setOpenItems((prev) => ({ ...prev, [`${trimmedSubject}::${newItem.id}`]: true }));
      }
    } catch (err) {
      setAnalysisError(err.message);
    } finally {
      setAnalysisLoading(false);
    }
  };

  const toggleSubjectSection = (subj) => {
    setOpenSubjects((prev) => ({ ...prev, [subj]: !prev[subj] }));
  };

  const toggleItem = (key) => {
    setOpenItems((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const handleDeleteItem = async (subj, itemId) => {
    setMaterialsBySubject((prev) => ({
      ...prev,
      [subj]: (prev[subj] || []).filter((item) => item.id !== itemId),
    }));

    try {
      await fetch(`${API_BASE}/api/materials`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: subj, item_id: itemId }),
      });
    } catch {
      // 서버 삭제가 실패해도 화면에서는 이미 지워진 채로 둔다 — 다음에 새로고침하면 다시 나타날 수 있음
    }
  };

  return (
    <div>
      <p className="text-text-muted text-sm mb-4">
        강의계획서나 강의자료(PDF/PPTX)를 올리고 "교수 시점 분석"을 누르면, 교수 입장에서
        내용을 설명·요약해주고 시험에 나올 만한 포인트와 예상 문제까지 알려줍니다. 과목/주제별로
        저장되어 계속 쌓이고, 같은 내용으로 미니테스트도 바로 만들 수 있습니다.
      </p>

      <div className="space-y-4 mb-6">
        <div>
          <label className={labelClass}>과목/주제</label>
          <input
            className={inputClass}
            placeholder="예: 논리회로 2장"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
        </div>

        <div>
          <label className={labelClass}>강의자료 업로드 (PDF 또는 PPTX)</label>
          <label className="flex items-center gap-2 w-full bg-ink border border-dashed border-panel-border rounded-lg px-3 py-3 text-sm text-text-muted cursor-pointer hover:border-blue transition-colors">
            <UploadCloud size={16} />
            {uploading ? "분석 중... (그림·표까지 같이 볼 수 있어 시간이 좀 걸려요)" : "파일을 선택하세요"}
            <input
              type="file"
              accept=".pdf,.pptx"
              onChange={handleFileChange}
              className="hidden"
              disabled={uploading}
            />
          </label>
          {uploadError && (
            <p className="text-xs text-coral mt-1">{uploadError}</p>
          )}
        </div>

        <div>
          <div className="flex items-center gap-2">
            <label className={labelClass}>추출된 내용 (직접 수정 가능)</label>
            {usedVision && (
              <span className="text-[10px] font-mono uppercase tracking-wide text-emerald bg-emerald/10 border border-emerald/30 rounded-full px-2 py-0.5">
                ✨ 그림·표 포함 분석
              </span>
            )}
          </div>
          <textarea
            className={inputClass}
            rows={6}
            placeholder="파일을 업로드하면 여기에 텍스트가 자동으로 채워집니다. 직접 입력해도 됩니다."
            value={materialText}
            onChange={(e) => setMaterialText(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!subject.trim() || !materialText.trim()}
            className={successButtonClass}
            onClick={() => onSendToQuiz(subject, materialText)}
          >
            이 내용으로 미니테스트 만들기
          </button>

          <button
            type="button"
            disabled={analysisLoading || !subject.trim() || !materialText.trim()}
            className={outlineButtonClass}
            onClick={handleAnalyze}
          >
            {analysisLoading ? (
              <span className="flex items-center gap-1.5">
                <Sparkles size={14} className="animate-pulse" />
                분석 중...
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <GraduationCap size={16} />
                교수 시점 분석 + 예상 문제
              </span>
            )}
          </button>
        </div>
      </div>

      {analysisError && (
        <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4 text-sm">
          <p className="font-bold mb-1">분석 실패</p>
          <p>{analysisError}</p>
        </div>
      )}

      {(() => {
        const subjectNames = Object.keys(materialsBySubject).filter(
          (s) => (materialsBySubject[s] || []).length > 0
        );

        if (subjectNames.length === 0) {
          return !analysisLoading && <EmptyState />;
        }

        return (
          <div className="space-y-4">
            {subjectNames.map((subj) => (
              <div key={subj} className="bg-panel border border-panel-border rounded-xl overflow-hidden">
                <button
                  type="button"
                  onClick={() => toggleSubjectSection(subj)}
                  className="w-full flex justify-between items-center px-4 py-3 text-left"
                >
                  <p className="font-bold text-sm">
                    {subj}{" "}
                    <span className="text-text-muted font-mono text-xs">
                      ({materialsBySubject[subj].length}개)
                    </span>
                  </p>
                  <span className="text-text-muted text-sm">{openSubjects[subj] ? "▲" : "▼"}</span>
                </button>

                {openSubjects[subj] && (
                  <div className="px-4 pb-4 space-y-3">
                    {materialsBySubject[subj]
                      .slice()
                      .reverse()
                      .map((item) => {
                        const key = `${subj}::${item.id}`;
                        return (
                          <MaterialAnalysisCard
                            key={key}
                            item={item}
                            open={!!openItems[key]}
                            onToggle={() => toggleItem(key)}
                            onDelete={() => handleDeleteItem(subj, item.id)}
                            onSendToQuiz={onSendToQuiz}
                          />
                        );
                      })}
                  </div>
                )}
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
