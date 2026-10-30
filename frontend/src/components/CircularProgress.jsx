export default function CircularProgress({ percent, color = "#4edea3", label, sublabel }) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  return (
    <div className="flex items-center gap-4">
      <div className="relative w-16 h-16 shrink-0">
        <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
          <circle cx="18" cy="18" r={radius} fill="none" stroke="#2a3033" strokeWidth="3" />
          <circle
            cx="18"
            cy="18"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center text-[10px] font-mono">{percent}%</div>
      </div>
      <div>
        <p className="text-sm font-semibold leading-tight">{label}</p>
        <p className="text-xs text-text-muted mt-1">{sublabel}</p>
      </div>
    </div>
  );
}