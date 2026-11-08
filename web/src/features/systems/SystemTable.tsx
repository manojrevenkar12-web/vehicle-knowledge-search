import type { Results, Summary, SystemName } from "../../shared/api/types";
import { SYSTEMS } from "../../shared/api/types";
import { euro, pct, seconds } from "../../shared/format";
import { systemColor } from "../../theme/tokens";

const W = 140;

/** Each system on a set of queries: exact filters with their interval, by kind, latency and cost. */
export function SystemTable({ r, set }: { r: Results; set: Record<SystemName, Summary> }) {
  const kinds = Object.keys(set.graph.by_kind);
  const t = r.targets;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">System</th>
            <th scope="col">Exact filters</th>
            {kinds.map((k) => (
              <th key={k} scope="col" className="num">
                {k.replace("_", " ")}
              </th>
            ))}
            <th scope="col" className="num">p95</th>
            <th scope="col" className="num">Cost</th>
          </tr>
        </thead>
        <tbody>
          {SYSTEMS.map((s) => {
            const v = set[s];
            return (
              <tr key={s}>
                <th scope="row">
                  <span className="swatch" style={{ background: systemColor[s] }} aria-hidden="true" />
                  {r.names[s]}
                </th>
                <td>
                  <span className="rate">
                    <svg width={W} height="12" aria-hidden="true">
                      <rect width={W} height="12" rx="6" className="rate__track" />
                      <rect width={W * v.exact[0]} height="12" rx="6" fill={systemColor[s]} />
                      <line x1={W * v.exact[1]} x2={W * v.exact[2]} y1="6" y2="6" className="rate__ci" />
                    </svg>
                    {pct(v.exact[0])}
                  </span>
                </td>
                {kinds.map((k) => (
                  <td key={k} className={`num ${v.by_kind[k]! < 0.8 ? "is-bad" : ""}`}>
                    {pct(v.by_kind[k]!, 0)}
                  </td>
                ))}
                <td className={`num ${v.p95_ms > t.p95_latency_ms ? "is-bad" : ""}`}>{seconds(v.p95_ms)}</td>
                <td className={`num ${v.cost_eur > t.cost_per_query_eur ? "is-bad" : ""}`}>{euro(v.cost_eur)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="note">
        Exact: every filter the system set is the filter the query meant. The line on each bar is the 95% interval, resampling queries. Budgets: p95 {seconds(t.p95_latency_ms, 1)},{" "}
        {euro(t.cost_per_query_eur)} per query; red is over budget, or under 80% for a kind of query.
      </p>
    </div>
  );
}
