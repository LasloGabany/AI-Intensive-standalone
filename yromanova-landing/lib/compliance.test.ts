import { describe, expect, it } from "vitest";
import { privacyConfigFromEnv } from "./compliance";

describe("privacyConfigFromEnv", () => {
  it("uses explicit operator and contact settings", () => {
    expect(
      privacyConfigFromEnv({
        PRIVACY_OPERATOR_NAME: "ИП Иванова Анна",
        PRIVACY_CONTACT_EMAIL: "privacy@example.com",
        PUBLIC_SITE_URL: "https://example.com",
      })
    ).toEqual({
      operatorName: "ИП Иванова Анна",
      contactEmail: "privacy@example.com",
      siteUrl: "https://example.com",
    });
  });

  it("falls back to neutral placeholders when env is not configured", () => {
    expect(privacyConfigFromEnv({})).toEqual({
      operatorName: "Организатор интенсива",
      contactEmail: null,
      siteUrl: null,
    });
  });
});
