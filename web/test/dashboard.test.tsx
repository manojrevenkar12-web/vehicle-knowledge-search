import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "../src/app/App";
import type { Results, Summary, Week } from "../src/shared/api/types";

const sum = (exact: number, p95: number, cost: number): Summary => ({
  exact: [exact, exact - 0.03, exact + 0.02], result_jaccard: 0.99, filter_f1: 0.99, zero_results: 0.08,
  by_kind: { concept: exact - 0.1, generation: exact }, p50_ms: 1500, p95_ms: p95, cost_eur: cost, docs: 0,
});
const week = (w: number, exact: number, alerts: string[] = []): Week => ({
  week: w, zero_results: 0.1, unknown_entities: 0, hallucinations: 0, psi: 0.02, exact_true: exact, exact_labelled: [exact, exact - 0.1, 1], alerts,
});
const systems = { llm_only: sum(0.63, 1800, 0.0027), vector_rag: sum(0.96, 1850, 0.0048), graph: sum(0.97, 1850, 0.0031), graph_agent: sum(0.97, 1980, 0.0031) };
const results: Results = {
  dev: {
    queries: 320, systems, paired: {},
    sessions: { queries: 320, queries_with_contacts: 126, label_precision: 0.99, gold_share_labelled: 0.036, systems: {
      llm_only: { contact_recall: 0.82, exact_true: 0.63 }, vector_rag: { contact_recall: 1, exact_true: 0.96 }, graph: { contact_recall: 1, exact_true: 0.97 }, graph_agent: { contact_recall: 1, exact_true: 0.97 } } },
    production: { graph: [week(1, 0.95), week(2, 0.86)], graph_agent: [week(1, 0.95), week(2, 0.95, ["hallucinations"])] },
    cases: { count: 149, why: {}, pass: { graph_agent: 140, graph: 100 } },
    gate: {
      "drop the validator": { system: "graph", exact: [0, 0, 0], budget: { p95_ms: 1850, cost_eur: 0.0031 }, blocked: true, reasons: ["fails 30 production case(s)"] },
      "same system, run again (A/A)": { system: "graph_agent", exact: [0.006, -0.006, 0.02], budget: { p95_ms: 1980, cost_eur: 0.0031 }, blocked: false, reasons: [] },
    },
  },
  heldout: { queries: 160, repeats: 3, commit: "abc1234", systems },
  heldout_runs: ["2026-11-08 commit=abc1234"],
  targets: { p95_latency_ms: 2500, cost_per_query_eur: 0.004 },
  names: { llm_only: "Model alone", vector_rag: "Vector RAG", graph: "Knowledge graph", graph_agent: "Graph + validator" },
  examples: [{
    id: "DEV-1", kind: "new_model", text: "Skoda Elroq bis 40.000 €", gold: { make: "Skoda", model: "Elroq", price_to: 40000 }, gold_results: 12,
    systems: {
      llm_only: { filters: { make: "Skoda", model: "Kodiaq", price_to: 40000 }, exact: false, results: 80, wrong: ["model"], extra: [] },
      vector_rag: { filters: { make: "Skoda", model: "Elroq", price_to: 40000 }, exact: true, results: 12, wrong: [], extra: [] },
      graph: { filters: { make: "Skoda", model: "Elroq", price_to: 40000 }, exact: true, results: 12, wrong: [], extra: [] },
      graph_agent: { filters: { make: "Skoda", model: "Elroq", price_to: 40000 }, exact: true, results: 12, wrong: [], extra: [] },
    },
  }],
  config: { repeats: 3, production: { season_week: 6, launch_week: 7, kg_update_lag_weeks: 2, llm_update_week: 10, labelled_per_week: 40 }, gate_max_drop: 0.02 },
};

function serve(map: Record<string, unknown>, fail = new Set<string>()) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (fail.has(url)) return new Response("no", { status: 500 });
    if (!(url in map)) return new Response("no", { status: 404 });
    return new Response(JSON.stringify(map[url]), { status: 200 });
  }));
}
afterEach(() => vi.unstubAllGlobals());

describe("dashboard", () => {
  it("loads, then states the held-out result", async () => {
    serve({ "/data/results.json": results });
    render(<App />);
    expect(screen.getByRole("status", { name: "Loading results" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 1 })).toHaveTextContent("right 97% of the time on queries nobody looked at. The model alone manages 63%.");
  });

  it("shows a substituted model as wrong, and right once the system changes", async () => {
    serve({ "/data/results.json": results });
    render(<App />);
    expect(await screen.findByText("Kodiaq")).toBeInTheDocument();
    expect(screen.getByText("meant Elroq")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Knowledge graph" }));
    expect(await screen.findByText(/Every filter as meant: 12 listings/)).toBeInTheDocument();
  });

  it("lists alerts and blocked changes", async () => {
    serve({ "/data/results.json": results });
    render(<App />);
    await screen.findByRole("heading", { level: 1 });
    expect(screen.getByText("hallucinations")).toBeInTheDocument();
    expect(screen.getByText("Blocked")).toBeInTheDocument();
  });

  it("explains a failed load and loads again", async () => {
    const fail = new Set(["/data/results.json"]);
    serve({ "/data/results.json": results }, fail);
    render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("could not be loaded");
    fail.clear();
    await userEvent.click(screen.getByRole("button", { name: "Load again" }));
    expect(await screen.findByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("says so when there are no examples", async () => {
    serve({ "/data/results.json": { ...results, examples: [], heldout: undefined, heldout_runs: [] } });
    render(<App />);
    expect(await screen.findByText("No example queries")).toBeInTheDocument();
    expect(screen.getByText("The held-out queries have not been run.")).toBeInTheDocument();
  });
});
