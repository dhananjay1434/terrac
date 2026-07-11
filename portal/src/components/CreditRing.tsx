// Compliance ring — fraction of checklist items passed, in the demo's visual
// language (emerald→sky gradient stroke over a faint track).
export default function CreditRing({
  okCount,
  total,
}: {
  okCount: number;
  total: number;
}) {
  const pct = total > 0 ? okCount / total : 0;
  const r = 63;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct);
  return (
    <div className="ring" role="img" aria-label={`${Math.round(pct * 100)}% of criteria met`}>
      <svg width="150" height="150" viewBox="0 0 150 150">
        <defs>
          <linearGradient id="ringgrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#12b981" />
            <stop offset="1" stopColor="#0ea5e9" />
          </linearGradient>
        </defs>
        <circle className="track" cx="75" cy="75" r={r} />
        <circle
          className="fill"
          cx="75"
          cy="75"
          r={r}
          strokeDasharray={c}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="center">
        <b className="tabular">{Math.round(pct * 100)}%</b>
        <small>criteria met</small>
      </div>
    </div>
  );
}
