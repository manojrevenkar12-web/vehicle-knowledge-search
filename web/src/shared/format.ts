export const pct = (x: number, digits = 1) => `${(100 * x).toFixed(digits)}%`;
export const seconds = (ms: number, digits = 2) => `${(ms / 1000).toFixed(digits)} s`;
export const euro = (x: number) => `€${x.toFixed(4)}`;
export const pts = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(100 * x).toFixed(1)} pts`;

const LABEL: Record<string, string> = {
  make: "Make",
  model: "Model",
  year_from: "From year",
  year_to: "To year",
  price_to: "Max price",
  fuel: "Fuel",
  body: "Body",
  power_from_kw: "From kW",
  power_to_kw: "To kW",
  consumption_to: "Max l/100 km",
  seats_from: "Seats from",
  equipment: "Equipment",
  drive: "Drive",
  gearbox: "Gearbox",
  mileage_to: "Max km",
};
export const filterLabel = (k: string) => LABEL[k] ?? k;

export function filterValue(k: string, v: unknown): string {
  if (Array.isArray(v)) return v.join(", ");
  if (typeof v === "number") return k === "price_to" || k === "mileage_to" ? v.toLocaleString("de-DE") : String(v);
  return String(v);
}

export const kindLabel: Record<string, string> = {
  generation: "A generation and a variant",
  concept: "Words, not specs",
  new_model: "A model launched after the LLM's cutoff",
  alias: "A colloquial name",
};
