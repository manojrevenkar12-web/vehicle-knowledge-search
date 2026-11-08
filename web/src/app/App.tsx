import { MotionConfig } from "framer-motion";
import { base, fetchJSON } from "../shared/api/client";
import type { Results } from "../shared/api/types";
import { useResource } from "../shared/hooks/useResource";
import { Empty, ErrorState, Section, Skeleton } from "../shared/ui/States";
import { pct } from "../shared/format";
import { QueryCompare } from "../features/query/QueryCompare";
import { SystemTable } from "../features/systems/SystemTable";
import { Timeline } from "../features/production/Timeline";
import { SessionLabels } from "../features/sessions/SessionLabels";
import { GateList } from "../features/gate/GateList";

const RESULTS = `${base}/results.json`;

export function App() {
  const res = useResource((s) => fetchJSON<Results>(RESULTS, s), RESULTS);
  return (
    <MotionConfig reducedMotion="user">
      <main className="page">
        <p className="masthead">vehicle-knowledge-search</p>
        {res.state === "loading" && <Skeleton />}
        {res.state === "error" && <ErrorState error={res.error} onRetry={res.retry} />}
        {res.state === "ready" && <Report r={res.data} />}
      </main>
    </MotionConfig>
  );
}

function Headline({ r }: { r: Results }) {
  const set = r.heldout?.systems ?? r.dev.systems;
  return (
    <h1>
      Grounded in the knowledge graph, natural-language car search sets every filter right {pct(set.graph_agent.exact[0], 0)} of the time{r.heldout ? " on queries nobody looked at" : ""}. The
      model alone manages {pct(set.llm_only.exact[0], 0)}.
    </h1>
  );
}

function Report({ r }: { r: Results }) {
  return (
    <>
      <header className="hero">
        <Headline r={r} />
        <p className="hero__lead">
          A query like “Golf 7 GTI unter 20 Tsd” or “sparsamer Familien-SUV mit Anhängerkupplung” has to become result-page filters. The model alone remembers years and
          powers wrongly, has never heard of cars launched after its cutoff, and has its own idea of “sparsam”. Here is the same query answered four ways.
        </p>
      </header>

      <Section id="compare" title="One query, four answers">
        {r.examples.length ? <QueryCompare r={r} /> : <Empty title="No example queries">Run make report to add them.</Empty>}
      </Section>

      <Section
        id="heldout"
        title={r.heldout ? "On held-out queries, run once" : "On development queries"}
        lead={r.heldout ? `${r.heldout.queries} queries, ${r.heldout.repeats} runs each, at commit ${r.heldout.commit}.` : undefined}
      >
        <SystemTable r={r} set={r.heldout?.systems ?? r.dev.systems} />
      </Section>

      <Section id="production" title="Twelve weeks in production" lead="Winter changes what people search for, a new model goes on sale before the graph knows it, and the LLM behind the search is upgraded.">
        <Timeline r={r} />
      </Section>

      <Section id="sessions" title="What clicks and contacts can label">
        <SessionLabels r={r} />
      </Section>

      <Section id="gate" title="The gate a change has to pass">
        <GateList r={r} />
      </Section>

      <footer className="footer">
        {r.heldout_runs.length ? (
          <p>
            Held-out run log: <code>{r.heldout_runs[0]}</code>
          </p>
        ) : (
          <p>The held-out queries have not been run.</p>
        )}
      </footer>
    </>
  );
}
