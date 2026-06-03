export type PrivacyConfig = {
  operatorName: string;
  contactEmail: string | null;
  siteUrl: string | null;
};

type EnvLike = Record<string, string | undefined>;

function clean(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function privacyConfigFromEnv(env: EnvLike = process.env): PrivacyConfig {
  return {
    operatorName: clean(env.PRIVACY_OPERATOR_NAME) ?? "Организатор интенсива",
    contactEmail: clean(env.PRIVACY_CONTACT_EMAIL),
    siteUrl: clean(env.PUBLIC_SITE_URL),
  };
}
