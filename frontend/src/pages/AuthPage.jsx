import { useEffect, useState } from "react";
import { useAuth } from "../auth.jsx";
import { navigate } from "../router.js";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function validate(mode, { name, email, password }) {
  if (mode === "register" && !name.trim()) return "Введите имя";
  if (!EMAIL_RE.test(email.trim())) return "Введите корректный email";
  if (mode === "register" && password.length < 6) return "Пароль должен быть не короче 6 символов";
  if (!password) return "Введите пароль";
  return null;
}

export default function AuthPage() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  // Уже вошли — на главную
  useEffect(() => {
    if (user) navigate("/");
  }, [user]);

  const isRegister = mode === "register";
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  function switchMode(next) {
    setMode(next);
    setError(null);
  }

  async function onSubmit(e) {
    e.preventDefault();
    const problem = validate(mode, form);
    if (problem) return setError(problem);

    setBusy(true);
    setError(null);
    try {
      if (isRegister) await register(form.name.trim(), form.email.trim(), form.password);
      else await login(form.email.trim(), form.password);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="tabs" role="tablist">
        <button
          role="tab"
          aria-selected={!isRegister}
          className={`tab ${!isRegister ? "tab-active" : ""}`}
          onClick={() => switchMode("login")}
        >
          Вход
        </button>
        <button
          role="tab"
          aria-selected={isRegister}
          className={`tab ${isRegister ? "tab-active" : ""}`}
          onClick={() => switchMode("register")}
        >
          Регистрация
        </button>
      </div>

      <form onSubmit={onSubmit} noValidate>
        <h1 className="auth-title">{isRegister ? "Создайте аккаунт" : "С возвращением"}</h1>

        {isRegister && (
          <div className="field">
            <label htmlFor="name">Имя</label>
            <input id="name" autoComplete="name" value={form.name} onChange={set("name")} />
          </div>
        )}

        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={form.email}
            onChange={set("email")}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            autoComplete={isRegister ? "new-password" : "current-password"}
            value={form.password}
            onChange={set("password")}
          />
          {isRegister && <small>Не короче 6 символов</small>}
        </div>

        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}

        <button className="btn btn-primary btn-block" type="submit" disabled={busy}>
          {busy ? "Подождите…" : isRegister ? "Зарегистрироваться" : "Войти"}
        </button>
      </form>
    </section>
  );
}
