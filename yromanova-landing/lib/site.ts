export type SiteConfig = {
  url: string;
  title: string;
  description: string;
};

type EnvLike = Record<string, string | undefined>;

function cleanUrl(value: string | undefined): string | null {
  const raw = value?.trim();
  if (!raw) return null;
  try {
    const url = new URL(raw);
    return url.toString().replace(/\/$/, "");
  } catch {
    return null;
  }
}

export function siteConfigFromEnv(env: EnvLike = process.env): SiteConfig {
  return {
    url: cleanUrl(env.PUBLIC_SITE_URL) ?? "http://localhost:3000",
    title: "Интенсив для психологов · Бесплатно, 11–13 мая",
    description:
      "За 3 вечера — готовое позиционирование, первый пост и план работы на 10 недель. Бесплатный онлайн-интенсив по ИИ для практикующих психологов.",
  };
}
