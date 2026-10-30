import { useState } from "react";
import { Compass, Sparkles } from "lucide-react";
import { API_BASE } from "../lib/api";

const inputClass =
  "w-full bg-ink border border-panel-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-blue";

const labelClass =
  "block text-xs font-mono uppercase tracking-wide text-text-muted mb-1";

const primaryButtonClass =
  "bg-blue hover:bg-blue-bright text-white font-bold rounded-full px-5 py-2 transition-all shadow-[0_0_15px_rgba(5,102,217,0.35)] hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100";

const chipButtonClass =
  "text-xs font-mono uppercase tracking-wide bg-emerald text-ink font-bold rounded-full px-3 py-1.5 transition-transform hover:scale-[1.05] active:scale-[0.95]";

function EmptyState() {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <Compass className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">
        학과·학년을 입력하고 추천받으면, 여기에 방향이 나타납니다.
      </p>
    </div>
  );
}

export default function TrendTab({onSelectGoal}) {
  const [department, setDepartment] = useState("");
  const [year, setYear] = useState("");
  const [interest, setInterest] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async (e) => {
    e.preventDefault();

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(`${API_BASE}/api/trend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          department,
          year,
          interest_hint: interest,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "트렌드 분석에 실패했습니다.");
      }

      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p className="text-text-muted text-sm mb-4">
        아직 목표가 없어도 괜찮습니다. 학과·학년과 관심 분야를 입력하면 AI가
        현재 트렌드를 분석해 추천해줍니다.
      </p>

      <form onSubmit={handleSearch} className="space-y-4 mb-6">
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
          <label className={labelClass}>관심 있는 분야 (선택)</label>
          <input
            className={inputClass}
            placeholder="예: 백엔드 쪽이 궁금하다"
            value={interest}
            onChange={(e) => setInterest(e.target.value)}
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
              분석 중...
            </span>
          ) : (
            "트렌드 기반 추천받기"
          )}
        </button>
      </form>

      {error && (
        <div className="mb-6 bg-red-500/10 border border-red-500/30 text-red-300 rounded-xl p-4 text-sm">
          <p className="font-bold mb-1">분석 실패</p>
          <p>{error}</p>
        </div>
      )}

      {result ? (
        <div>
          <p className="text-sm text-text-muted mb-4">
            {result.analysis}
          </p>

          <div className="space-y-3">
            {result.recommendations.map((rec, i) => (
              <div
                key={i}
                className="bg-panel border border-panel-border rounded-xl p-4 hover:border-blue hover:-translate-y-0.5 transition-all"
              >
                <h4 className="font-bold mb-1">{rec.title}</h4>

                <p className="text-sm mb-1">
                  {rec.reason}
                </p>

                <p className="text-xs text-text-muted mb-3">
                  근거: {rec.evidence}
                </p>

                <button
                  type="button"
                  className={chipButtonClass}
                  onClick={()=>onSelectGoal(rec.title)}
                >
                  이 방향으로 커리큘럼 만들기
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : (
        !loading && <EmptyState />
      )}
    </div>
  );
}