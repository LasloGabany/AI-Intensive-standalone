import { mkdtemp, readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";
import { describe, expect, it } from "vitest";
import { enqueueLeadReplay } from "./lead-replay-queue";
import type { Lead } from "./getcourse";

const lead: Lead = {
  name: "Анна Тестова",
  email: "anna@example.com",
  phone: "+79990001122",
};

describe("enqueueLeadReplay", () => {
  it("appends failed leads to a durable JSONL queue", async () => {
    const dir = await mkdtemp(join(tmpdir(), "lead-replay-"));

    const result = await enqueueLeadReplay(lead, {
      dir,
      reason: "http_502",
      id: () => "replay-1",
      now: () => new Date("2026-06-02T17:30:00.000Z"),
    });

    expect(result).toEqual({ ok: true, id: "replay-1" });
    const raw = await readFile(join(dir, "pending.jsonl"), "utf8");
    const rows = raw.trim().split("\n").map((line) => JSON.parse(line));
    expect(rows).toHaveLength(1);
    expect(rows[0]).toMatchObject({
      id: "replay-1",
      createdAt: "2026-06-02T17:30:00.000Z",
      reason: "http_502",
      lead,
    });
  });

  it("keeps the queue directory private to the current user", async () => {
    const dir = await mkdtemp(join(tmpdir(), "lead-replay-"));

    await enqueueLeadReplay(lead, {
      dir,
      reason: "network_error",
      id: () => "replay-2",
      now: () => new Date("2026-06-02T17:30:00.000Z"),
    });

    const mode = (await stat(dir)).mode & 0o777;
    expect(mode & 0o077).toBe(0);
  });
});
