import { NextRequest, NextResponse } from "next/server";
import { submitLead, safeLogLine, type Lead, type GcConfig } from "@/lib/getcourse";
import { enqueueLeadReplay } from "@/lib/lead-replay-queue";

export const runtime = "nodejs";

// --- minimal in-memory rate limit (per-IP, sliding window) ---
// NOTE: process-local only. Replace with shared store (KV/Redis) before prod scale.
const WINDOW_MS = 60_000;
const MAX_HITS = 5;
const hits = new Map<string, number[]>();

function rateLimited(ip: string): boolean {
  const now = Date.now();
  const arr = (hits.get(ip) || []).filter((t) => now - t < WINDOW_MS);
  arr.push(now);
  hits.set(ip, arr);
  return arr.length > MAX_HITS;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

type LeadInput = {
  name?: unknown;
  email?: unknown;
  phone?: unknown;
  company?: unknown;
};

function gcConfig(): GcConfig | null {
  const account = process.env.GC_ACCOUNT;
  const key = process.env.GC_API_KEY;
  if (!account || !key) return null;
  return { account, key, groupName: process.env.GC_GROUP || undefined };
}

export async function POST(req: NextRequest) {
  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0].trim() ||
    req.headers.get("x-real-ip") ||
    "local";

  if (rateLimited(ip)) {
    return NextResponse.json({ ok: false, error: "rate_limited" }, { status: 429 });
  }

  let body: LeadInput;
  try {
    body = (await req.json()) as LeadInput;
  } catch {
    return NextResponse.json({ ok: false, error: "bad_json" }, { status: 400 });
  }

  // honeypot: real users never fill this — pretend success, do nothing downstream
  if (typeof body.company === "string" && body.company.trim() !== "") {
    return NextResponse.json({ ok: true }, { status: 200 });
  }

  const name = typeof body.name === "string" ? body.name.trim() : "";
  const email = typeof body.email === "string" ? body.email.trim() : "";
  const phone = typeof body.phone === "string" ? body.phone.trim() : undefined;

  if (name.length < 2 || name.length > 80) {
    return NextResponse.json({ ok: false, error: "name" }, { status: 400 });
  }
  if (!EMAIL_RE.test(email) || email.length > 160) {
    return NextResponse.json({ ok: false, error: "email" }, { status: 400 });
  }

  const lead: Lead = { name, email, phone };
  const cfg = gcConfig();

  // No GetCourse creds (dev/preview): accept without downstream call.
  if (!cfg) {
    console.info(`[lead] accepted (no-gc) ip=${maskIp(ip)} ${safeLogLine(lead)}`);
    return NextResponse.json({ ok: true }, { status: 200 });
  }

  const result = await submitLead(lead, cfg, { fetch });

  if (result.ok) {
    console.info(`[lead] gc-ok ip=${maskIp(ip)} ${safeLogLine(lead)}`);
    return NextResponse.json({ ok: true }, { status: 200 });
  }

  // FR-4: GetCourse failed after retries — lead must not be silently lost.
  // If LEAD_REPLAY_DIR is configured, persist PII in a private JSONL queue for manual replay.
  const replayDir = process.env.LEAD_REPLAY_DIR;
  if (replayDir) {
    const queued = await enqueueLeadReplay(lead, {
      dir: replayDir,
      reason: result.error,
    });

    if (queued.ok) {
      console.error(
        `[lead] gc-fail-queued id=${queued.id} ip=${maskIp(ip)} reason=${result.error} ${safeLogLine(lead)}`
      );
      return NextResponse.json({ ok: true, queued: true }, { status: 202 });
    }

    console.error(
      `[lead] gc-fail-queue-error ip=${maskIp(ip)} reason=${result.error} queue_error=${queued.error} ${safeLogLine(lead)}`
    );
  } else {
    console.error(
      `[lead] gc-fail-needs-replay ip=${maskIp(ip)} reason=${result.error} ${safeLogLine(lead)}`
    );
  }

  return NextResponse.json({ ok: false, error: "upstream" }, { status: 502 });
}

function maskIp(ip: string): string {
  const parts = ip.split(".");
  if (parts.length === 4) return `${parts[0]}.${parts[1]}.x.x`;
  return "masked";
}
