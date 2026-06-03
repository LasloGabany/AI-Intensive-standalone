"use client";

import { useEffect, useState } from "react";
import type { AnalyticsConfig } from "@/lib/analytics";
import { hasAnalytics } from "@/lib/analytics";

type Consent = "unknown" | "accepted" | "declined";
const STORAGE_KEY = "yromanova-analytics-consent";

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
    ym?: (...args: unknown[]) => void;
  }
}

function loadScript(src: string) {
  if (document.querySelector(`script[src="${src}"]`)) return;
  const script = document.createElement("script");
  script.async = true;
  script.src = src;
  document.head.appendChild(script);
}

function queueYandexCall(args: unknown[]) {
  const ym = window.ym as ((...args: unknown[]) => void) & { a?: unknown[] };
  ym.a = ym.a || [];
  ym.a.push(args);
}

function enableAnalytics(config: AnalyticsConfig) {
  if (config.gaId) {
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function gtag(...args: unknown[]) {
      window.dataLayer?.push(args);
    };
    window.gtag("js", new Date());
    window.gtag("config", config.gaId, { anonymize_ip: true });
    loadScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(config.gaId)}`);
  }

  if (config.ymId) {
    window.ym = window.ym || function ym(...args: unknown[]) {
      queueYandexCall(args);
    };
    window.ym(Number(config.ymId), "init", {
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
    });
    loadScript("https://mc.yandex.ru/metrika/tag.js");
  }
}

export default function AnalyticsConsent({ config }: { config: AnalyticsConfig }) {
  const [consent, setConsent] = useState<Consent>("unknown");

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === "accepted" || stored === "declined") setConsent(stored);
  }, []);

  useEffect(() => {
    if (consent === "accepted" && hasAnalytics(config)) enableAnalytics(config);
  }, [config, consent]);

  if (!hasAnalytics(config) || consent !== "unknown") return null;

  function choose(next: Exclude<Consent, "unknown">) {
    window.localStorage.setItem(STORAGE_KEY, next);
    setConsent(next);
  }

  return (
    <div className="cookie-consent" role="region" aria-label="Настройки аналитики">
      <p>Мы используем аналитику, чтобы понимать, какие блоки лендинга помогают с регистрацией.</p>
      <div className="cookie-actions">
        <button type="button" className="btn btn-primary" onClick={() => choose("accepted")}>
          Разрешить
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => choose("declined")}>
          Отклонить
        </button>
      </div>
    </div>
  );
}
