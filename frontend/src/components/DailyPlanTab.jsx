import { useEffect, useState } from "react";
import { CalendarDays, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { loadPersisted, usePersistedState } from "../lib/usePersistedState";
import { API_BASE } from "../lib/api";

const STORAGE_PREFIX = "studyplanner:dailyplan:";

const inputClass =
  "w-full bg-ink border border-panel-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-blue";

const labelClass =
  "block text-xs font-mono uppercase tracking-wide text-text-muted mb-1";

const buttonClass =
  "bg-blue hover:bg-blue-bright text-white font-bold rounded-full px-5 py-2 transition-all shadow-[0_0_15px_rgba(5,102,217,0.35)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

function todayIsoDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function EmptyState() {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <CalendarDays className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">
        위 정보를 입력하고 생성하면, 여기에 하루 단위 계획이 나타납니다.
      </p>
    </div>
  );
}

function SubjectBlock({ subject }) {
  return (
    <div className="border-l-2 border-panel-border pl-3">
      <div className="flex items-center gap-2">
        <span className="text-base leading-none">{subject.emoji}</span>
        <span className="font-bold text-sm">{subject.subject}</span>
      </div>

      <p className="text-sm font-semibold text-blue mt-1 mb-1.5">{subject.topic}</p>

      <ul className="list-disc list-inside text-sm text-text-muted space-y-0.5">
        {subject.concepts.map((concept, j) => (
          <li key={j}>{concept}</li>
        ))}
      </ul>

      {subject.practice && (
        <div className="bg-ink border border-panel-border rounded-lg p-3 mt-2">
          <p className="text-[10px] font-mono uppercase tracking-wide text-emerald mb-1">
            직접 해보기
          </p>
          <pre className="text-xs font-mono text-text-primary whitespace-pre-wrap leading-relaxed">
            {subject.practice}
          </pre>
        </div>
      )}
    </div>
  );
}

function SubjectPlanSection({ subject, plan, open, onToggle, onDelete }) {
  return (
    <div className="bg-panel border border-panel-border rounded-xl overflow-hidden">
      <div className="w-full flex justify-between items-center px-4 py-3 gap-2">
        <button
          type="button"
          onClick={onToggle}
          className="flex-1 min-w-0 flex justify-between items-center text-left"
        >
          <div className="min-w-0">
            <p className="font-mono text-xs uppercase tracking-wide text-blue">{subject}</p>
            <p className="font-bold text-sm mt-0.5 truncate">{plan.plan_title}</p>
          </div>
          <span className="text-text-muted text-sm shrink-0 ml-2">{open ? "▲" : "▼"}</span>
        </button>
        <button
          type="button"
          onClick={onDelete}
          className="text-text-muted hover:text-coral transition-colors shrink-0"
          title="플랜 삭제"
        >
          <Trash2 size={16} />
        </button>
      </div>

      {open && (
        <div className="px-4 pb-4 space-y-2 animate-[fadeIn_0.2s_ease-out]">
          {plan.days.map((day) => (
            <DayCard key={day.day} day={day} />
          ))}
        </div>
      )}
    </div>
  );
}

function DayCard({ day }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-panel border border-panel-border rounded-xl overflow-hidden hover:border-blue transition-colors">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="w-full flex justify-between items-center px-4 py-3 font-mono text-sm font-bold text-left"
      >
        <span>
          📅 Day {day.day} — {day.date}
        </span>
        <span className="text-text-muted">
          {open ? "▲" : "▼"}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 animate-[fadeIn_0.2s_ease-out]">
          {day.subjects.map((subject, i) => (
            <SubjectBlock key={i} subject={subject} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function DailyPlanTab() {
  const [department, setDepartment] = usePersistedState(`${STORAGE_PREFIX}department`, "");
  const [year, setYear] = usePersistedState(`${STORAGE_PREFIX}year`, "");
  const [subject, setSubject] = usePersistedState(`${STORAGE_PREFIX}subject`, "");
  const [courseDetails, setCourseDetails] = usePersistedState(`${STORAGE_PREFIX}courseDetails`, "");
  const [startDate, setStartDate] = usePersistedState(`${STORAGE_PREFIX}startDate`, todayIsoDate());
  const [daysRemaining, setDaysRemaining] = usePersistedState(`${STORAGE_PREFIX}daysRemaining`, 12);

  // 플랜을 과목별로 따로 저장한다 — 하나만 저장하면 다른 과목으로 새로 생성할 때
  // 이전 과목의 플랜이 사라져버린다. 여러 과목의 플랜을 목록으로 한 화면에 다 보여주고,
  // 각각 펼치고 접을 수 있게 한다("과목별 커리큘럼" 탭이 모든 과목을 한 번에 보여주는 것과
  // 같은 방식). 서버(backend/data/daily_plans.json)에 저장해서 같은 와이파이의 다른 기기에서
  // 접속해도 같은 플랜이 보인다 — localStorage와 달리 기기별로 갈리지 않는다.
  const [plansBySubject, setPlansBySubject] = useState({});
  const trimmedSubject = subject.trim();
  const [openSubjects, setOpenSubjects] = useState(() =>
    trimmedSubject ? { [trimmedSubject]: true } : {}
  );

  useEffect(() => {
    const LEGACY_KEY = `${STORAGE_PREFIX}plansBySubject`;

    const loadPlans = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/daily-plans`);
        if (!response.ok) return;
        const data = await response.json();
        let plans = data.plans || {};

        // 예전 버전은 이 브라우저의 localStorage에만 저장했다. 서버에 아직 아무것도 없고
        // 이 브라우저에 옛날 데이터가 남아있으면, 한 번만 서버로 옮겨서 다른 기기에서도
        // 보이게 한다.
        if (Object.keys(plans).length === 0) {
          const legacy = loadPersisted(LEGACY_KEY, {});
          const legacyEntries = Object.entries(legacy);
          if (legacyEntries.length > 0) {
            for (const [subj, plan] of legacyEntries) {
              await fetch(`${API_BASE}/api/daily-plans`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ subject: subj, plan }),
              });
            }
            plans = legacy;
            localStorage.removeItem(LEGACY_KEY);
          }
        }

        setPlansBySubject(plans);
        setOpenSubjects((prev) => {
          if (Object.keys(prev).length > 0) return prev;
          const firstSubject = Object.keys(plans)[0];
          return firstSubject ? { [firstSubject]: true } : prev;
        });
      } catch {
        // 서버에서 못 불러와도 새로 생성하는 건 그대로 가능하니 조용히 넘어간다
      }
    };

    loadPlans();
  }, []);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [importNotice, setImportNotice] = useState("");

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

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

      setCourseDetails((prev) => (prev.trim() ? `${prev}\n\n${data.extracted_text}` : data.extracted_text));
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");
    setImportNotice("");

    try {
      const response = await fetch(`${API_BASE}/api/daily-plan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          department,
          year,
          subject,
          course_details: courseDetails,
          days_remaining: Number(daysRemaining),
          start_date: startDate,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "학습 계획 생성에 실패했습니다.");
      }

      setPlansBySubject((prev) => ({ ...prev, [trimmedSubject]: data }));
      setOpenSubjects((prev) => ({ ...prev, [trimmedSubject]: true }));

      try {
        const importResponse = await fetch(`${API_BASE}/api/custom-curriculum/import-daily-plan`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(data),
        });
        if (importResponse.ok) {
          setImportNotice("과목별 커리큘럼에 자동으로 추가했습니다.");
        }
      } catch {
        // 과목별 커리큘럼 반영에 실패해도 플랜 자체는 그대로 보여준다
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSubjectPlan = (subj) => {
    setOpenSubjects((prev) => ({ ...prev, [subj]: !prev[subj] }));
  };

  const handleDeletePlan = async (subj) => {
    setPlansBySubject((prev) => {
      const next = { ...prev };
      delete next[subj];
      return next;
    });
    setOpenSubjects((prev) => {
      const next = { ...prev };
      delete next[subj];
      return next;
    });

    try {
      await fetch(`${API_BASE}/api/daily-plans`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject: subj }),
      });
    } catch {
      // 서버 삭제가 실패해도 화면에서는 이미 지워진 채로 둔다 — 다음에 새로고침하면 다시 나타날 수 있음
    }
  };

  return (
    <div>
      <p className="text-text-muted text-sm mb-4">
        학과·학년·학습 과목·과목 상세 정보를 입력하면 AI가 하루 단위
        계획을 만들어줍니다. 강의계획서 PDF/PPTX를 올리면 주차별 진도표 같은 내용을
        자동으로 읽어와 채워줍니다.
      </p>

      <form onSubmit={handleGenerate} className="space-y-4 mb-6">
        <div>
          <label className={labelClass}>학과</label>
          <input
            className={inputClass}
            placeholder="예: 컴퓨터공학과"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            required
          />
        </div>

        <div>
          <label className={labelClass}>학년</label>
          <input
            className={inputClass}
            placeholder="예: 2학년 2학기 복학 예정"
            value={year}
            onChange={(e) => setYear(e.target.value)}
            required
          />
        </div>

        <div>
          <label className={labelClass}>학습 과목</label>
          <input
            className={inputClass}
            placeholder="예: 논리회로"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            required
          />
        </div>

        <div>
          <label className={labelClass}>과목 상세 정보</label>

          <label className="flex items-center gap-2 w-full bg-ink border border-dashed border-panel-border rounded-lg px-3 py-2.5 text-sm text-text-muted cursor-pointer hover:border-blue transition-colors mb-2">
            <UploadCloud size={16} />
            {uploading
              ? "분석 중... (그림·표까지 같이 볼 수 있어 시간이 좀 걸려요)"
              : "강의계획서 PDF/PPTX 업로드 (선택 — 아래 칸에 내용이 자동으로 추가됩니다)"}
            <input
              type="file"
              accept=".pdf,.pptx"
              onChange={handleFileChange}
              className="hidden"
              disabled={uploading}
            />
          </label>
          {uploadError && (
            <p className="text-xs text-coral mb-2">{uploadError}</p>
          )}

          <textarea
            className={inputClass}
            rows={4}
            placeholder="비중 25% - 중간고사 범위: 1~7주차 (수 체계, 논리 게이트, 카르노맵...)"
            value={courseDetails}
            onChange={(e) => setCourseDetails(e.target.value)}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className={labelClass}>시작 날짜</label>
            <input
              type="date"
              className={inputClass}
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              required
            />
          </div>

          <div>
            <label className={labelClass}>계획을 세울 기간 (일)</label>
            <input
              type="number"
              className={inputClass}
              value={daysRemaining}
              onChange={(e) => setDaysRemaining(e.target.value)}
              min={1}
              max={20}
              required
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className={buttonClass}
        >
          {loading ? (
            <span className="flex items-center gap-1.5">
              <Sparkles size={14} className="animate-pulse" />
              AI 생성 중...
            </span>
          ) : (
            "일별 플랜 생성하기"
          )}
        </button>
      </form>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4 text-sm">
          <p className="font-bold mb-1">생성 실패</p>
          <p>{error}</p>
        </div>
      )}

      {importNotice && (
        <p className="text-xs text-emerald mb-3">{importNotice}</p>
      )}

      {Object.keys(plansBySubject).length > 0 ? (
        <div className="space-y-4">
          {Object.entries(plansBySubject)
            .reverse()
            .map(([subj, planData]) => (
              <SubjectPlanSection
                key={subj}
                subject={subj}
                plan={planData}
                open={!!openSubjects[subj]}
                onToggle={() => toggleSubjectPlan(subj)}
                onDelete={() => handleDeletePlan(subj)}
              />
            ))}
        </div>
      ) : (
        !loading && <EmptyState />
      )}
    </div>
  );
}
