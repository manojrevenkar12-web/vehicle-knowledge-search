import type { Results, SystemName, Week } from "../../shared/api/types";
import { pct } from "../../shared/format";
import { color, systemColor, timeline as T } from "../../theme/tokens";

const SHOWN: SystemName[] = ["graph", "graph_agent"];

/** Exact filters per production week for the graph with and without the validator, the events, and the alerts. */
export function Timeline({ r }: { r: Results }) {
  const P = r.dev.production;
  const series = SHOWN.filter((s) => P[s]?.length);
  if (!series.length) return null;
  const weeks = P[series[0]!]!.map((w) => w.week);
  const n = weeks.length;
  const x = (w: number) => T.left + ((T.width - T.left - T.right) * (w - 1)) / Math.max(1, n - 1);
  const y = (v: number) => T.top + ((T.height - T.top - T.bottom) * (1 - (v - T.floor) / (1 - T.floor))) ;
  const c = r.config.production;
  const events = [
    { w: c.season_week, label: "winter" },
    { w: c.launch_week, label: "EV2 on sale" },
    { w: c.launch_week + c.kg_update_lag_weeks, label: "EV2 in the graph" },
    { w: c.llm_update_week, label: "LLM upgraded" },
  ];
  const agent = P.graph_agent ?? [];
  return (
    <figure className="figure">
      <svg className="timeline" viewBox={`0 0 ${T.width} ${T.height}`} role="img" aria-label="Exact filters per production week, with and without the validator">
        {[0.8, 0.9, 1].map((v) => (
          <g key={v}>
            <line x1={T.left} x2={T.width - T.right} y1={y(v)} y2={y(v)} stroke={color.rule} />
            <text x={T.left - 6} y={y(v) + 4} textAnchor="end" className="tick">
              {pct(v, 0)}
            </text>
          </g>
        ))}
        {events.map((e, i) => (
          <g key={e.label}>
            <line x1={x(e.w)} x2={x(e.w)} y1={T.top - 6} y2={T.height - T.bottom} stroke={color.event} strokeDasharray="3 4" />
            <text x={x(e.w) + 4} y={T.top - 10 + (i % 2) * 14} className="tick tick--event">
              {e.label}
            </text>
          </g>
        ))}
        {series.map((s) => {
          const ws = P[s] as Week[];
          return (
            <g key={s}>
              <polyline fill="none" stroke={systemColor[s]} strokeWidth={2.5} points={ws.map((w) => `${x(w.week)},${y(Math.max(T.floor, w.exact_true))}`).join(" ")} />
              {ws.map((w) => (
                <circle key={w.week} cx={x(w.week)} cy={y(Math.max(T.floor, w.exact_true))} r={T.dot} fill={systemColor[s]} />
              ))}
            </g>
          );
        })}
        {weeks.map((w) => (
          <text key={w} x={x(w)} y={T.height - T.bottom + 18} textAnchor="middle" className="tick">
            {w}
          </text>
        ))}
      </svg>
      <div className="legend">
        {series.map((s) => (
          <span key={s}>
            <span className="swatch" style={{ background: systemColor[s] }} aria-hidden="true" />
            {r.names[s]}
          </span>
        ))}
      </div>
      <div className="table-wrap">
        <table className="table table--compact">
          <thead>
            <tr>
              <th scope="col">Week</th>
              <th scope="col" className="num">Exact (true)</th>
              <th scope="col" className="num">Labelled sample</th>
              <th scope="col" className="num">Zero results</th>
              <th scope="col" className="num">Unknown names</th>
              <th scope="col" className="num">Invalid values</th>
              <th scope="col" className="num">Query drift (PSI)</th>
              <th scope="col">Alerts</th>
            </tr>
          </thead>
          <tbody>
            {agent.map((w) => (
              <tr key={w.week}>
                <th scope="row">{w.week}</th>
                <td className="num">{pct(w.exact_true)}</td>
                <td className="num">
                  {pct(w.exact_labelled[0], 0)} <span className="muted">({pct(w.exact_labelled[1], 0)}–{pct(w.exact_labelled[2], 0)})</span>
                </td>
                <td className="num">{pct(w.zero_results)}</td>
                <td className="num">{pct(w.unknown_entities)}</td>
                <td className="num">{pct(w.hallucinations)}</td>
                <td className="num">{w.psi.toFixed(2)}</td>
                <td>{w.alerts.length ? w.alerts.map((a) => <span key={a} className="alert">{a}</span>) : <span className="muted">none</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption className="note">
        The table is the graph with the validator. Monitors read only the log; the labelled sample is {c.labelled_per_week} queries a person checks each week, too few to see a
        ten-point drop on its own. Invalid values in weeks 10 to 12 are the upgraded model misreading “Tsd”; the validator repairs them, so they are alerts, not wrong results.
      </figcaption>
    </figure>
  );
}
