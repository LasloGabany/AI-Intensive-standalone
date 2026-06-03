import { appendFile, chmod, mkdir } from "node:fs/promises";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import type { Lead } from "./getcourse";

export type LeadReplayRecord = {
  id: string;
  createdAt: string;
  reason: string;
  lead: Lead;
};

type EnqueueOpts = {
  dir: string;
  reason: string;
  id?: () => string;
  now?: () => Date;
};

export type EnqueueResult =
  | { ok: true; id: string }
  | { ok: false; error: string };

export async function enqueueLeadReplay(
  lead: Lead,
  opts: EnqueueOpts
): Promise<EnqueueResult> {
  const id = opts.id?.() ?? randomUUID();
  const record: LeadReplayRecord = {
    id,
    createdAt: (opts.now?.() ?? new Date()).toISOString(),
    reason: opts.reason,
    lead,
  };

  try {
    await mkdir(opts.dir, { recursive: true, mode: 0o700 });
    await chmod(opts.dir, 0o700);
    await appendFile(
      join(opts.dir, "pending.jsonl"),
      `${JSON.stringify(record)}\n`,
      { encoding: "utf8", mode: 0o600 }
    );
    return { ok: true, id };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : "queue_write_failed",
    };
  }
}
