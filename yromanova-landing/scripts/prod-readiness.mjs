#!/usr/bin/env node
import { fileURLToPath } from 'node:url';

const REQUIRED = [
  ['PUBLIC_SITE_URL', 'PUBLIC_SITE_URL is required for canonical production URLs.'],
  ['GC_ACCOUNT', 'GC_ACCOUNT is required for production lead delivery.'],
  ['GC_API_KEY', 'GC_API_KEY is required for production lead delivery.'],
  ['PRIVACY_OPERATOR_NAME', 'PRIVACY_OPERATOR_NAME is required for the privacy policy.'],
  ['PRIVACY_CONTACT_EMAIL', 'PRIVACY_CONTACT_EMAIL is required for privacy requests.'],
  ['LEAD_REPLAY_DIR', 'LEAD_REPLAY_DIR is required until a managed queue replaces file-backed replay.'],
];

const CONFIRMATIONS = [
  ['MANAGED_LEAD_QUEUE_CONFIRMED', 'MANAGED_LEAD_QUEUE_CONFIRMED=true is required for multi-instance/serverless production.'],
  ['DKIM_CONFIRMED', 'DKIM_CONFIRMED=true is required before launch.'],
  ['DMARC_CONFIRMED', 'DMARC_CONFIRMED=true is required before launch.'],
  ['DOMAIN_RENEWAL_CONFIRMED', 'DOMAIN_RENEWAL_CONFIRMED=true is required before launch.'],
];

function isSet(value) {
  return typeof value === 'string' && value.trim().length > 0;
}

function isTrue(value) {
  return String(value || '').trim().toLowerCase() === 'true';
}

export function checkProdReadiness(env = process.env) {
  const failures = [];
  const checks = [];

  for (const [name, message] of REQUIRED) {
    const ok = isSet(env[name]);
    checks.push({ name, status: ok ? 'set' : 'missing' });
    if (!ok) failures.push(message);
  }

  for (const [name, message] of CONFIRMATIONS) {
    const ok = isTrue(env[name]);
    checks.push({ name, status: ok ? 'confirmed' : 'missing' });
    if (!ok) failures.push(message);
  }

  const adminEnabled = isTrue(env.KEYSTATIC_ADMIN_ENABLED);
  const adminUserSet = isSet(env.KEYSTATIC_ADMIN_USER);
  const adminPasswordSet = isSet(env.KEYSTATIC_ADMIN_PASSWORD);
  checks.push({
    name: 'KEYSTATIC_ADMIN',
    status: adminEnabled ? (adminUserSet && adminPasswordSet ? 'protected' : 'misconfigured') : 'disabled',
  });
  if (adminEnabled && (!adminUserSet || !adminPasswordSet)) {
    failures.push('KEYSTATIC_ADMIN_USER and KEYSTATIC_ADMIN_PASSWORD are required when KEYSTATIC_ADMIN_ENABLED=true.');
  }

  return { ok: failures.length === 0, failures, checks };
}


export function formatReport(report) {
  const lines = ['Production readiness check'];
  lines.push(report.ok ? 'Status: PASS' : 'Status: FAIL');
  lines.push('');
  lines.push('Checks:');
  for (const check of report.checks) lines.push(`- ${check.name}: ${check.status}`);
  if (report.failures.length) {
    lines.push('');
    lines.push('Failures:');
    for (const failure of report.failures) lines.push(`- ${failure}`);
  }
  return lines.join('\n');
}

const isCli = process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1];
if (isCli) {
  const report = checkProdReadiness(process.env);
  console.log(formatReport(report));
  process.exit(report.ok ? 0 : 1);
}
