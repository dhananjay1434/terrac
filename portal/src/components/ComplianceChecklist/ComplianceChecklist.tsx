import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown, AlertTriangle } from "lucide-react";
import type { ChecklistItem } from "../../api";
import { groupChecklist, statusOf, type ItemStatus } from "../../compliance";
import StatusDot from "../StatusDot/StatusDot";
import styles from "./ComplianceChecklist.module.css";

const STATUS_TEXT: Record<ItemStatus, string> = {
  ok: "OK",
  blocking: "MISSING",
  inert: "N/A",
};
const DOT_VARIANT: Record<ItemStatus, "success" | "warning" | "inert"> = {
  ok: "success",
  blocking: "warning",
  inert: "inert",
};
const SEVERITY: Record<ItemStatus, number> = { blocking: 0, inert: 1, ok: 2 };

/**
 * Grouped compliance checklist: one accordion section per methodology group
 * (grouping comes from compliance.ts — never reimplemented here), rows sorted
 * blocking → inert → ok, with a sticky mini-nav on wide screens. All sections
 * start expanded so nothing is hidden by default.
 */
export default function ComplianceChecklist({
  checklist,
}: {
  checklist: ChecklistItem[];
}) {
  const groups = groupChecklist(checklist);

  function jumpTo(group: string) {
    document
      .querySelector(`[data-testid="group-${group}"]`)
      ?.scrollIntoView?.({ behavior: "smooth", block: "start" });
  }

  return (
    <div className={styles.layout}>
      <Accordion.Root
        type="multiple"
        defaultValue={groups.map((g) => g.group)}
        className={styles.groups}
      >
        {groups.map((g) => {
          const inertCount = g.items.length - g.okCount - g.blockingCount;
          const sorted = [...g.items].sort(
            (a, b) => SEVERITY[statusOf(a)] - SEVERITY[statusOf(b)],
          );
          return (
            <Accordion.Item
              key={g.group}
              value={g.group}
              className={`card ${styles.item}`}
              data-testid={`group-${g.group}`}
            >
              <Accordion.Header className={styles.header}>
                <Accordion.Trigger className={styles.trigger}>
                  <span className="micro">{g.label}</span>
                  <span className={styles.counts}>
                    <StatusDot variant="success" label={`${g.okCount} ok`} />
                    {g.blockingCount > 0 && (
                      <StatusDot
                        variant="warning"
                        label={`${g.blockingCount} missing`}
                      />
                    )}
                    {inertCount > 0 && (
                      <StatusDot variant="inert" label={`${inertCount} n/a`} />
                    )}
                  </span>
                  <ChevronDown size={14} aria-hidden className={styles.chevron} />
                </Accordion.Trigger>
              </Accordion.Header>
              <Accordion.Content className={styles.content}>
                <ul className="crit-list">
                  {sorted.map((item) => {
                    const st = statusOf(item);
                    return (
                      <li
                        key={item.code}
                        className={`crit ${styles.row}`}
                        data-status={st}
                      >
                        {st === "blocking" ? (
                          <AlertTriangle
                            size={16}
                            aria-hidden
                            className={styles.blockingIcon}
                          />
                        ) : (
                          <StatusDot variant={DOT_VARIANT[st]} />
                        )}
                        <span className={styles.labelCol}>
                          <span className="crit-label">{item.label}</span>
                          <span className={`mono ${styles.code}`}>
                            {item.code}
                          </span>
                        </span>
                        {item.enforcement !== "enforced" && (
                          <span className={`chip ${styles.enforcement}`}>
                            {item.enforcement}
                          </span>
                        )}
                        <span
                          className={`crit-status micro ${styles[st]}`}
                        >
                          {STATUS_TEXT[st]}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              </Accordion.Content>
            </Accordion.Item>
          );
        })}
      </Accordion.Root>
      <aside className={styles.miniNav} aria-label="Checklist sections">
        {groups.map((g) => (
          <button
            key={g.group}
            type="button"
            className={styles.navBtn}
            onClick={() => jumpTo(g.group)}
          >
            <span className={styles.navLabel}>{g.label}</span>
            <span className="tabular">
              {g.okCount}/{g.items.length}
            </span>
          </button>
        ))}
      </aside>
    </div>
  );
}
