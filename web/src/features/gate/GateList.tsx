import type { GateDecision, Results } from "../../shared/api/types";
import { euro, pts, seconds } from "../../shared/format";

/** Every proposed change, against the graph with the validator. */
export function GateList({ r }: { r: Results }) {
  const g: Record<string, GateDecision> = r.dev.gate;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th scope="col">Change</th>
            <th scope="col">Decision</th>
            <th scope="col" className="num">Exact filters</th>
            <th scope="col" className="num">p95</th>
            <th scope="col" className="num">Cost</th>
            <th scope="col">Why</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(g).map(([name, d]) => (
            <tr key={name}>
              <th scope="row">{name}</th>
              <td>
                <span className={`status status--${d.blocked ? "wrong" : "right"}`}>{d.blocked ? "Blocked" : "Passes"}</span>
              </td>
              <td className="num">
                {pts(d.exact[0])}
                <span className="cell-sub">lower bound {pts(d.exact[1])}</span>
              </td>
              <td className="num">{seconds(d.budget.p95_ms)}</td>
              <td className="num">{euro(d.budget.cost_eur)}</td>
              <td className="why">{d.reasons.length ? d.reasons.map((x) => x.charAt(0).toUpperCase() + x.slice(1)).join(". ") + "." : "Nothing got worse."}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">
        Blocked when the paired lower bound on exact filters is below −{(100 * r.config.gate_max_drop).toFixed(0)} points, when a labelled production case the current
        system passes fails, or when a change breaks the latency or cost budget. Dropping the validator changes nothing on the development queries; the production cases are
        what catch it.
      </p>
    </div>
  );
}
