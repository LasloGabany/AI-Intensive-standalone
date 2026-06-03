import { describe, expect, it } from "vitest";
import { siteConfigFromEnv } from "./site";

describe("siteConfigFromEnv", () => {
  it("uses PUBLIC_SITE_URL without trailing slash", () => {
    expect(siteConfigFromEnv({ PUBLIC_SITE_URL: "https://example.com/" }).url).toBe(
      "https://example.com"
    );
  });

  it("falls back to localhost for non-production builds", () => {
    expect(siteConfigFromEnv({}).url).toBe("http://localhost:3000");
  });

  it("keeps canonical landing metadata in one place", () => {
    const config = siteConfigFromEnv({ PUBLIC_SITE_URL: "https://example.com" });

    expect(config.title).toContain("Интенсив для психологов");
    expect(config.description).toContain("3 вечера");
  });
});
