import { describe, expect, it } from "vitest";
import { analyticsConfigFromEnv, hasAnalytics } from "./analytics";

describe("analyticsConfigFromEnv", () => {
  it("returns configured public analytics ids", () => {
    expect(
      analyticsConfigFromEnv({
        NEXT_PUBLIC_GA_ID: "G-12345",
        NEXT_PUBLIC_YM_ID: "987654",
      })
    ).toEqual({ gaId: "G-12345", ymId: "987654" });
  });

  it("normalizes empty ids to null", () => {
    expect(analyticsConfigFromEnv({ NEXT_PUBLIC_GA_ID: " ", NEXT_PUBLIC_YM_ID: "" })).toEqual({
      gaId: null,
      ymId: null,
    });
  });
});

describe("hasAnalytics", () => {
  it("is false when no provider ids are configured", () => {
    expect(hasAnalytics({ gaId: null, ymId: null })).toBe(false);
  });

  it("is true when at least one provider id is configured", () => {
    expect(hasAnalytics({ gaId: "G-12345", ymId: null })).toBe(true);
  });
});
