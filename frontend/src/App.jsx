import { useEffect, useState } from "react";

// Заглушка: проверяем, что фронтенд достаёт до backend.
// Дальше здесь появятся страницы каталога, корзины и истории заказов.
export default function App() {
  const [status, setStatus] = useState("проверяем...");

  useEffect(() => {
    fetch("/api/health")
      .then((response) => response.json())
      .then((data) => setStatus(data.status === "ok" ? "работает" : "ошибка"))
      .catch(() => setStatus("недоступен"));
  }, []);

  return (
    <main style={{ fontFamily: "sans-serif", padding: "2rem" }}>
      <h1>Flower Delivery</h1>
      <p>Backend: {status}</p>
    </main>
  );
}
