import type { Metadata } from "next";
import { privacyConfigFromEnv } from "@/lib/compliance";

export const metadata: Metadata = {
  title: "Политика конфиденциальности · Интенсив для психологов",
  description: "Политика обработки персональных данных для регистрации на бесплатный онлайн-интенсив.",
};

export default function PrivacyPage() {
  const privacy = privacyConfigFromEnv();

  return (
    <main className="privacy-page">
      <section className="wrap privacy-content">
        <a className="privacy-back" href="/">
          Вернуться на лендинг
        </a>
        <h1>Политика конфиденциальности</h1>
        <p>
          Оставляя заявку на участие в интенсиве, вы передаёте имя и email для
          регистрации, отправки материалов и организационных сообщений по
          интенсиву.
        </p>
        <p>
          Данные не публикуются и не передаются третьим лицам, кроме сервисов,
          необходимых для обработки заявки и отправки материалов.
        </p>
        <p>
          Оператор данных: {privacy.operatorName}.
        </p>
        {privacy.siteUrl && (
          <p>
            Сайт регистрации: <a href={privacy.siteUrl}>{privacy.siteUrl}</a>.
          </p>
        )}
        <p>
          Вы можете запросить удаление или уточнение данных
          {privacy.contactEmail ? (
            <>
              , написав на <a href={`mailto:${privacy.contactEmail}`}>{privacy.contactEmail}</a>.
            </>
          ) : (
            " через контакты, указанные в рассылке или на странице регистрации."
          )}
        </p>
      </section>
    </main>
  );
}
