"use client";

// Top-level error boundary. Required by Next for the global-error slot and
// renders its own <html>/<body>. No PII, generic friendly copy.
export default function GlobalError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="ru">
      <body
        style={{
          margin: 0,
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
          fontFamily: "system-ui, sans-serif",
          background: "#f6f2ea",
          color: "#2a2522",
        }}
      >
        <main style={{ textAlign: "center", padding: "2rem" }}>
          <h1 style={{ fontWeight: 500 }}>Что-то пошло не так</h1>
          <p style={{ color: "#6b635c" }}>
            Попробуйте обновить страницу. Если не помогло — напишите нам на почту.
          </p>
          <button
            onClick={reset}
            style={{
              marginTop: "1.2rem",
              padding: "0.8rem 1.6rem",
              borderRadius: "999px",
              border: "none",
              background: "#8a6d3b",
              color: "#fff",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Обновить
          </button>
        </main>
      </body>
    </html>
  );
}
