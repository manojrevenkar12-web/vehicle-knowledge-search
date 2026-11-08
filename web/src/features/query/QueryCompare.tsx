import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import type { Example, Results, SystemName } from "../../shared/api/types";
import { SYSTEMS } from "../../shared/api/types";
import { filterLabel, filterValue, kindLabel } from "../../shared/format";
import { Segmented } from "../../shared/ui/Segmented";
import { chips, systemColor } from "../../theme/tokens";

function same(a: unknown, b: unknown): boolean {
  if (Array.isArray(a) || Array.isArray(b)) return JSON.stringify([...((a as unknown[]) ?? [])].sort()) === JSON.stringify([...((b as unknown[]) ?? [])].sort());
  return a === b;
}

/** The filters one system set for the query, each marked against what the query meant. */
function FilterChips({ ex, sys }: { ex: Example; sys: SystemName }) {
  const f = ex.systems[sys].filters;
  const keys = Array.from(new Set([...Object.keys(ex.gold), ...Object.keys(f)]));
  return (
    <ul className="chips" aria-label="Filters">
      <AnimatePresence mode="popLayout" initial={false}>
        {keys.map((k, i) => {
          const has = k in f;
          const meant = k in ex.gold;
          const status = !has ? "missing" : !meant ? "extra" : same(f[k], ex.gold[k]) ? "right" : "wrong";
          return (
            <motion.li
              key={`${sys}-${k}`}
              className={`chip chip--${status}`}
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: chips.settle, delay: i * chips.stagger }}
            >
              <span className="chip__key">{filterLabel(k)}</span>
              <span className="chip__value">{has ? filterValue(k, f[k]) : "not set"}</span>
              {(status === "wrong" || status === "missing") && <span className="chip__meant">meant {filterValue(k, ex.gold[k])}</span>}
            </motion.li>
          );
        })}
      </AnimatePresence>
    </ul>
  );
}

/** One query, answered by each system: the filters it set and how many listings that finds. */
export function QueryCompare({ r }: { r: Results }) {
  const [pick, setPick] = useState(r.examples[0]?.id ?? "");
  const [sys, setSys] = useState<SystemName>("llm_only");
  const ex = r.examples.find((e) => e.id === pick) ?? r.examples[0];
  if (!ex) return null;
  const a = ex.systems[sys];
  return (
    <div className="compare">
      <Segmented label="Query" value={ex.id} onChange={setPick} options={r.examples.map((e) => ({ id: e.id, label: kindLabel[e.kind] ?? e.kind }))} />
      <div className="compare__panel">
        <p className="query" aria-label="Search query">
          {ex.text}
        </p>
        <div className="compare__systems">
          <Segmented label="System" value={sys} onChange={(v) => setSys(v as SystemName)} options={SYSTEMS.map((s) => ({ id: s, label: r.names[s] }))} />
        </div>
        <FilterChips ex={ex} sys={sys} />
        <p className="compare__outcome">
          <span className="swatch" style={{ background: systemColor[sys] }} aria-hidden="true" />
          {a.exact ? (
            <span className="is-good">Every filter as meant: {a.results} listings.</span>
          ) : (
            <span className="is-bad">
              {a.results} listings, against {ex.gold_results} the query meant.
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
