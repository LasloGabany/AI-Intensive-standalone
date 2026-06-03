import { describe, expect, it } from "vitest";
import { adminAccessDecision, isAdminPath } from "./admin-access";

const prodEnv = {
  KEYSTATIC_ADMIN_ENABLED: "true",
  KEYSTATIC_ADMIN_USER: "editor",
  KEYSTATIC_ADMIN_PASSWORD: "secret",
};

function basic(user: string, password: string) {
  return `Basic ${Buffer.from(`${user}:${password}`).toString("base64")}`;
}

describe("isAdminPath", () => {
  it("matches Keystatic UI and API routes only", () => {
    expect(isAdminPath("/keystatic")).toBe(true);
    expect(isAdminPath("/keystatic/collections/settings")).toBe(true);
    expect(isAdminPath("/api/keystatic/settings")).toBe(true);
    expect(isAdminPath("/")).toBe(false);
    expect(isAdminPath("/api/lead")).toBe(false);
  });
});

describe("adminAccessDecision", () => {
  it("allows local development admin without credentials", () => {
    expect(
      adminAccessDecision({ pathname: "/keystatic", authorization: null, nodeEnv: "development", env: {} })
    ).toBe("allow");
  });

  it("disables production admin unless explicitly enabled", () => {
    expect(
      adminAccessDecision({ pathname: "/keystatic", authorization: null, nodeEnv: "production", env: {} })
    ).toBe("disabled");
  });

  it("disables production admin when enabled without complete credentials", () => {
    expect(
      adminAccessDecision({
        pathname: "/api/keystatic/settings",
        authorization: null,
        nodeEnv: "production",
        env: { KEYSTATIC_ADMIN_ENABLED: "true", KEYSTATIC_ADMIN_USER: "editor" },
      })
    ).toBe("disabled");
  });

  it("challenges production admin with missing or wrong credentials", () => {
    expect(
      adminAccessDecision({ pathname: "/keystatic", authorization: null, nodeEnv: "production", env: prodEnv })
    ).toBe("challenge");
    expect(
      adminAccessDecision({
        pathname: "/keystatic",
        authorization: basic("editor", "wrong"),
        nodeEnv: "production",
        env: prodEnv,
      })
    ).toBe("challenge");
  });

  it("allows production admin with matching credentials", () => {
    expect(
      adminAccessDecision({
        pathname: "/keystatic",
        authorization: basic("editor", "secret"),
        nodeEnv: "production",
        env: prodEnv,
      })
    ).toBe("allow");
  });
});
