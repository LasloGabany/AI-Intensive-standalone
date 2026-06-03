#!/usr/bin/env node
import { appendFile, chmod, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const PENDING = 'pending.jsonl';
const PROCESSED = 'processed.jsonl';
const FAILED = 'failed.jsonl';

export function parseJsonl(text) {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      try {
        return JSON.parse(line);
      } catch (err) {
        throw new Error(`Invalid JSONL at line ${index + 1}: ${err instanceof Error ? err.message : 'parse_error'}`);
      }
    });
}

export function publicSummary(record) {
  const email = String(record.lead?.email || '');
  const domain = email.includes('@') ? email.split('@').pop() : 'unknown';
  return {
    id: record.id,
    createdAt: record.createdAt,
    reason: record.reason,
    nameLen: String(record.lead?.name || '').length,
    emailDomain: domain,
    hasPhone: Boolean(record.lead?.phone),
  };
}

function splitName(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  return { first: parts[0] || '', last: parts.slice(1).join(' ') };
}

export function buildGetCourseBody(lead, cfg) {
  const { first, last } = splitName(lead.name);
  const payload = {
    user: {
      email: lead.email,
      phone: lead.phone || '',
      first_name: first,
      last_name: last,
      group_name: cfg.groupName ? [cfg.groupName] : [],
    },
    system: { refresh_if_exists: 1 },
    session: { ...(lead.utm || {}) },
  };
  return new URLSearchParams({
    action: 'add',
    key: cfg.key,
    params: Buffer.from(JSON.stringify(payload), 'utf8').toString('base64'),
  });
}

export function applyReplayResults(records, results, nowIso) {
  const byId = new Map(results.map((result) => [result.id, result]));
  const pending = [];
  const processed = [];
  const failed = [];

  for (const record of records) {
    const result = byId.get(record.id);
    if (!result) {
      pending.push(record);
      continue;
    }
    if (result.ok) {
      processed.push({ ...record, processedAt: nowIso, gcId: result.gcId });
    } else {
      pending.push(record);
      failed.push({ ...record, failedAt: nowIso, error: result.error });
    }
  }

  return { pending, processed, failed };
}

export function moveRecordById(records, id, status, note, nowIso) {
  const pending = [];
  let moved = null;

  for (const record of records) {
    if (record.id !== id) {
      pending.push(record);
      continue;
    }
    moved = {
      ...record,
      status,
      note: note || 'manual',
      ...(status === 'processed' ? { processedAt: nowIso } : { failedAt: nowIso }),
    };
  }

  if (!moved) throw new Error(`No pending lead with id=${id}`);
  return { pending, moved };
}

async function readRecords(dir) {
  const path = join(dir, PENDING);
  if (!existsSync(path)) return [];
  return parseJsonl(await readFile(path, 'utf8'));
}

function toJsonl(records) {
  return records.map((record) => JSON.stringify(record)).join('\n') + (records.length ? '\n' : '');
}

async function atomicWrite(path, content) {
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  const tmp = `${path}.${process.pid}.tmp`;
  await writeFile(tmp, content, { encoding: 'utf8', mode: 0o600 });
  await rename(tmp, path);
  await chmod(path, 0o600);
}

async function appendRecords(path, records) {
  if (!records.length) return;
  await mkdir(dirname(path), { recursive: true, mode: 0o700 });
  await appendFile(path, toJsonl(records), { encoding: 'utf8', mode: 0o600 });
  await chmod(path, 0o600);
}

async function submitToGetCourse(record, cfg) {
  const url = `https://${cfg.account}.getcourse.ru/pl/api/users`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: buildGetCourseBody(record.lead, cfg).toString(),
    });
    if (!res.ok) return { id: record.id, ok: false, error: `http_${res.status}` };
    const data = await res.json().catch(() => null);
    if (data?.status === 'success' && typeof data.id === 'number') {
      return { id: record.id, ok: true, gcId: data.id };
    }
    return { id: record.id, ok: false, error: 'gc_rejected' };
  } catch {
    return { id: record.id, ok: false, error: 'network_error' };
  }
}

function parseArgs(argv) {
  const opts = { command: 'list', limit: Infinity, dryRun: false, note: '' };
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--dir') opts.dir = argv[++i];
    else if (arg === '--limit') opts.limit = Number(argv[++i]);
    else if (arg === '--replay') opts.command = 'replay';
    else if (arg === '--dry-run') opts.dryRun = true;
    else if (arg === '--list') opts.command = 'list';
    else if (arg === '--mark-processed') { opts.command = 'mark-processed'; opts.id = argv[++i]; }
    else if (arg === '--mark-failed') { opts.command = 'mark-failed'; opts.id = argv[++i]; }
    else if (arg === '--note') opts.note = argv[++i];
    else if (arg === '--help' || arg === '-h') opts.command = 'help';
    else throw new Error(`Unknown argument: ${arg}`);
  }
  opts.dir ||= process.env.LEAD_REPLAY_DIR;
  return opts;
}

function printHelp() {
  console.log(`Usage:
  npm run replay:leads -- --list --dir <queue-dir>
  npm run replay:leads -- --replay --limit 10 --dir <queue-dir>
  npm run replay:leads -- --dry-run --replay --dir <queue-dir>
  npm run replay:leads -- --mark-processed <id> --note "handled" --dir <queue-dir>
  npm run replay:leads -- --mark-failed <id> --note "duplicate" --dir <queue-dir>

Env for replay:
  LEAD_REPLAY_DIR, GC_ACCOUNT, GC_API_KEY, optional GC_GROUP
`);
}

async function main(argv) {
  const opts = parseArgs(argv);
  if (opts.command === 'help') return printHelp();
  if (!opts.dir) throw new Error('Missing queue dir. Set LEAD_REPLAY_DIR or pass --dir <dir>.');

  const records = await readRecords(opts.dir);
  if (opts.command === 'list') {
    console.log(JSON.stringify(records.map(publicSummary), null, 2));
    return;
  }

  const nowIso = new Date().toISOString();
  const pendingPath = join(opts.dir, PENDING);

  if (opts.command === 'mark-processed' || opts.command === 'mark-failed') {
    if (!opts.id) throw new Error('Missing id.');
    const status = opts.command === 'mark-processed' ? 'processed' : 'failed';
    const { pending, moved } = moveRecordById(records, opts.id, status, opts.note, nowIso);
    await atomicWrite(pendingPath, toJsonl(pending));
    await appendRecords(join(opts.dir, status === 'processed' ? PROCESSED : FAILED), [moved]);
    console.log(JSON.stringify({ moved: publicSummary(moved), pending: pending.length }, null, 2));
    return;
  }

  if (opts.command === 'replay') {
    const selected = records.slice(0, opts.limit);
    if (opts.dryRun) {
      console.log(JSON.stringify({ dryRun: true, selected: selected.map(publicSummary) }, null, 2));
      return;
    }
    const cfg = {
      account: process.env.GC_ACCOUNT,
      key: process.env.GC_API_KEY,
      groupName: process.env.GC_GROUP || undefined,
    };
    if (!cfg.account || !cfg.key) throw new Error('Missing GC_ACCOUNT or GC_API_KEY.');

    const results = [];
    for (const record of selected) results.push(await submitToGetCourse(record, cfg));
    const { pending, processed, failed } = applyReplayResults(records, results, nowIso);
    await atomicWrite(pendingPath, toJsonl(pending));
    await appendRecords(join(opts.dir, PROCESSED), processed);
    await appendRecords(join(opts.dir, FAILED), failed);
    console.log(JSON.stringify({
      processed: processed.map(publicSummary),
      failed: failed.map(publicSummary),
      pending: pending.length,
    }, null, 2));
    return;
  }

  throw new Error(`Unhandled command: ${opts.command}`);
}

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isCli) {
  main(process.argv.slice(2)).catch((err) => {
    console.error(`[replay-leads] ${err instanceof Error ? err.message : String(err)}`);
    process.exit(1);
  });
}
