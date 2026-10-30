import { Trophy } from "lucide-react";

export default function LevelPanel({ level, xpIntoLevel, xpNeeded }) {
  const ratio = Math.min(100, Math.round((xpIntoLevel / xpNeeded) * 100));
  return (
    <div className="bg-panel border border-panel-border rounded-2xl p-5">
      <p className="font-mono text-xs tracking-widest text-emerald uppercase mb-3">
        Study Quest Log
      </p>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-11 h-11 rounded-full bg-ink border border-panel-border flex items-center justify-center">
          <Trophy size={20} className="text-emerald" />
        </div>
        <p className="text-2xl font-extrabold leading-none">레벨 {level}</p>
      </div>
      <div className="flex justify-between text-xs text-text-muted mb-1">
        <span>경험치</span>
        <span>
          {xpIntoLevel} / {xpNeeded} XP
        </span>
      </div>
      <div className="w-full h-2 bg-ink rounded-full overflow-hidden">
        <div
          className="h-full bg-emerald transition-all duration-500"
          style={{ width: `${ratio}%` }}
        />
      </div>
    </div>
  );
}