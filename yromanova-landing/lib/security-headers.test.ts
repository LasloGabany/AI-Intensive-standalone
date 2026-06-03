import { describe, it, expect } from "vitest";
import { buildCsp, securityHeaders } from "./security-headers";

const NONCE = "abc123";

describe("buildCsp", () => {
  it("locks default-src to self and nonces scripts with strict-dynamic", () => {
    const csp = buildCsp(NONCE, { dev: false });
    expect(csp).toContain("default-src 'self'");
    expect(csp).toContain(`'nonce-${NONCE}'`);
    expect(csp).toContain("'strict-dynamic'");
    expect(csp).toContain("object-src 'none'");
    expect(csp).toContain("frame-ancestors 'none'");
    expect(csp).toContain("base-uri 'self'");
    expect(csp).toContain("form-action 'self'");
  });

  it("never allows unsafe-inline or unsafe-eval in script-src in production", () => {
    const csp = buildCsp(NONCE, { dev: false });
    const scriptSrc = csp.split(";").find((d) => d.trim().startsWith("script-src"))!;
    expect(scriptSrc).not.toContain("unsafe-inline");
    expect(scriptSrc).not.toContain("unsafe-eval");
  });

  it("allows unsafe-eval in script-src only in dev (HMR), and upgrade-insecure only in prod", () => {
    const dev = buildCsp(NONCE, { dev: true });
    const prod = buildCsp(NONCE, { dev: false });
    const devScript = dev.split(";").find((d) => d.trim().startsWith("script-src"))!;
    expect(devScript).toContain("'unsafe-eval'");
    expect(dev).not.toContain("upgrade-insecure-requests");
    expect(prod).toContain("upgrade-insecure-requests");
  });

  it("permits inline styles (documented tradeoff for next/font + style attrs)", () => {
    const styleSrc = buildCsp(NONCE, { dev: false })
      .split(";")
      .find((d) => d.trim().startsWith("style-src"))!;
    expect(styleSrc).toContain("'unsafe-inline'");
  });

  it("permits analytics endpoints for consented browser beacons", () => {
    const csp = buildCsp(NONCE, { dev: false });
    const connectSrc = csp.split(";").find((d) => d.trim().startsWith("connect-src"))!;
    expect(connectSrc).toContain("https://www.google-analytics.com");
    expect(connectSrc).toContain("https://mc.yandex.ru");
  });
});

describe("securityHeaders", () => {
  it("returns the full hardened header set", () => {
    const h = securityHeaders(NONCE, { dev: false });
    expect(h["Strict-Transport-Security"]).toBe(
      "max-age=31536000; includeSubDomains; preload"
    );
    expect(h["X-Content-Type-Options"]).toBe("nosniff");
    expect(h["X-Frame-Options"]).toBe("DENY");
    expect(h["Referrer-Policy"]).toBe("strict-origin-when-cross-origin");
    expect(h["Permissions-Policy"]).toBe("camera=(), microphone=(), geolocation=()");
    expect(h["Content-Security-Policy"]).toContain(`'nonce-${NONCE}'`);
  });
});
