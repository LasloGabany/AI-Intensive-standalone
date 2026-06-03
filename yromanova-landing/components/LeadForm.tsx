"use client";

import { useState } from "react";
import {
  clientLeadError,
  normalizeLeadPayload,
  serverLeadMessage,
  successLeadMessage,
  successLeadSubMessage,
} from "@/lib/lead-validation";

type Status = "idle" | "loading" | "ok" | "error";

export default function LeadForm({ id = "lead" }: { id?: string }) {
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [successQueued, setSuccessQueued] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status === "loading") return;
    const form = e.currentTarget;
    const data = new FormData(form);

    const payload = normalizeLeadPayload({
      name: data.get("name"),
      email: data.get("email"),
      company: data.get("company"),
    });
    const error = clientLeadError({
      name: payload.name,
      email: payload.email,
      consent: Boolean(data.get("consent")),
    });

    if (error) {
      setStatus("error");
      setMessage(error);
      return;
    }

    setStatus("loading");
    setMessage("");
    try {
      const res = await fetch("/api/lead", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = (await res.json().catch(() => null)) as
        | { error?: string; queued?: boolean }
        | null;
      if (!res.ok) {
        throw new Error(serverLeadMessage(res.status, body?.error));
      }
      const queued = Boolean(body?.queued);
      setSuccessQueued(queued);
      setStatus("ok");
      setMessage(successLeadMessage({ queued }));
      form.reset();
    } catch (err) {
      setStatus("error");
      setMessage(
        err instanceof Error
          ? err.message
          : "Не удалось отправить. Попробуйте ещё раз через минуту."
      );
    }
  }

  if (status === "ok") {
    return (
      <div className="form-done" role="status">
        <div className="form-done-mark" aria-hidden>✓</div>
        <h3>Готово. Вы в списке.</h3>
        <p>{message}</p>
        <p className="form-done-sub">{successLeadSubMessage({ queued: successQueued })}</p>
      </div>
    );
  }

  return (
    <form className="lead-form" onSubmit={onSubmit} noValidate>
      <div className="field">
        <label htmlFor={`${id}-name`}>Как вас зовут?</label>
        <input id={`${id}-name`} name="name" type="text" autoComplete="name" required placeholder="Имя" />
      </div>
      <div className="field">
        <label htmlFor={`${id}-email`}>Куда прислать материалы?</label>
        <input id={`${id}-email`} name="email" type="email" autoComplete="email" required placeholder="email@example.com" />
      </div>

      {/* honeypot — visually hidden, off-screen for a11y */}
      <div aria-hidden className="hp">
        <label>Компания<input name="company" tabIndex={-1} autoComplete="off" /></label>
      </div>

      <label className="consent">
        <input name="consent" type="checkbox" />
        <span>
          Согласен на обработку персональных данных и условия{" "}
          <a href="/privacy" target="_blank" rel="noreferrer">
            Политики конфиденциальности
          </a>
        </span>
      </label>

      <button className="btn btn-primary form-submit" type="submit" disabled={status === "loading"}>
        {status === "loading" ? "Отправляем…" : "Занять место бесплатно"}
      </button>

      {status === "error" && (
        <p className="form-error" role="alert">{message}</p>
      )}
      <p className="form-fine">Без карты. Без скрытых платежей. Место в два клика.</p>
    </form>
  );
}
