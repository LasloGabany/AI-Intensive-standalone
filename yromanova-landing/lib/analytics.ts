export type AnalyticsConfig = {
  gaId: string | null;
  ymId: string | null;
};

type EnvLike = Record<string, string | undefined>;

function clean(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function analyticsConfigFromEnv(env: EnvLike = process.env): AnalyticsConfig {
  return {
    gaId: clean(env.NEXT_PUBLIC_GA_ID),
    ymId: clean(env.NEXT_PUBLIC_YM_ID),
  };
}

export function hasAnalytics(config: AnalyticsConfig): boolean {
  return Boolean(config.gaId || config.ymId);
}
