import { describe, it, expect, vi } from "vitest";
import { buildParams, submitLead, safeLogLine, type Lead, type GcConfig } from "./getcourse";

const lead: Lead = { name: "Анна Тестова", email: "anna@example.com", phone: "+79990001122" };
const cfg: GcConfig = { account: "clubromanova", key: "SECRET123", groupName: "Интенсив" };

function decode(b64: string) {
  return JSON.parse(Buffer.from(b64, "base64").toString("utf8"));
}

describe("buildParams", () => {
  it("encodes the lead into base64 JSON with split name and group", () => {
    const params = buildParams(lead, cfg);
    const obj = decode(params);
    expect(obj.user.email).toBe("anna@example.com");
    expect(obj.user.first_name).toBe("Анна");
    expect(obj.user.last_name).toBe("Тестова");
    expect(obj.user.phone).toBe("+79990001122");
    expect(obj.user.group_name).toContain("Интенсив");
    expect(obj.system.refresh_if_exists).toBe(1);
  });

  it("passes utm tags into the session block", () => {
    const obj = decode(buildParams({ ...lead, utm: { utm_source: "vk" } }, cfg));
    expect(obj.session.utm_source).toBe("vk");
  });
});

describe("submitLead", () => {
  const ok = () =>
    new Response(JSON.stringify({ status: "success", id: 42 }), { status: 200 });
  const fail5xx = () => new Response("upstream", { status: 502 });
  const badStatus = () =>
    new Response(JSON.stringify({ status: "error", error_message: "bad" }), { status: 200 });

  it("POSTs action=add with key and params, returns the user id", async () => {
    const fetchMock = vi.fn(async (_url: string, _init: RequestInit) => ok());
    const res = await submitLead(lead, cfg, { fetch: fetchMock as unknown as typeof fetch });

    expect(res).toEqual({ ok: true, id: 42 });
    const [url, init] = fetchMock.mock.calls[0];
    const initBody = String(init.body);
    expect(url).toBe("https://clubromanova.getcourse.ru/pl/api/users");
    expect(init.method).toBe("POST");
    expect(initBody).toContain("action=add");
    expect(initBody).toContain("key=SECRET123");
    expect(initBody).toContain("params=");
  });

  it("retries on 5xx and succeeds on a later attempt", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(fail5xx())
      .mockResolvedValueOnce(fail5xx())
      .mockResolvedValueOnce(ok());
    const res = await submitLead(lead, cfg, {
      fetch: fetchMock as unknown as typeof fetch,
      retries: 3,
      retryDelayMs: 0,
    });
    expect(res).toEqual({ ok: true, id: 42 });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("returns not-ok after exhausting retries on persistent 5xx (lead not lost)", async () => {
    const fetchMock = vi.fn(async () => fail5xx());
    const res = await submitLead(lead, cfg, {
      fetch: fetchMock as unknown as typeof fetch,
      retries: 3,
      retryDelayMs: 0,
    });
    expect(res.ok).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("does NOT retry on a non-success business response (permanent error)", async () => {
    const fetchMock = vi.fn(async () => badStatus());
    const res = await submitLead(lead, cfg, {
      fetch: fetchMock as unknown as typeof fetch,
      retries: 3,
      retryDelayMs: 0,
    });
    expect(res.ok).toBe(false);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("safeLogLine", () => {
  it("never includes raw email or phone (152-ФЗ: no PII in logs)", () => {
    const line = safeLogLine(lead);
    expect(line).not.toContain("anna@example.com");
    expect(line).not.toContain("+79990001122");
    expect(line).not.toContain("Анна");
  });
});
