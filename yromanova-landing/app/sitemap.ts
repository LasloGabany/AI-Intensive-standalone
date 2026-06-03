import type { MetadataRoute } from "next";
import { siteConfigFromEnv } from "@/lib/site";

export default function sitemap(): MetadataRoute.Sitemap {
  const site = siteConfigFromEnv();
  return [
    {
      url: site.url,
      lastModified: new Date("2026-06-02T00:00:00.000Z"),
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${site.url}/privacy`,
      lastModified: new Date("2026-06-02T00:00:00.000Z"),
      changeFrequency: "monthly",
      priority: 0.3,
    },
  ];
}
