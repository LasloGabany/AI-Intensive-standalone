import { describe, it, expect } from "vitest";
import { normalizeSettings, DEFAULT_SETTINGS } from "./landing-settings";

describe("normalizeSettings", () => {
  it("returns defaults for null / non-object input", () => {
    expect(normalizeSettings(null)).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings("nope")).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings(undefined)).toEqual(DEFAULT_SETTINGS);
  });

  it("overrides only provided text fields, keeps defaults for the rest", () => {
    const out = normalizeSettings({ eventDates: "1–3 июня", ctaText: "Записаться" });
    expect(out.eventDates).toBe("1–3 июня");
    expect(out.ctaText).toBe("Записаться");
    expect(out.heroLead).toBe(DEFAULT_SETTINGS.heroLead);
  });

  it("ignores empty / blank text so the page never goes blank", () => {
    const out = normalizeSettings({ eventDates: "", heroTitleLead: "   " });
    expect(out.eventDates).toBe(DEFAULT_SETTINGS.eventDates);
    expect(out.heroTitleLead).toBe(DEFAULT_SETTINGS.heroTitleLead);
  });

  it("respects boolean toggles, including false", () => {
    const out = normalizeSettings({ showPains: false, showValue: false });
    expect(out.showPains).toBe(false);
    expect(out.showValue).toBe(false);
    expect(out.showDays).toBe(true); // untouched default
  });

  it("ignores non-boolean toggle values, falling back to default", () => {
    const out = normalizeSettings({ showPains: "yes" });
    expect(out.showPains).toBe(true);
  });
});
