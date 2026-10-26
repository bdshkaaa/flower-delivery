import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";

export default function HomePage() {
  const { user } = useAuth();
  const [backend, setBackend] = useState("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((r) => r.json())
      .then((d) => setBackend(d.status === "ok" ? "ok" : "error"))
      .catch(() => setBackend("error"));
  }, []);

  return (
    <section className="hero">
      <h1>{user ? `Здравствуйте, ${user.name}!` : "Цветы с доставкой"}</h1>
      <p className="lead">
        Выберите букет к любому поводу и сразу увидите стоимость и срок доставки до оплаты.
      </p>
      <div className="hero-actions">
        <a className="btn btn-primary btn-large" href="#/catalog">
          Смотреть каталог
        </a>
        {!user && (
          <a className="btn btn-ghost btn-large" href="#/login">
            Войти
          </a>
        )}
      </div>
      <p className={`status status-${backend}`}>
        Сервер:{" "}
        {backend === "checking" ? "проверяем…" : backend === "ok" ? "работает" : "недоступен"}
      </p>
    </section>
  );
}
