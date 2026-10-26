import { useAuth } from "../auth.jsx";

export default function Header() {
  const { user, logout } = useAuth();

  return (
    <header className="header">
      <a className="brand" href="#/">
        <span aria-hidden="true">🌸</span> Flower Delivery
      </a>
      <nav className="header-actions">
        <a className="nav-link" href="#/catalog">
          Каталог
        </a>
        {user ? (
          <>
            <span className="user-name">{user.name}</span>
            <button className="btn btn-ghost" onClick={logout}>
              Выйти
            </button>
          </>
        ) : (
          <a className="btn btn-primary" href="#/login">
            Войти
          </a>
        )}
      </nav>
    </header>
  );
}
