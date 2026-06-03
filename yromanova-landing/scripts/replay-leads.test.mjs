import { describe, expect, it } from "vitest";
import {
  applyReplayResults,
  buildGetCourseBody,
  moveRecordById,
  parseJsonl,
  publicSummary,
} from "./replay-leads.mjs";

const record = {
  id: "lead-1",
  createdAt: "2026-06-02T18:00:00.000Z",
  reason: "network_error",
  lead: {
    name: "Анна Тестова",
    email: "anna@example.com",
    phone: "+79990001122",
  },
};

describe("parseJsonl", () => {
  it("parses non-empty JSONL rows", () => {
    expect(parseJsonl(`${JSON.stringify(record)}

`)).toEqual([record]);
  });
});

describe("publicSummary", () => {
  it("does not expose raw PII", () => {
    const summary = JSON.stringify(publicSummary(record));

    expect(summary).toContain("lead-1");
    expect(summary).toContain("example.com");
    expect(summary).not.toContain("Анна");
    expect(summary).not.toContain("anna@example.com");
    expect(summary).not.toContain("+79990001122");
  });
});

describe("buildGetCourseBody", () => {
  it("builds the import API body without leaking values into query params", () => {
    const body = buildGetCourseBody(record.lead, {
      key: "SECRET123",
      groupName: "Интенсив",
    });

    expect(body.get("action")).toBe("add");
    expect(body.get("key")).toBe("SECRET123");
    expect(body.get("params")).toBeTruthy();
    expect(String(body)).not.toContain("anna@example.com");
  });
});

describe("applyReplayResults", () => {
  it("removes successful records from pending and appends processed records", () => {
    const second = { ...record, id: "lead-2" };
    const result = applyReplayResults([record, second], [
      { id: "lead-1", ok: true, gcId: 42 },
      { id: "lead-2", ok: false, error: "http_500" },
    ], "2026-06-02T18:10:00.000Z");

    expect(result.pending.map((r) => r.id)).toEqual(["lead-2"]);
    expect(result.processed).toEqual([
      {
        ...record,
        processedAt: "2026-06-02T18:10:00.000Z",
        gcId: 42,
      },
    ]);
    expect(result.failed[0]).toMatchObject({ id: "lead-2", error: "http_500" });
  });
});

describe("moveRecordById", () => {
  it("moves a pending record into a manual destination", () => {
    const result = moveRecordById([record], "lead-1", "processed", "manual-ok", "2026-06-02T18:20:00.000Z");

    expect(result.pending).toEqual([]);
    expect(result.moved).toMatchObject({
      id: "lead-1",
      status: "processed",
      note: "manual-ok",
      processedAt: "2026-06-02T18:20:00.000Z",
    });
  });
});
