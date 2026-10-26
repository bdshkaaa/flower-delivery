import { useAuth } from "../auth.jsx";
import { useCart } from "../cart.jsx";

export default function Header() {
  const { user, logout } = useAuth();
  const { count } = useCart();

  return (
    <header className="header">
      <a className="brand" href="#/">
        <span aria-hidden="true">🌸</span> Flower Delivery
      </a>
      <nav className="header-actions">
        <a className="nav-link" href="#/catalog">
          Каталог
        </a>
        <a className="nav-link" href="#/cart">
          Корзина{count > 0 && <span className="badge" aria-label={`товаров: ${count}`}>{count}</span>}
        </a>
        {user ? (
          <>
            <a className="nav-link" href="#/orders">
              Заказы
            </a>
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
