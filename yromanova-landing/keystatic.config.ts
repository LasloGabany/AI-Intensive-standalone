import { config, fields, singleton } from "@keystatic/core";

// Local storage = edits write to ./content/*.json (dev / self-hosted).
// For client editing on Vercel (read-only FS) switch to:
//   storage: { kind: "github", repo: "owner/repo" }
// + Keystatic GitHub App + env (see README "Keystatic prod").
export default config({
  storage: { kind: "local" },
  ui: {
    brand: { name: "Романова · Лендинг" },
  },
  singletons: {
    settings: singleton({
      label: "Настройки лендинга",
      path: "content/settings",
      format: { data: "json" },
      schema: {
        // --- Тексты ---
        eventDates: fields.text({
          label: "Даты интенсива",
          description: "Показывается в шапке и hero, напр. «11–13 мая»",
          validation: { isRequired: true },
        }),
        heroTitleLead: fields.text({ label: "Hero — заголовок (начало)" }),
        heroTitleAccent: fields.text({
          label: "Hero — заголовок (акцент)",
          description: "Выделяется золотым курсивом",
        }),
        heroLead: fields.text({ label: "Hero — подзаголовок", multiline: true }),
        heroSub: fields.text({ label: "Hero — описание", multiline: true }),
        heroNote: fields.text({ label: "Hero — приписка", multiline: true }),
        ctaText: fields.text({ label: "Текст кнопки CTA" }),
        ctaSub: fields.text({ label: "Подпись под CTA", multiline: true }),
        heroPrice: fields.text({ label: "Цена (hero)", description: "напр. «0»" }),
        anchorTotal: fields.text({
          label: "Цена-якорь (зачёркнутая)",
          description: "напр. «40 000 ₽»",
        }),

        // --- Переключатели секций ---
        showPains: fields.checkbox({ label: "Секция «Боли»", defaultValue: true }),
        showMethod: fields.checkbox({ label: "Секция «Метод»", defaultValue: true }),
        showDays: fields.checkbox({ label: "Секция «3 дня»", defaultValue: true }),
        showFit: fields.checkbox({ label: "Секция «Для кого»", defaultValue: true }),
        showExperts: fields.checkbox({ label: "Секция «Эксперты»", defaultValue: true }),
        showTestimonials: fields.checkbox({ label: "Секция «Отзывы»", defaultValue: true }),
        showFormat: fields.checkbox({ label: "Секция «Формат»", defaultValue: true }),
        showValue: fields.checkbox({ label: "Секция «Что внутри»", defaultValue: true }),
      },
    }),
  },
});
