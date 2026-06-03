import { hero, value } from "./content";

// Editable subset of the landing, managed via Keystatic (content/settings).
// Heavy nested lists (testimonials, days, experts) stay in content.ts for now.
export type LandingSettings = {
  eventDates: string;
  heroTitleLead: string;
  heroTitleAccent: string;
  heroLead: string;
  heroSub: string;
  heroNote: string;
  ctaText: string;
  ctaSub: string;
  heroPrice: string;
  anchorTotal: string;
  showPains: boolean;
  showMethod: boolean;
  showDays: boolean;
  showFit: boolean;
  showExperts: boolean;
  showTestimonials: boolean;
  showFormat: boolean;
  showValue: boolean;
};

// Defaults trace back to content.ts so the two never drift.
export const DEFAULT_SETTINGS: LandingSettings = {
  eventDates: "11–13 мая",
  heroTitleLead: "Интенсив",
  heroTitleAccent: "для психологов",
  heroLead: hero.lead,
  heroSub: hero.sub,
  heroNote: hero.note,
  ctaText: hero.cta,
  ctaSub: hero.ctaSub,
  heroPrice: "0",
  anchorTotal: value.total,
  showPains: true,
  showMethod: true,
  showDays: true,
  showFit: true,
  showExperts: true,
  showTestimonials: true,
  showFormat: true,
  showValue: true,
};

const TEXT_KEYS = [
  "eventDates",
  "heroTitleLead",
  "heroTitleAccent",
  "heroLead",
  "heroSub",
  "heroNote",
  "ctaText",
  "ctaSub",
  "heroPrice",
  "anchorTotal",
] as const;

const TOGGLE_KEYS = [
  "showPains",
  "showMethod",
  "showDays",
  "showFit",
  "showExperts",
  "showTestimonials",
  "showFormat",
  "showValue",
] as const;

// Pure: merge raw Keystatic data over defaults. Blank text and non-boolean
// toggles fall back to defaults so a misedit never blanks/hides everything.
export function normalizeSettings(raw: unknown): LandingSettings {
  if (!raw || typeof raw !== "object") return { ...DEFAULT_SETTINGS };
  const data = raw as Record<string, unknown>;
  const out: LandingSettings = { ...DEFAULT_SETTINGS };

  for (const key of TEXT_KEYS) {
    const v = data[key];
    if (typeof v === "string" && v.trim() !== "") out[key] = v;
  }
  for (const key of TOGGLE_KEYS) {
    const v = data[key];
    if (typeof v === "boolean") out[key] = v;
  }
  return out;
}

// Async: read the Keystatic singleton at request time. Falls back to defaults
// if the file is missing or unreadable (e.g. fresh deploy).
export async function getLandingSettings(): Promise<LandingSettings> {
  try {
    const { createReader } = await import("@keystatic/core/reader");
    const { default: keystaticConfig } = await import("../keystatic.config");
    const reader = createReader(process.cwd(), keystaticConfig);
    const raw = await reader.singletons.settings.read();
    return normalizeSettings(raw);
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}
