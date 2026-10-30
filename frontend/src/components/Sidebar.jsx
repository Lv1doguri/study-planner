import { LayoutDashboard, BookOpen, CalendarDays, ClipboardCheck, Compass, FileText, Trophy, Sparkles, Archive } from "lucide-react";

const NAV_ITEMS = [
  { key: "dashboard", label: "대시보드", icon: LayoutDashboard },
  { key: "track", label: "과목별 커리큘럼", icon: BookOpen },
  { key: "daily", label: "일별 맞춤 플랜", icon: CalendarDays },
  { key: "material", label: "강의자료 분석", icon: FileText },
  { key: "quiz", label: "주간 미니테스트", icon: ClipboardCheck },
  { key: "quizbank", label: "기출문제/오답노트", icon: Archive },
  { key: "trend", label: "막막할 때", icon: Compass },
];

export default function Sidebar({ active, onChange, level, xpIntoLevel, xpNeeded }) {
  const ratio = Math.min(100, Math.round((xpIntoLevel / xpNeeded) * 100));
  return (
    <nav className="hidden md:flex flex-col fixed left-0 top-16 h-[calc(100vh-64px)] w-64 bg-panel border-r border-panel-border p-4 z-40">
      <div className="flex flex-col items-center mb-8 pt-4">
        <div className="w-16 h-16 rounded-full bg-ink border-2 border-blue flex items-center justify-center mb-3">
          <Trophy size={26} className="text-emerald" />
        </div>
        <p className="font-bold text-sm">레벨 {level}</p>
        <p className="text-xs text-text-muted mt-0.5">
          {xpIntoLevel} / {xpNeeded} XP
        </p>
        <div className="w-full h-1.5 bg-ink rounded-full overflow-hidden mt-2">
          <div className="h-full bg-emerald transition-all duration-500" style={{ width: `${ratio}%` }} />
        </div>
      </div>

      <ul className="flex-1 space-y-1">
        {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
          <li key={key}>
            <button
              onClick={() => onChange(key)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all ${
                active === key
                  ? "bg-blue/10 text-blue font-bold"
                  : "text-text-muted hover:bg-ink hover:translate-x-1"
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          </li>
        ))}
      </ul>

      <button className="w-full flex items-center justify-center gap-2 bg-blue hover:bg-blue-bright text-white font-bold rounded-lg py-3 transition-all hover:scale-[1.02]">
        <Sparkles size={16} />
        새 목표 생성
      </button>
    </nav>
  );
}