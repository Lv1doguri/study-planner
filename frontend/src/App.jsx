import { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar";
import Header from "./components/Header";
import DashboardHome from "./components/DashboardHome";
import TrackCurriculumTab from "./components/TrackCurriculumTab";
import DailyPlanTab from "./components/DailyPlanTab";
import MaterialTab from "./components/MaterialTab";
import QuizTab from "./components/QuizTab";
import QuizBankTab from "./components/QuizBankTab";
import TrendTab from "./components/TrendTab";
import { API_BASE } from "./lib/api";

export default function App() {
  const [active, setActive] = useState("dashboard");
  const [subjectSeed, setSubjectSeed] = useState("");
  const [quizSeed, setQuizSeed] = useState({ topic: "", content: "", numQuestions: null });
  const [xp, setXp] = useState({ level: 1, xpIntoLevel: 0, xpNeeded: 150 });
  const [levelUpFlash, setLevelUpFlash] = useState(null);

  const refreshXp = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/xp`);
      if (!response.ok) return;
      const data = await response.json();
      if (data.level > xp.level) {
        setLevelUpFlash(data.level);
      }
      setXp({ level: data.level, xpIntoLevel: data.xp_into_level, xpNeeded: data.xp_needed });
    } catch {
      // 백엔드가 꺼져 있으면 그냥 현재 화면 값을 유지한다
    }
  };

  useEffect(() => {
    refreshXp();
  }, []);

  useEffect(() => {
    if (levelUpFlash === null) return;
    const timer = setTimeout(() => setLevelUpFlash(null), 3000);
    return () => clearTimeout(timer);
  }, [levelUpFlash]);

  const { level, xpIntoLevel, xpNeeded } = xp;

  const goToQuiz = (topic, content, numQuestions = null) => {
    setQuizSeed({ topic, content, numQuestions });
    setActive("quiz");
  };

  return (
    <div className="min-h-screen bg-ink relative">
      <div className="pointer-events-none fixed -top-32 -left-32 w-96 h-96 bg-blue/20 rounded-full blur-3xl" />
      <div className="pointer-events-none fixed top-1/3 -right-32 w-96 h-96 bg-emerald/10 rounded-full blur-3xl" />

      <Header />
      <Sidebar active={active} onChange={setActive} level={level} xpIntoLevel={xpIntoLevel} xpNeeded={xpNeeded} />

      {levelUpFlash !== null && (
        <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50 bg-emerald text-ink font-bold px-6 py-3 rounded-full shadow-[0_0_30px_rgba(78,222,163,0.6)] animate-[fadeIn_0.3s_ease-out]">
          🎉 레벨 {levelUpFlash} 달성!
        </div>
      )}

      <main className="relative md:ml-64 pt-24 pb-12 px-4 md:px-8 max-w-6xl mx-auto">
        <div key={active} className="animate-[fadeIn_0.25s_ease-out]">
          {active === "dashboard" && (
            <DashboardHome
              level={level}
              xpIntoLevel={xpIntoLevel}
              xpNeeded={xpNeeded}
              onGoToQuiz={goToQuiz}
            />
          )}
          {active === "track" && (
            <TrackCurriculumTab
              initialSubject={subjectSeed}
              onSeedConsumed={() => setSubjectSeed("")}
              onXpChange={refreshXp}
              onGoToQuiz={goToQuiz}
            />
          )}
          {active === "daily" && <DailyPlanTab />}
          {active === "material" && <MaterialTab onSendToQuiz={goToQuiz} />}
          {active === "quiz" && (
            <QuizTab
              initialTopic={quizSeed.topic}
              initialContent={quizSeed.content}
              initialNumQuestions={quizSeed.numQuestions}
              onXpChange={refreshXp}
              onSeedConsumed={() => setQuizSeed({ topic: "", content: "", numQuestions: null })}
            />
          )}
          {active === "quizbank" && <QuizBankTab />}
          {active === "trend" && (<TrendTab
              onSelectGoal={(goal) => {
                setSubjectSeed(goal);
                setActive("track");
              }}
            />
          )}
        </div>
      </main>
    </div>
  );
}