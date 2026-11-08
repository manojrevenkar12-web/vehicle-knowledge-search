import type { Results } from "../../shared/api/types";
import { SYSTEMS } from "../../shared/api/types";
import { pct } from "../../shared/format";
import { systemColor } from "../../theme/tokens";

/** What contacts can and cannot say about a system, next to what it really scores. */
export function SessionLabels({ r }: { r: Results }) {
  const s = r.dev.sessions;
  return (
    <div>
      <dl className="facts">
        <div>
          <dt>Contacted listings that fit what the user asked for</dt>
          <dd>{pct(s.label_precision)}</dd>
        </div>
        <div>
          <dt>Share of fitting listings that ever get a contact</dt>
          <dd>{pct(s.gold_share_labelled)}</dd>
        </div>
        <div>
          <dt>Queries with any contact</dt>
          <dd>
            {s.queries_with_contacts} of {s.queries}
          </dd>
        </div>
      </dl>
      <div className="table-wrap">
        <table className="table table--compact">
          <thead>
            <tr>
              <th scope="col">System</th>
              <th scope="col" className="num">Judged by contacts</th>
              <th scope="col" className="num">Exact filters (labelled)</th>
            </tr>
          </thead>
          <tbody>
            {SYSTEMS.map((k) => (
              <tr key={k}>
                <th scope="row">
                  <span className="swatch" style={{ background: systemColor[k] }} aria-hidden="true" />
                  {r.names[k]}
                </th>
                <td className="num">{pct(s.systems[k].contact_recall)}</td>
                <td className="num">{pct(s.systems[k].exact_true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="note">
        Vector retrieval served these sessions. Contacts are precise but sparse, and they only exist for listings that system showed: they cannot tell the three grounded
        systems apart, and they rate the model alone far above its real score. They are good for finding queries to label, not for scoring.
      </p>
    </div>
  );
}
