import type { ChecklistItem } from "../api";
import { groupChecklist, statusOf } from "../compliance";

const DOT: Record<string, string> = {
  ok: "var(--status-success-fg)",
  blocking: "var(--status-warning-fg)",
  inert: "var(--text-tertiary)",
};

const STATUS_TEXT: Record<string, string> = {
  ok: "OK",
  blocking: "MISSING",
  inert: "N/A",
};

export default function ComplianceChecklist({
  checklist,
}: {
  checklist: ChecklistItem[];
}) {
  const groups = groupChecklist(checklist);
  return (
    <div>
      {groups.map((g) => (
        <section key={g.group} className="card group" data-testid={`group-${g.group}`}>
          <header className="group-head">
            <span className="micro">{g.label}</span>
            <span className="micro tabular">
              {g.okCount}/{g.items.length}
              {g.blockingCount > 0 && (
                <b className="amber-tag"> · {g.blockingCount} missing</b>
              )}
            </span>
          </header>
          <ul className="crit-list">
            {g.items.map((item) => {
              const st = statusOf(item);
              return (
                <li key={item.code} className="crit" data-status={st}>
                  <span className="crit-dot" style={{ background: DOT[st] }} />
                  <span className="crit-label">{item.label}</span>
                  <span className="crit-status micro" style={{ color: DOT[st] }}>
                    {STATUS_TEXT[st]}
                  </span>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}
