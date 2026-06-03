export type ClientLeadFields = {
  name: string;
  email: string;
  consent: boolean;
};

export type LeadPayload = {
  name: string;
  email: string;
  company: string;
};

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

export function normalizeLeadPayload(fields: {
  name: FormDataEntryValue | null | string;
  email: FormDataEntryValue | null | string;
  company: FormDataEntryValue | null | string;
}): LeadPayload {
  return {
    name: String(fields.name || "").trim(),
    email: String(fields.email || "").trim(),
    company: String(fields.company || ""),
  };
}

export function clientLeadError(fields: ClientLeadFields): string | null {
  if (!fields.consent) {
    return "Подтвердите согласие на обработку данных.";
  }
  if (fields.name.trim().length < 2) {
    return "Введите имя.";
  }
  if (!EMAIL_RE.test(fields.email.trim())) {
    return "Введите корректный email.";
  }
  return null;
}

export function serverLeadMessage(status: number, error?: string): string {
  if (status === 400 && error === "name") return "Введите имя.";
  if (status === 400 && error === "email") return "Введите корректный email.";
  if (status === 429) return "Слишком много заявок. Попробуйте ещё раз через минуту.";
  return "Не удалось отправить. Попробуйте ещё раз через минуту.";
}


export function successLeadMessage(result: { queued?: boolean }): string {
  if (result.queued) {
    return "Заявка принята. Материалы отправим, как только обработаем регистрацию.";
  }
  return "Проверьте почту — первое задание уже отправлено.";
}


export function successLeadSubMessage(result: { queued?: boolean }): string {
  if (result.queued) {
    return "Мы сохранили заявку и обработаем её вручную.";
  }
  return "Ссылка на закрытый чат пришла на указанную почту.";
}
