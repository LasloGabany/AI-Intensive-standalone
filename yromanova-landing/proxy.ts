import { NextRequest, NextResponse } from "next/server";
import { ADMIN_AUTH_HEADER, adminAccessDecision } from "@/lib/admin-access";
import { securityHeaders } from "@/lib/security-headers";

function hardenedTextResponse(body: string, status: number) {
  const headers = securityHeaders("admin", { dev: process.env.NODE_ENV === "development" });
  const response = new NextResponse(body, { status });
  for (const [name, value] of Object.entries(headers)) response.headers.set(name, value);
  response.headers.set("X-Robots-Tag", "noindex, nofollow");
  return response;
}

// Next 16 proxy (formerly middleware). Generates a per-request CSP nonce,
// exposes it via x-nonce so the App Router applies it to framework scripts,
// and stamps the hardened header set on every dynamic response.
export function proxy(request: NextRequest) {
  const adminDecision = adminAccessDecision({
    pathname: request.nextUrl.pathname,
    authorization: request.headers.get("authorization"),
    env: process.env,
    nodeEnv: process.env.NODE_ENV,
  });

  if (adminDecision === "disabled") return hardenedTextResponse("Not found", 404);
  if (adminDecision === "challenge") {
    const response = hardenedTextResponse("Authentication required", 401);
    response.headers.set("WWW-Authenticate", ADMIN_AUTH_HEADER);
    return response;
  }
  if (adminDecision === "allow") {
    const response = NextResponse.next();
    response.headers.set("X-Robots-Tag", "noindex, nofollow");
    return response;
  }

  const nonce = Buffer.from(crypto.randomUUID()).toString("base64");
  const dev = process.env.NODE_ENV === "development";
  const headers = securityHeaders(nonce, { dev });

  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", headers["Content-Security-Policy"]);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  for (const [name, value] of Object.entries(headers)) {
    response.headers.set(name, value);
  }
  return response;
}

export const config = {
  // Apply to all routes except Next static assets, image optimizer, favicon.
  matcher: [
    {
      source: "/((?!_next/static|_next/image|favicon.ico).*)",
      missing: [
        { type: "header", key: "next-router-prefetch" },
        { type: "header", key: "purpose", value: "prefetch" },
      ],
    },
  ],
};
