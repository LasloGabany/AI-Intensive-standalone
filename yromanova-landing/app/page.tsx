import Reveal from "@/components/Reveal";
import LeadForm from "@/components/LeadForm";
import AnalyticsConsent from "@/components/AnalyticsConsent";
import { analyticsConfigFromEnv } from "@/lib/analytics";
import { getLandingSettings, type LandingSettings } from "@/lib/landing-settings";
import {
  hero,
  pains,
  method,
  days,
  fit,
  experts,
  testimonials,
  format,
  value,
  finalCta,
  guarantee,
} from "@/lib/content";

// Dynamic rendering so the per-request CSP nonce (proxy.ts) is applied to
// framework scripts. Static HTML would ship nonce-less scripts that the
// strict-dynamic CSP blocks. Security gate §7 (CSP nonce) > static perf.
export const dynamic = "force-dynamic";

const analytics = analyticsConfigFromEnv();

export default async function Home() {
  const s = await getLandingSettings();
  return (
    <>
      <Header settings={s} />
      <main>
        <Hero settings={s} />
        {s.showPains && <Pains />}
        {s.showMethod && <Method />}
        {s.showDays && <Days />}
        {s.showFit && <Fit />}
        {s.showExperts && <Experts />}
        {s.showTestimonials && <Testimonials />}
        {s.showFormat && <Format />}
        {s.showValue && <Value />}
        <Cta />
      </main>
      <Footer />
      <AnalyticsConsent config={analytics} />
    </>
  );
}

function Header({ settings }: { settings: LandingSettings }) {
  return (
    <header className="site-header">
      <div className="wrap">
        <div className="brand">
          Романова<span>.</span>
        </div>
        <div className="header-meta">
          <span className="header-date">Бесплатно · {settings.eventDates}</span>
          <a href="#lead" className="btn btn-primary">
            Зарегистрироваться
          </a>
        </div>
      </div>
    </header>
  );
}

function Hero({ settings }: { settings: LandingSettings }) {
  return (
    <section className="hero">
      <div className="wrap hero-grid">
        <div>
          <Reveal>
            <span className="eyebrow">Бесплатный онлайн-интенсив · {settings.eventDates}</span>
          </Reveal>
          <Reveal delay={60}>
            <h1 className="hero-title">
              {settings.heroTitleLead} <em>{settings.heroTitleAccent}</em>
            </h1>
          </Reveal>
          <Reveal delay={120}>
            <p className="hero-lead">{settings.heroLead}</p>
          </Reveal>
          <Reveal delay={160}>
            <p className="hero-sub">{settings.heroSub}</p>
          </Reveal>
          <Reveal delay={200}>
            <p className="hero-note">{settings.heroNote}</p>
          </Reveal>
          <Reveal delay={240}>
            <div className="hero-actions">
              <a href="#lead" className="btn btn-primary">
                {settings.ctaText}
              </a>
              <span className="hero-cta-sub">{settings.ctaSub}</span>
            </div>
          </Reveal>
          <Reveal delay={300}>
            <ul className="hero-badges">
              {hero.badges.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
          </Reveal>
        </div>

        <Reveal delay={180} as="div">
          <aside className="hero-card">
            <div className="hero-card-price">
              {settings.heroPrice}&nbsp;<small>₽</small>
            </div>
            <div className="hero-card-strike">аналог — {settings.anchorTotal}</div>
            <ul className="hero-card-list">
              <li>Готовое позиционирование — к концу 1-го дня</li>
              <li>Первый пост вашим голосом — опубликован</li>
              <li>Контент-план на 10 недель — на руки</li>
              <li>Закрытый чат с куратором — сразу</li>
            </ul>
          </aside>
        </Reveal>
      </div>
    </section>
  );
}

function Pains() {
  return (
    <section className="section pains">
      <div className="wrap">
        <div className="section-head">
          <Reveal>
            <span className="eyebrow">{pains.intro}</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{pains.title}</h2>
          </Reveal>
        </div>
        <div className="pains-grid">
          {pains.items.map((p, i) => (
            <Reveal key={p.title} delay={i * 80} as="article">
              <article className="pain-card">
                <h3>{p.title}</h3>
                <p>{p.text}</p>
              </article>
            </Reveal>
          ))}
        </div>
        <Reveal delay={120}>
          <p className="pains-resolve">
            Это не про то, что вы мало работаете. Это про то, что у вас нет
            системы. <b>ИИ — это система.</b>
          </p>
        </Reveal>
      </div>
    </section>
  );
}

function Method() {
  return (
    <section className="section">
      <div className="wrap method-grid">
        <div>
          <Reveal>
            <span className="eyebrow">{method.kicker}</span>
          </Reveal>
          <Reveal delay={60}>
            <p className="method-quote">«{method.quote}»</p>
          </Reveal>
          <Reveal delay={120} as="div">
            <div className="method-body">
              {method.body.map((t, i) => (
                <p key={i}>{t}</p>
              ))}
            </div>
          </Reveal>
        </div>
        <Reveal delay={160} as="div">
          <div className="stat-card">
            <div className="stat-value">{method.stat.value}</div>
            <p className="stat-label">{method.stat.label}</p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Days() {
  return (
    <section className="section days">
      <div className="wrap">
        <div className="section-head center">
          <Reveal>
            <span className="eyebrow">3 вечера — 3 результата</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{days.title}</h2>
          </Reveal>
        </div>
        <div className="days-grid">
          {days.items.map((d, i) => (
            <Reveal key={d.day} delay={i * 90} as="div">
              <div className="day-card">
                <span className="day-tag">{d.day}</span>
                <h3>{d.title}</h3>
                <ul className="day-points">
                  {d.points.map((pt) => (
                    <li key={pt}>{pt}</li>
                  ))}
                </ul>
                <div className="day-prices">
                  <span className="day-anchor">{d.anchor}</span>
                  <span className="day-yours">{d.yours}</span>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Fit() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head center">
          <Reveal>
            <span className="eyebrow">Честная проверка</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{fit.title}</h2>
          </Reveal>
        </div>
        <div className="fit-grid">
          <Reveal as="div">
            <div className="fit-col fit-yes">
              <h3>{fit.forYou.title}</h3>
              <ul className="fit-list">
                {fit.forYou.items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            </div>
          </Reveal>
          <Reveal delay={90} as="div">
            <div className="fit-col fit-no">
              <h3>{fit.notForYou.title}</h3>
              <ul className="fit-list">
                {fit.notForYou.items.map((it) => (
                  <li key={it}>{it}</li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
        <Reveal delay={120}>
          <p className="fit-closer">{fit.closer}</p>
        </Reveal>
      </div>
    </section>
  );
}

function initials(name: string) {
  return name
    .split(" ")
    .map((w) => w[0])
    .slice(0, 2)
    .join("");
}

function Experts() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head center">
          <Reveal>
            <span className="eyebrow">Кто ведёт</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{experts.title}</h2>
          </Reveal>
        </div>
        <div className="experts-grid">
          {experts.items.map((e, i) => (
            <Reveal key={e.name} delay={i * 90} as="div">
              <div className="expert-card">
                <div className="expert-avatar" aria-hidden>
                  {initials(e.name)}
                </div>
                <div>
                  <h3>{e.name}</h3>
                  <p className="expert-role">{e.role}</p>
                  <p className="expert-bio">{e.bio}</p>
                  <ul className="expert-facts">
                    {e.facts.map((f) => (
                      <li key={f}>{f}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Testimonials() {
  return (
    <section className="section testi">
      <div className="wrap">
        <div className="section-head center">
          <Reveal>
            <span className="eyebrow">Отзывы выпускников</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{testimonials.title}</h2>
          </Reveal>
        </div>
        <div className="testi-grid">
          {testimonials.items.map((t, i) => (
            <Reveal key={i} delay={(i % 3) * 70} as="div">
              <figure className="testi-card">
                <span className="testi-mark" aria-hidden>
                  &ldquo;
                </span>
                <p>{t.text}</p>
                <figcaption className="testi-who">
                  <b>{t.name}</b> <span>· {t.meta}</span>
                </figcaption>
              </figure>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Format() {
  return (
    <section className="section">
      <div className="wrap">
        <div className="section-head">
          <Reveal>
            <span className="eyebrow">Формат</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{format.title}</h2>
          </Reveal>
        </div>
        <ol className="format-steps">
          {format.steps.map((s, i) => (
            <Reveal key={s.n} delay={i * 60} as="li">
              <div className="format-step">
                <span className="format-n">{s.n}</span>
                <div>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </ol>
      </div>
    </section>
  );
}

function Value() {
  return (
    <section className="section days">
      <div className="wrap">
        <div className="section-head center">
          <Reveal>
            <span className="eyebrow">Что внутри</span>
          </Reveal>
          <Reveal delay={60}>
            <h2 className="section-title">{value.title}</h2>
          </Reveal>
        </div>
        <Reveal as="div">
          <div className="value-card">
            {value.rows.map((r) => (
              <div className="value-row" key={r.item}>
                <span>{r.item}</span>
                <span>{r.price}</span>
              </div>
            ))}
            <div className="value-total">
              <span className="lbl">Суммарная стоимость аналога</span>
              <span className="sum">{value.total}</span>
            </div>
            <div className="value-final">
              <span className="lbl">Ваши вложения</span>
              <span className="free">{value.yours}</span>
            </div>
          </div>
        </Reveal>
        <p className="value-note">{value.note}</p>
      </div>
    </section>
  );
}

function Cta() {
  return (
    <section className="section cta" id="lead">
      <div className="wrap">
        <Reveal as="div">
          <div className="cta-inner">
            <div>
              <span className="eyebrow">{finalCta.sub}</span>
              <h2>{finalCta.title}</h2>
              <p className="cta-sub">
                Сразу после регистрации — доступ в закрытый чат и первое задание.
              </p>
              <ul className="cta-bullets">
                {finalCta.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </div>
            <LeadForm />
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="site-footer">
      <div className="wrap">
        <p className="footer-guarantee">{guarantee}</p>
        <div className="footer-meta">
          <span>© 2026 Юлия Романова</span>
          <a href="#lead">Регистрация</a>
          <a href="/privacy">Политика конфиденциальности</a>
        </div>
      </div>
    </footer>
  );
}
