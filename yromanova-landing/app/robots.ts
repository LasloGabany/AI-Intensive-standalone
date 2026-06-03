import type { MetadataRoute } from "next";
import { siteConfigFromEnv } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  const site = siteConfigFromEnv();
  return {
    rules: {
      userAgent: "*",
      allow: "/",
    },
    sitemap: `${site.url}/sitemap.xml`,
  };
}
