import { describe, expect, it } from "vitest";
import { checkProdReadiness, formatReport } from "./prod-readiness.mjs";

const completeEnv = {
  NODE_ENV: "production",
  PUBLIC_SITE_URL: "https://example.com",
  GC_ACCOUNT: "clubromanova",
  GC_API_KEY: "super-secret-key",
  PRIVACY_OPERATOR_NAME: "ИП Иванова Анна",
  PRIVACY_CONTACT_EMAIL: "privacy@example.com",
  LEAD_REPLAY_DIR: "/secure/leads/replay",
  MANAGED_LEAD_QUEUE_CONFIRMED: "true",
  DKIM_CONFIRMED: "true",
  DMARC_CONFIRMED: "true",
  DOMAIN_RENEWAL_CONFIRMED: "true",
};

describe("checkProdReadiness", () => {
  it("passes when required production settings are present", () => {
    const report = checkProdReadiness(completeEnv);

    expect(report.ok).toBe(true);
    expect(report.failures).toEqual([]);
  });

  it("fails when compliance and infra settings are missing", () => {
    const report = checkProdReadiness({ NODE_ENV: "production" });

    expect(report.ok).toBe(false);
    expect(report.failures).toContain("GC_ACCOUNT is required for production lead delivery.");
    expect(report.failures).toContain("PRIVACY_CONTACT_EMAIL is required for privacy requests.");
    expect(report.failures).toContain("DKIM_CONFIRMED=true is required before launch.");
  });

  it("warns when replay queue is file-backed instead of managed", () => {
    const report = checkProdReadiness({
      ...completeEnv,
      MANAGED_LEAD_QUEUE_CONFIRMED: "false",
    });

    expect(report.ok).toBe(false);
    expect(report.failures).toContain("MANAGED_LEAD_QUEUE_CONFIRMED=true is required for multi-instance/serverless production.");
  });

  it("does not print secret values in the report", () => {
    const text = formatReport(checkProdReadiness(completeEnv));

    expect(text).not.toContain("super-secret-key");
    expect(text).toContain("GC_API_KEY: set");
  });
});


describe("Keystatic admin readiness", () => {
  it("passes with production admin disabled by default", () => {
    const report = checkProdReadiness(completeEnv);

    expect(report.ok).toBe(true);
    expect(report.checks).toContainEqual({ name: "KEYSTATIC_ADMIN", status: "disabled" });
  });

  it("fails when production admin is enabled without credentials", () => {
    const report = checkProdReadiness({ ...completeEnv, KEYSTATIC_ADMIN_ENABLED: "true" });

    expect(report.ok).toBe(false);
    expect(report.failures).toContain(
      "KEYSTATIC_ADMIN_USER and KEYSTATIC_ADMIN_PASSWORD are required when KEYSTATIC_ADMIN_ENABLED=true."
    );
    expect(report.checks).toContainEqual({ name: "KEYSTATIC_ADMIN", status: "misconfigured" });
  });

  it("passes when production admin is enabled with credentials", () => {
    const report = checkProdReadiness({
      ...completeEnv,
      KEYSTATIC_ADMIN_ENABLED: "true",
      KEYSTATIC_ADMIN_USER: "editor",
      KEYSTATIC_ADMIN_PASSWORD: "super-secret-admin-password",
    });

    expect(report.ok).toBe(true);
    expect(report.checks).toContainEqual({ name: "KEYSTATIC_ADMIN", status: "protected" });
    expect(formatReport(report)).not.toContain("super-secret-admin-password");
  });
});
