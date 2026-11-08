export type Interval = [number, number, number];
export type SystemName = "llm_only" | "vector_rag" | "graph" | "graph_agent";
export const SYSTEMS: SystemName[] = ["llm_only", "vector_rag", "graph", "graph_agent"];

export interface Summary {
  exact: Interval;
  result_jaccard: number;
  filter_f1: number;
  zero_results: number;
  by_kind: Record<string, number>;
  p50_ms: number;
  p95_ms: number;
  cost_eur: number;
  docs: number;
}

export interface Week {
  week: number;
  zero_results: number;
  unknown_entities: number;
  hallucinations: number;
  psi: number;
  exact_true: number;
  exact_labelled: Interval;
  alerts: string[];
}

export interface GateDecision {
  system: string;
  exact: Interval;
  budget: { p95_ms: number; cost_eur: number };
  blocked: boolean;
  reasons: string[];
}

export type Filters = Record<string, unknown>;

export interface Example {
  id: string;
  kind: string;
  text: string;
  gold: Filters;
  gold_results: number;
  systems: Record<SystemName, { filters: Filters; exact: boolean; results: number; wrong: string[]; extra: string[] }>;
}

export interface Results {
  dev: {
    queries: number;
    systems: Record<SystemName, Summary>;
    paired: Record<string, Interval>;
    sessions: {
      queries: number;
      queries_with_contacts: number;
      label_precision: number;
      gold_share_labelled: number;
      systems: Record<SystemName, { contact_recall: number; exact_true: number }>;
    };
    production: Partial<Record<SystemName, Week[]>>;
    cases: { count: number; why: Record<string, number>; pass: Record<string, number> };
    gate: Record<string, GateDecision>;
  };
  heldout?: { queries: number; repeats: number; commit: string; systems: Record<SystemName, Summary> };
  heldout_runs: string[];
  targets: { p95_latency_ms: number; cost_per_query_eur: number };
  names: Record<SystemName, string>;
  examples: Example[];
  config: {
    repeats: number;
    production: { season_week: number; launch_week: number; kg_update_lag_weeks: number; llm_update_week: number; labelled_per_week: number };
    gate_max_drop: number;
  };
}
