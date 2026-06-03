import { describe, expect, it } from "vitest";
import {
  clientLeadError,
  normalizeLeadPayload,
  serverLeadMessage,
  successLeadMessage,
  successLeadSubMessage,
} from "./lead-validation";

describe("normalizeLeadPayload", () => {
  it("trims name and email while preserving honeypot value", () => {
    const payload = normalizeLeadPayload({
      name: "  Анна Тестова  ",
      email: "  ANNA@example.com  ",
      company: "bot-value",
    });

    expect(payload).toEqual({
      name: "Анна Тестова",
      email: "ANNA@example.com",
      company: "bot-value",
    });
  });
});

describe("clientLeadError", () => {
  it("asks for consent before sending", () => {
    expect(
      clientLeadError({
        name: "Анна",
        email: "anna@example.com",
        consent: false,
      })
    ).toBe("Подтвердите согласие на обработку данных.");
  });

  it("rejects an empty name", () => {
    expect(
      clientLeadError({
        name: " ",
        email: "anna@example.com",
        consent: true,
      })
    ).toBe("Введите имя.");
  });

  it("rejects an invalid email", () => {
    expect(
      clientLeadError({
        name: "Анна",
        email: "bad-email",
        consent: true,
      })
    ).toBe("Введите корректный email.");
  });

  it("accepts valid form data", () => {
    expect(
      clientLeadError({
        name: "Анна",
        email: "anna@example.com",
        consent: true,
      })
    ).toBeNull();
  });
});

describe("serverLeadMessage", () => {
  it("maps API validation errors to field-specific copy", () => {
    expect(serverLeadMessage(400, "name")).toBe("Введите имя.");
    expect(serverLeadMessage(400, "email")).toBe("Введите корректный email.");
  });

  it("keeps transient failures as retry copy", () => {
    expect(serverLeadMessage(502, "upstream")).toBe(
      "Не удалось отправить. Попробуйте ещё раз через минуту."
    );
  });
});


describe("successLeadMessage", () => {
  it("does not promise immediate email delivery when a lead is queued", () => {
    expect(successLeadMessage({ queued: true })).toBe(
      "Заявка принята. Материалы отправим, как только обработаем регистрацию."
    );
  });

  it("keeps the normal delivery copy for direct GetCourse success", () => {
    expect(successLeadMessage({ queued: false })).toBe(
      "Проверьте почту — первое задание уже отправлено."
    );
  });
});


describe("successLeadSubMessage", () => {
  it("does not claim the chat link was emailed when a lead is queued", () => {
    expect(successLeadSubMessage({ queued: true })).toBe(
      "Мы сохранили заявку и обработаем её вручную."
    );
  });

  it("keeps the normal chat link copy for direct GetCourse success", () => {
    expect(successLeadSubMessage({ queued: false })).toBe(
      "Ссылка на закрытый чат пришла на указанную почту."
    );
  });
});
