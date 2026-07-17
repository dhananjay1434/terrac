import styles from "./ActivityTimeline.module.css";

export interface ActivityEvent {
  id: string;
  actor: string;
  action: string;
  at: string;
  meta?: string;
}

/**
 * Vertical activity timeline. The portal API exposes no activity/history
 * fields on BatchDetail today, so callers pass [] and users see an honest
 * empty state — events are never fabricated.
 */
export default function ActivityTimeline({
  events,
}: {
  events: ActivityEvent[];
}) {
  if (events.length === 0) {
    return (
      <div className="card" style={{ marginTop: 14 }} data-testid="activity-empty">
        <span className="micro">Activity</span>
        <div className={styles.empty}>
          Activity log will appear here once the backend exposes it.
        </div>
      </div>
    );
  }
  return (
    <div className="card" style={{ marginTop: 14 }}>
      <span className="micro">Activity</span>
      <ol className={styles.timeline}>
        {events.map((e) => (
          <li key={e.id} className={styles.event}>
            <span className={styles.dot} aria-hidden />
            <div className={styles.body}>
              <div className={styles.action}>
                <b>{e.actor}</b> {e.action}
              </div>
              <div className={`${styles.time} tabular`}>
                {e.at.slice(0, 16).replace("T", " ")}
              </div>
              {e.meta && <div className={styles.metaText}>{e.meta}</div>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
