import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useCart } from "../cart.jsx";
import { formatPrice, orderStatusLabel } from "../labels.js";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short" });

export default function OrdersPage() {
  const { user, token } = useAuth();
  const { flash: pendingFlash, setFlash } = useCart();
  // Запоминаем сообщение при открытии страницы и сразу очищаем общее, чтобы оно не показалось снова
  const [flash] = useState(pendingFlash);
  const [state, setState] = useState({ status: "loading", orders: [] });
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    setState((s) => ({ ...s, status: "loading" }));
    api("/orders", { token, signal: controller.signal })
      .then((orders) => setState({ status: "ok", orders }))
      .catch((err) => {
        if (err.name !== "AbortError") setState({ status: "error", orders: [], message: err.message });
      });
    return () => controller.abort();
  }, [token, reloadKey]);

  useEffect(() => setFlash(null), [setFlash]);

  if (!user) {
    return (
      <section>
        <h1 className="page-title">Мои заказы</h1>
        <div className="notice">
          <p>Войдите, чтобы увидеть историю заказов</p>
          <a className="btn btn-primary" href="#/login">
            Войти
          </a>
        </div>
      </section>
    );
  }

  return (
    <section>
      <h1 className="page-title">Мои заказы</h1>

      {flash && (
        <p className="success" role="status">
          Заказ оформлен! Сумма: {formatPrice(flash.total_price)}.
          {flash.delivery_approximate && " Стоимость доставки предварительная, мы её уточним."}
        </p>
      )}

      {state.status === "loading" && <div className="card skeleton" aria-busy="true" aria-label="Загрузка" />}

      {state.status === "error" && (
        <div className="notice">
          <p>{state.message}</p>
          <button className="btn btn-primary" onClick={() => setReloadKey((k) => k + 1)}>
            Повторить
          </button>
        </div>
      )}

      {state.status === "ok" && state.orders.length === 0 && (
        <div className="notice">
          <p>Заказов пока нет</p>
          <a className="btn btn-primary" href="#/catalog">
            Выбрать букет
          </a>
        </div>
      )}

      {state.status === "ok" && state.orders.length > 0 && (
        <ul className="orders">
          {state.orders.map((order) => (
            <li key={order.id} className="order">
              <div className="order-head">
                <span>{dateFormat.format(new Date(order.created_at))}</span>
                <span className="tag">{orderStatusLabel(order.status)}</span>
              </div>
              <ul className="order-items">
                {order.items.map((item) => (
                  <li key={item.product_id}>
                    {item.name} × {item.quantity}
                    <span>{formatPrice(item.unit_price * item.quantity)}</span>
                  </li>
                ))}
              </ul>
              <p className="muted">
                {order.delivery_type === "pickup" ? "Самовывоз" : `Доставка: ${order.address}`}
                {order.delivery_type === "delivery" &&
                  ` · ${formatPrice(order.delivery_cost)}${order.delivery_approximate ? " (предварительно)" : ""}`}
              </p>
              <p className="order-total">Итого: {formatPrice(order.total_price)}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
