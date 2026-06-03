export const ADMIN_AUTH_HEADER = 'Basic realm="Keystatic Admin", charset="UTF-8"';

export type AdminAccessDecision = 'allow' | 'not-admin' | 'disabled' | 'challenge';

type EnvLike = Record<string, string | undefined>;

type Input = {
  pathname: string;
  authorization: string | null;
  env?: EnvLike;
  nodeEnv?: string;
};

export function isAdminPath(pathname: string): boolean {
  return pathname === '/keystatic' || pathname.startsWith('/keystatic/') || pathname.startsWith('/api/keystatic');
}

function isEnabled(value: string | undefined): boolean {
  return String(value || '').trim().toLowerCase() === 'true';
}

function isSet(value: string | undefined): value is string {
  return typeof value === 'string' && value.trim().length > 0;
}

function decodeBasicAuth(header: string | null): { user: string; password: string } | null {
  if (!header?.startsWith('Basic ')) return null;
  try {
    const encoded = header.slice('Basic '.length).trim();
    const decoded = typeof atob === 'function'
      ? atob(encoded)
      : Buffer.from(encoded, 'base64').toString('utf8');
    const splitAt = decoded.indexOf(':');
    if (splitAt < 0) return null;
    return {
      user: decoded.slice(0, splitAt),
      password: decoded.slice(splitAt + 1),
    };
  } catch {
    return null;
  }
}

export function adminAccessDecision({
  pathname,
  authorization,
  env = process.env,
  nodeEnv = process.env.NODE_ENV,
}: Input): AdminAccessDecision {
  if (!isAdminPath(pathname)) return 'not-admin';
  if (nodeEnv !== 'production') return 'allow';

  if (!isEnabled(env.KEYSTATIC_ADMIN_ENABLED)) return 'disabled';
  if (!isSet(env.KEYSTATIC_ADMIN_USER) || !isSet(env.KEYSTATIC_ADMIN_PASSWORD)) return 'disabled';

  const credentials = decodeBasicAuth(authorization);
  if (
    credentials?.user === env.KEYSTATIC_ADMIN_USER &&
    credentials.password === env.KEYSTATIC_ADMIN_PASSWORD
  ) {
    return 'allow';
  }

  return 'challenge';
}
