// The visual system: a search console. Cool white, graphite ink, and one colour per way of answering a query, so a
// system keeps its colour from the query comparison to the production timeline.

export const color = {
  page: "#F6F7F9",
  sheet: "#FFFFFF",
  ink: "#141A24",
  muted: "#5A6474",
  faint: "#9AA3B1",
  rule: "#DCE0E6",
  track: "#E9ECF0",
  right: "#1F7A4D",
  rightWash: "#E2F2E9",
  wrong: "#C0392B",
  wrongWash: "#F9E3E0",
  extra: "#9A6A08",
  extraWash: "#F6EDD8",
  event: "#7A5AF0",
} as const;

export const systemColor: Record<string, string> = {
  llm_only: "#8A93A3",
  vector_rag: "#B4517E",
  graph: "#3B6FD9",
  graph_agent: "#0E7C66",
};

export const font = { ui: '"Figtree", "Segoe UI", system-ui, sans-serif' } as const;
export const size = { tick: 12, small: 14, body: 16, lead: 19, title: 26, display: 42 } as const;
export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48, 8: 72 } as const;
export const radius = { control: 6, panel: 10, chip: 999 } as const;
export const layout = { contentMax: 1140, measure: 68 } as const;

/** The production timeline: plot size, the accuracy axis floor, marker sizes. */
export const timeline = { width: 760, height: 260, left: 44, right: 16, top: 40, bottom: 34, floor: 0.8, dot: 3.5 } as const;
/** Chips settle in when the system changes. */
export const chips = { settle: 0.22, stagger: 0.03 } as const;

export function applyTokens(root: HTMLElement = document.documentElement): void {
  const set = (k: string, v: string | number) => root.style.setProperty(k, typeof v === "number" ? `${v}px` : v);
  Object.entries(color).forEach(([k, v]) => set(`--c-${k}`, v));
  Object.entries(size).forEach(([k, v]) => set(`--fs-${k}`, v));
  Object.entries(space).forEach(([k, v]) => set(`--sp-${k}`, v));
  Object.entries(radius).forEach(([k, v]) => set(`--r-${k}`, v));
  set("--font-ui", font.ui);
  set("--content-max", layout.contentMax);
  set("--measure", `${layout.measure}ch`);
}
