// GetCourse import-API proxy core (server-only).
// Contract: POST https://{account}.getcourse.ru/pl/api/users
//   body: action=add&key={secret}&params={base64(json)}
//   success: { status: "success", id }
// Stateless pass-through — no PII persisted, no raw PII logged (152-ФЗ).

export type Lead = {
  name: string;
  email: string;
  phone?: string;
  utm?: Record<string, string>;
};

export type GcConfig = {
  account: string;
  key: string;
  groupName?: string;
  refreshIfExists?: boolean;
};

export type GcDeps = {
  fetch: typeof fetch;
  retries?: number;
  retryDelayMs?: number;
};

export type GcResult = { ok: true; id: number } | { ok: false; error: string };

function splitName(name: string): { first: string; last: string } {
  const parts = name.trim().split(/\s+/);
  return { first: parts[0] ?? "", last: parts.slice(1).join(" ") };
}

export function buildParams(lead: Lead, cfg: GcConfig): string {
  const { first, last } = splitName(lead.name);
  const payload = {
    user: {
      email: lead.email,
      phone: lead.phone ?? "",
      first_name: first,
      last_name: last,
      group_name: cfg.groupName ? [cfg.groupName] : [],
    },
    system: {
      refresh_if_exists: cfg.refreshIfExists === false ? 0 : 1,
    },
    session: { ...(lead.utm ?? {}) },
  };
  return Buffer.from(JSON.stringify(payload), "utf8").toString("base64");
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function submitLead(
  lead: Lead,
  cfg: GcConfig,
  deps: GcDeps
): Promise<GcResult> {
  const retries = deps.retries ?? 3;
  const retryDelayMs = deps.retryDelayMs ?? 300;
  const url = `https://${cfg.account}.getcourse.ru/pl/api/users`;
  const body = new URLSearchParams({
    action: "add",
    key: cfg.key,
    params: buildParams(lead, cfg),
  }).toString();

  let lastError = "upstream_unavailable";

  for (let attempt = 1; attempt <= retries; attempt++) {
    try {
      const res = await deps.fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });

      // 5xx → transient, retry
      if (res.status >= 500) {
        lastError = `http_${res.status}`;
        if (attempt < retries) await sleep(retryDelayMs);
        continue;
      }

      // 4xx → permanent, no retry
      if (!res.ok) {
        return { ok: false, error: `http_${res.status}` };
      }

      const data = (await res.json().catch(() => null)) as
        | { status?: string; id?: number }
        | null;

      if (data?.status === "success" && typeof data.id === "number") {
        return { ok: true, id: data.id };
      }
      // 200 but business error → permanent, no retry
      return { ok: false, error: "gc_rejected" };
    } catch {
      // network error → transient, retry
      lastError = "network_error";
      if (attempt < retries) await sleep(retryDelayMs);
    }
  }

  return { ok: false, error: lastError };
}

// Log line guaranteed to contain zero PII — counts/flags only.
export function safeLogLine(lead: Lead): string {
  return `lead name_len=${lead.name.length} has_phone=${Boolean(lead.phone)}`;
}
