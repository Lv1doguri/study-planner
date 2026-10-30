import { useEffect, useState } from "react";
import { BookOpen, ClipboardCheck, GraduationCap, GripVertical, Plus, Trash2 } from "lucide-react";
import { API_BASE } from "../lib/api";

function buildSubjectStudyContent(items) {
  return items
    .filter((item) => item.content)
    .map((item) => `[${item.title}]\n${item.content}`)
    .join("\n\n");
}

const API_URL = API_BASE;

const inputClass =
  "w-full bg-ink border border-panel-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-blue";

const buttonClass =
  "bg-blue hover:bg-blue-bright text-white font-bold rounded-full px-4 py-2 text-sm transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:hover:scale-100 shrink-0";

function EmptyState() {
  return (
    <div className="bg-panel border border-dashed border-panel-border rounded-xl p-10 text-center">
      <BookOpen className="mx-auto mb-3 text-text-muted" size={28} />
      <p className="text-sm text-text-muted">
        아직 등록한 과목이 없습니다. 아래에서 과목을 추가해보세요.
      </p>
    </div>
  );
}

function SubjectCard({
  subject,
  items,
  onAddItem,
  onToggleItem,
  onEditTitle,
  onDeleteItem,
  onDeleteSubject,
  onMakeQuiz,
  onMakeExam,
  onReorderItems,
}) {
  const [newItemTitle, setNewItemTitle] = useState("");
  const [dragItemId, setDragItemId] = useState(null);
  const [expandedIds, setExpandedIds] = useState(() => new Set());
  const completedCount = items.filter((item) => item.done).length;
  const ratio = items.length ? Math.round((completedCount / items.length) * 100) : 0;
  const hasContent = items.some((item) => item.content);

  const toggleExpanded = (itemId) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(itemId)) next.delete(itemId);
      else next.add(itemId);
      return next;
    });
  };

  const handleDrop = (targetId) => {
    if (dragItemId === null || dragItemId === targetId) {
      setDragItemId(null);
      return;
    }
    const ids = items.map((i) => i.id);
    const fromIndex = ids.indexOf(dragItemId);
    const toIndex = ids.indexOf(targetId);
    ids.splice(fromIndex, 1);
    ids.splice(toIndex, 0, dragItemId);
    onReorderItems(ids);
    setDragItemId(null);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const title = newItemTitle.trim();
    if (!title) return;
    onAddItem(title);
    setNewItemTitle("");
  };

  return (
    <div className="bg-panel border border-panel-border rounded-xl p-4">
      <div className="flex items-center justify-between gap-3 mb-2">
        <h3 className="font-bold text-sm">{subject}</h3>
        <div className="flex items-center gap-3 shrink-0">
          <span className="text-xs font-mono text-text-muted">
            {completedCount} / {items.length} 완료
          </span>
          {hasContent && (
            <button
              type="button"
              onClick={onMakeExam}
              className="flex items-center gap-1 text-xs font-mono uppercase tracking-wide text-blue hover:text-blue-bright transition-colors"
              title="지금까지 공부한 내용을 모아 모의고사 만들기"
            >
              <GraduationCap size={14} />
              모의고사
            </button>
          )}
          <button
            type="button"
            onClick={onDeleteSubject}
            className="text-text-muted hover:text-coral transition-colors"
            title="과목 삭제"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="w-full h-1.5 bg-ink rounded-full overflow-hidden mb-3">
        <div className="h-full bg-blue transition-all duration-500" style={{ width: `${ratio}%` }} />
      </div>

      <div className="space-y-2 mb-3">
        {items.map((item) => {
          const hasDetail = (item.concepts && item.concepts.length > 0) || item.practice;
          const expanded = expandedIds.has(item.id);

          return (
            <div key={item.id}>
              <div
                draggable
                onDragStart={() => setDragItemId(item.id)}
                onDragOver={(e) => e.preventDefault()}
                onDrop={() => handleDrop(item.id)}
                onDragEnd={() => setDragItemId(null)}
                className={`flex items-center gap-2 rounded-lg transition-opacity ${
                  dragItemId === item.id ? "opacity-40" : ""
                }`}
              >
                <GripVertical size={14} className="text-text-muted cursor-grab shrink-0" />
                <input
                  type="checkbox"
                  checked={item.done}
                  onChange={() => onToggleItem(item)}
                  className="w-4 h-4 accent-blue shrink-0"
                />
                {item.emoji && <span className="text-sm leading-none shrink-0">{item.emoji}</span>}
                <input
                  className={`flex-1 bg-transparent text-sm px-2 py-1 rounded-lg focus:outline-none focus:bg-ink ${
                    item.done ? "line-through text-text-muted" : "text-text-primary"
                  }`}
                  value={item.title}
                  onChange={(e) => onEditTitle(item, e.target.value)}
                  onBlur={(e) => onEditTitle(item, e.target.value, true)}
                />
                {hasDetail && (
                  <button
                    type="button"
                    onClick={() => toggleExpanded(item.id)}
                    className="text-text-muted hover:text-blue transition-colors shrink-0 text-xs"
                    title="일별 플랜 내용 보기"
                  >
                    {expanded ? "▲" : "▼"}
                  </button>
                )}
                {item.content && (
                  <button
                    type="button"
                    onClick={() => onMakeQuiz(item)}
                    className="text-text-muted hover:text-emerald transition-colors shrink-0"
                    title="이 내용으로 미니테스트 만들기"
                  >
                    <ClipboardCheck size={14} />
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => onDeleteItem(item)}
                  className="text-text-muted hover:text-coral transition-colors shrink-0"
                  title="항목 삭제"
                >
                  <Trash2 size={14} />
                </button>
              </div>

              {expanded && hasDetail && (
                <div className="ml-6 mt-1.5 mb-2 pl-3 border-l-2 border-panel-border animate-[fadeIn_0.2s_ease-out]">
                  {item.concepts && item.concepts.length > 0 && (
                    <ul className="list-disc list-inside text-sm text-text-muted space-y-0.5">
                      {item.concepts.map((concept, i) => (
                        <li key={i}>{concept}</li>
                      ))}
                    </ul>
                  )}
                  {item.practice && (
                    <div className="bg-ink border border-panel-border rounded-lg p-3 mt-2">
                      <p className="text-[10px] font-mono uppercase tracking-wide text-emerald mb-1">
                        직접 해보기
                      </p>
                      <pre className="text-xs font-mono text-text-primary whitespace-pre-wrap leading-relaxed">
                        {item.practice}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
        {items.length === 0 && (
          <p className="text-xs text-text-muted">아직 항목이 없습니다.</p>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          className={inputClass}
          placeholder="새 항목 추가 (예: 카르노맵 정리)"
          value={newItemTitle}
          onChange={(e) => setNewItemTitle(e.target.value)}
        />
        <button type="submit" className={buttonClass}>
          <Plus size={16} />
        </button>
      </form>
    </div>
  );
}

export default function TrackCurriculumTab({ initialSubject = "", onSeedConsumed, onXpChange, onGoToQuiz }) {
  const [subjects, setSubjects] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [newSubjectName, setNewSubjectName] = useState(initialSubject);

  useEffect(() => {
    if (initialSubject) onSeedConsumed?.();
  }, []);

  useEffect(() => {
    const fetchCurriculum = async () => {
      try {
        setLoading(true);
        setError("");
        const response = await fetch(`${API_URL}/api/custom-curriculum`);
        if (!response.ok) {
          throw new Error("과목별 커리큘럼을 가져오는데 실패했습니다.");
        }
        const data = await response.json();
        setSubjects(data.subjects);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchCurriculum();
  }, []);

  const handleAddSubject = async (e) => {
    e.preventDefault();
    const subject = newSubjectName.trim();
    if (!subject || subjects[subject]) return;

    const response = await fetch(`${API_URL}/api/custom-curriculum/subject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
      setNewSubjectName("");
    }
  };

  const handleDeleteSubject = async (subject) => {
    const response = await fetch(`${API_URL}/api/custom-curriculum/subject`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
    }
  };

  const handleAddItem = async (subject, title) => {
    const response = await fetch(`${API_URL}/api/custom-curriculum/item`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, title }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
    }
  };

  const handleToggleItem = async (subject, item) => {
    const nextDone = !item.done;

    setSubjects((prev) => ({
      ...prev,
      [subject]: prev[subject].map((i) => (i.id === item.id ? { ...i, done: nextDone } : i)),
    }));

    const response = await fetch(`${API_URL}/api/custom-curriculum/item`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, item_id: item.id, done: nextDone }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
      onXpChange?.();
    }
  };

  const handleEditTitle = (subject, item, title, commit) => {
    setSubjects((prev) => ({
      ...prev,
      [subject]: prev[subject].map((i) => (i.id === item.id ? { ...i, title } : i)),
    }));

    if (!commit || title.trim() === item.title) return;

    fetch(`${API_URL}/api/custom-curriculum/item`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, item_id: item.id, title: title.trim() }),
    });
  };

  const handleReorderItems = async (subject, itemIds) => {
    setSubjects((prev) => {
      const itemsById = Object.fromEntries(prev[subject].map((i) => [i.id, i]));
      return { ...prev, [subject]: itemIds.map((id) => itemsById[id]) };
    });

    const response = await fetch(`${API_URL}/api/custom-curriculum/reorder-items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, item_ids: itemIds }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
    }
  };

  const handleDeleteItem = async (subject, item) => {
    const response = await fetch(`${API_URL}/api/custom-curriculum/item`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ subject, item_id: item.id }),
    });
    if (response.ok) {
      const data = await response.json();
      setSubjects(data.subjects);
    }
  };

  if (loading) {
    return (
      <div>
        <h2 className="text-xl font-extrabold mb-4">과목별 커리큘럼</h2>
        <p className="text-text-muted">불러오는 중...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h2 className="text-xl font-extrabold mb-4">과목별 커리큘럼</h2>
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  const subjectNames = Object.keys(subjects);

  return (
    <div>
      <h2 className="text-xl font-extrabold mb-1">과목별 커리큘럼</h2>
      <p className="text-text-muted text-sm mb-4">
        과목을 추가하고, 그 안에 직접 공부할 항목을 적어서 체크해나가세요.
      </p>

      <form onSubmit={handleAddSubject} className="flex gap-2 mb-6">
        <input
          className={inputClass}
          placeholder="새 과목 추가 (예: 논리회로)"
          value={newSubjectName}
          onChange={(e) => setNewSubjectName(e.target.value)}
        />
        <button type="submit" className={buttonClass}>
          과목 추가
        </button>
      </form>

      {subjectNames.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="space-y-4">
          {subjectNames.map((subject) => (
            <SubjectCard
              key={subject}
              subject={subject}
              items={subjects[subject]}
              onAddItem={(title) => handleAddItem(subject, title)}
              onToggleItem={(item) => handleToggleItem(subject, item)}
              onEditTitle={(item, title, commit) => handleEditTitle(subject, item, title, commit)}
              onDeleteItem={(item) => handleDeleteItem(subject, item)}
              onDeleteSubject={() => handleDeleteSubject(subject)}
              onMakeQuiz={(item) => onGoToQuiz(item.title, item.content)}
              onMakeExam={() =>
                onGoToQuiz(`${subject} 중간고사 대비 모의고사`, buildSubjectStudyContent(subjects[subject]), 15)
              }
              onReorderItems={(itemIds) => handleReorderItems(subject, itemIds)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
