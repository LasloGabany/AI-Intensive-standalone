// Security headers + CSP builder (pure, testable).
// Wired into proxy.ts which generates a per-request nonce.
// Policy: script-src strict (nonce + strict-dynamic), style-src allows
// 'unsafe-inline' (next/font injected styles + React inline style attrs —
// low-risk tradeoff, matches project web/security.md standard).

type Opts = { dev: boolean };

export function buildCsp(nonce: string, { dev }: Opts): string {
  const directives = [
    `default-src 'self'`,
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ""}`,
    `style-src 'self' 'unsafe-inline'`,
    `img-src 'self' blob: data: https:`,
    `font-src 'self'`,
    `connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://mc.yandex.ru${dev ? " ws:" : ""}`,
    `object-src 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `frame-ancestors 'none'`,
    // force https in prod; would break http://localhost in dev
    ...(dev ? [] : ["upgrade-insecure-requests"]),
  ];
  return directives.join("; ");
}

export function securityHeaders(
  nonce: string,
  opts: Opts
): Record<string, string> {
  return {
    "Content-Security-Policy": buildCsp(nonce, opts),
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
  };
}
