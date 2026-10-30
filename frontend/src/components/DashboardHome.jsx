import { useEffect, useState } from "react";
import { Trophy, ListChecks, HelpCircle } from "lucide-react";
import CircularProgress from "./CircularProgress";
import { API_BASE } from "../lib/api";

const PROGRESS_COLORS = ["#0566d9", "#4edea3", "#ef6461", "#2e7fea", "#8a929a"];

function buildSubjectProgress(subjects) {
  return Object.entries(subjects).map(([name, items], i) => {
    const total = items.length;
    const done = items.filter((item) => item.done).length;
    return {
      label: name,
      sublabel: `${done} / ${total} 단계`,
      percent: total ? Math.round((done / total) * 100) : 0,
      color: PROGRESS_COLORS[i % PROGRESS_COLORS.length],
    };
  });
}

const ACTIVITY_ICON = {
  step_completed: "✅",
  quiz_graded: "📝",
  daily_plan_generated: "📅",
  study_list_generated: "📄",
  lecture_analysis_generated: "🎓",
};

function isSameLocalDate(a, b) {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function groupByDay(activities) {
  const now = new Date();
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  const today = [];
  const prevDay = [];

  for (const activity of activities) {
    const when = new Date(activity.timestamp);
    if (isSameLocalDate(when, now)) {
      today.push(activity);
    } else if (isSameLocalDate(when, yesterday)) {
      prevDay.push(activity);
    }
  }

  return { today, prevDay };
}

function buildWeeklyQuizContent(items) {
  return items.map((item) => `[${item.subject} · ${item.title}]\n${item.content}`).join("\n\n");
}

function ActivityGroup({ title, activities }) {
  return (
    <div>
      <p className="text-xs font-mono uppercase tracking-wide text-text-muted mb-2">{title}</p>

      {activities.length === 0 ? (
        <p className="text-sm text-text-muted">기록이 없습니다.</p>
      ) : (
        <ul className="space-y-2">
          {activities.map((activity, i) => (
            <li
              key={i}
              className="flex items-start gap-3 p-3 rounded-xl border border-panel-border"
            >
              <span className="text-lg leading-none shrink-0">
                {ACTIVITY_ICON[activity.type] || "•"}
              </span>
              <div className="flex-1">
                <p className="font-semibold text-sm">{activity.title}</p>
                <p className="text-xs text-text-muted mt-0.5">
                  {new Date(activity.timestamp).toLocaleTimeString("ko-KR", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
              {activity.xp_delta !== 0 && (
                <span className="text-xs font-mono text-emerald whitespace-nowrap">
                  +{activity.xp_delta} XP
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function DashboardHome({ level, xpIntoLevel, xpNeeded, onGoToQuiz }) {
  const ratio = Math.min(100, Math.round((xpIntoLevel / xpNeeded) * 100));
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activityOpen, setActivityOpen] = useState(true);
  const [weeklyItems, setWeeklyItems] = useState([]);
  const [subjectProgress, setSubjectProgress] = useState([]);

  useEffect(() => {
    const fetchActivity = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/activity?days=2`);
        if (response.ok) {
          const data = await response.json();
          setActivities(data.activities);
        }
      } catch {
        // 백엔드가 꺼져 있으면 빈 목록으로 보여준다
      } finally {
        setLoading(false);
      }
    };

    const fetchWeeklyItems = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/custom-curriculum/recent-completed?days=7`);
        if (response.ok) {
          const data = await response.json();
          setWeeklyItems(data.items);
        }
      } catch {
        // 백엔드가 꺼져 있으면 빈 목록으로 보여준다
      }
    };

    const fetchCurriculumProgress = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/custom-curriculum`);
        if (response.ok) {
          const data = await response.json();
          setSubjectProgress(buildSubjectProgress(data.subjects));
        }
      } catch {
        // 백엔드가 꺼져 있으면 빈 목록으로 보여준다
      }
    };

    fetchActivity();
    fetchWeeklyItems();
    fetchCurriculumProgress();
  }, []);

  const { today, prevDay } = groupByDay(activities);

  // "다음 목표"는 진행률이 가장 낮은(가장 손봐야 할) 과목을 보여준다 — 이미 커리큘럼
  // 진행률용으로 받아온 데이터를 그대로 재사용한다.
  const nextGoalSubject = subjectProgress.length
    ? subjectProgress.reduce((lowest, p) => (p.percent < lowest.percent ? p : lowest))
    : null;
  const allSubjectsDone = subjectProgress.length > 0 && subjectProgress.every((p) => p.percent === 100);

  return (
    <div className="space-y-6">
      <div className="bg-panel border border-panel-border rounded-2xl p-6 md:p-8">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex-1 w-full">
            <h1 className="text-2xl font-extrabold mb-2">레벨 {level}</h1>
            <p className="text-sm text-text-muted mb-4 flex items-center gap-1.5">
              <Trophy size={14} className="text-emerald" />
              {nextGoalSubject ? (
                allSubjectsDone ? (
                  <span className="text-text-primary font-semibold">모든 과목 완료! 🎉</span>
                ) : (
                  <>
                    다음 목표:{" "}
                    <span className="text-text-primary font-semibold">
                      {nextGoalSubject.label} ({nextGoalSubject.sublabel})
                    </span>
                  </>
                )
              ) : (
                <span>아직 등록한 과목이 없어요</span>
              )}
            </p>
            <div className="w-full h-3 bg-ink rounded-full overflow-hidden">
              <div className="h-full bg-blue transition-all duration-500" style={{ width: `${ratio}%` }} />
            </div>
            <div className="flex justify-between text-xs text-text-muted mt-2 font-mono">
              <span>{xpIntoLevel} XP</span>
              <span>{xpNeeded} XP</span>
            </div>
          </div>
          <div className="hidden md:flex flex-col items-center justify-center w-28 h-28 rounded-full bg-ink border border-panel-border shadow-[0_0_20px_rgba(78,222,163,0.25)]">
            <Trophy size={28} className="text-emerald mb-1" />
            <p className="text-[10px] text-text-muted text-center leading-tight">
              마스터리
              <br />
              달성 임박
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-panel border border-panel-border rounded-2xl p-6">
            <button
              type="button"
              onClick={() => setActivityOpen(!activityOpen)}
              className="w-full flex items-center justify-between mb-5"
            >
              <h2 className="font-bold flex items-center gap-2">
                <ListChecks size={18} className="text-blue" />
                최근 활동
              </h2>
              <span className="text-text-muted text-sm">{activityOpen ? "▲" : "▼"}</span>
            </button>

            {activityOpen &&
              (loading ? (
                <p className="text-sm text-text-muted">불러오는 중...</p>
              ) : (
                <div className="space-y-5">
                  <ActivityGroup title="오늘" activities={today} />
                  <ActivityGroup title="어제" activities={prevDay} />
                </div>
              ))}
          </div>

          <div className="bg-panel border border-blue/30 rounded-2xl p-6 flex flex-col sm:flex-row items-center gap-5">
            <div className="w-14 h-14 rounded-full bg-blue/10 border border-blue/30 flex items-center justify-center shrink-0">
              <HelpCircle size={26} className="text-blue" />
            </div>
            <div className="flex-1 text-center sm:text-left">
              {weeklyItems.length > 0 ? (
                <>
                  <h3 className="font-bold mb-1">이번 주 미니테스트가 준비됐어요</h3>
                  <p className="text-sm text-text-muted">
                    이번 주에 체크한 {weeklyItems.length}개 항목을 바탕으로 문제를 만들 수 있어요.
                  </p>
                </>
              ) : (
                <>
                  <h3 className="font-bold mb-1">이번 주에 체크한 항목이 아직 없어요</h3>
                  <p className="text-sm text-text-muted">
                    "과목별 커리큘럼"에서 항목을 체크하면, 그 내용으로 여기서 미니테스트를 만들 수 있어요.
                  </p>
                </>
              )}
            </div>
            <button
              type="button"
              disabled={weeklyItems.length === 0}
              onClick={() =>
                onGoToQuiz(
                  "이번 주 체크한 내용 총정리",
                  buildWeeklyQuizContent(weeklyItems),
                  Math.min(10, Math.max(5, weeklyItems.length))
                )
              }
              className="bg-blue hover:bg-blue-bright text-white font-bold rounded-full px-5 py-2 transition-all hover:scale-[1.02] disabled:opacity-40 disabled:hover:scale-100 whitespace-nowrap"
            >
              퀴즈 풀러 가기
            </button>
          </div>
        </div>

        <div className="bg-panel border border-panel-border rounded-2xl p-6">
          <h2 className="font-bold mb-5">커리큘럼 진행률</h2>
          {subjectProgress.length === 0 ? (
            <p className="text-sm text-text-muted">
              아직 등록한 과목이 없어요. "과목별 커리큘럼"에서 과목을 추가해보세요.
            </p>
          ) : (
            <div className="space-y-6">
              {subjectProgress.map((p, i) => (
                <CircularProgress key={i} {...p} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
