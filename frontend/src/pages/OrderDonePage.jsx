import { useAuth } from "../auth.jsx";
import { formatAddressDetails, formatPhone, formatPrice } from "../labels.js";
import { formatCountdown, formatExpected, paymentMethodLabel } from "../orderFlow.js";
import { useCountdown, useOrder } from "../useOrder.js";

// Завершающий экран после оплаты: «Заказ принят» и что будет дальше.
export default function OrderDonePage({ id }) {
  const { user, token } = useAuth();
  const { status, order, receivedAt, message, reload } = useOrder(id, token);
  const left = useCountdown(order?.seconds_left ?? null, receivedAt);

  if (!user) {
    return (
      <section>
        <div className="notice">
          <p>Войдите, чтобы увидеть заказ</p>
          <a className="btn btn-primary" href="#/login">
            Войти
          </a>
        </div>
      </section>
    );
  }
  if (status === "loading") return <div className="card skeleton" aria-busy="true" aria-label="Загрузка" />;
  if (status === "notfound" || (status === "error" && !order)) {
    return (
      <section>
        <div className="notice">
          <p>{status === "notfound" ? "Заказ не найден" : message}</p>
          {status === "error" ? (
            <button className="btn btn-primary" onClick={reload}>
              Повторить
            </button>
          ) : (
            <a className="btn btn-primary" href="#/orders">
              К моим заказам
            </a>
          )}
        </div>
      </section>
    );
  }

  // Если заказ ещё не оплачен, подтверждать нечего: возвращаем к оплате
  if (order.status === "created") {
    return (
      <section>
        <div className="notice">
          <p>Заказ №{order.number} ещё не оплачен</p>
          <small>Пока он не оплачен, мы не начинаем сборку.</small>
          <a className="btn btn-primary" href={`#/order/${id}/pay`}>
            Перейти к оплате
          </a>
        </div>
      </section>
    );
  }

  const pickup = order.delivery_type === "pickup";
  const expected = order.expected_at ? formatExpected(order.expected_at) : null;
  const details = [formatAddressDetails(order), order.recipient_name && `получатель ${order.recipient_name}`,
    order.recipient_phone && formatPhone(order.recipient_phone)].filter(Boolean).join(" · ");

  return (
    <section className="done">
      <div className="done-hero">
        <div className="check-badge" aria-hidden="true">✓</div>
        <h1>Спасибо! Заказ №{order.number} принят</h1>
        <p className="lead">
          {pickup
            ? "Мы уже собираем ваш букет. Когда он будет готов, его можно забрать в магазине."
            : "Мы уже собираем ваш букет и скоро передадим его курьеру."}
        </p>
      </div>

      {left != null && (
        <div className="eta-card" role="status">
          <span className="muted">{pickup ? "Будет готов через" : "Будет у вас через"}</span>
          <strong className="eta-value">{formatCountdown(left)}</strong>
          {expected && <span className="muted">Ожидаемое время: {expected}</span>}
        </div>
      )}

      <div className="flow-card">
        <h2>Что дальше</h2>
        <ol className="next-steps">
          <li>Флорист собирает букет: это занимает до получаса.</li>
          {pickup ? <li>Когда заказ будет готов, он отобразится на странице заказа.</li> : <li>Курьер забирает заказ и везёт его по вашему адресу.</li>}
          <li>Статус заказа можно смотреть в любой момент: страница обновляется сама.</li>
        </ol>
      </div>

      <div className="flow-card">
        <h2>Ваш заказ</h2>
        <ul className="order-items">
          {order.items.map((item) => (
            <li key={item.product_id}>
              {item.name} × {item.quantity}
              <span>{formatPrice(item.unit_price * item.quantity)}</span>
            </li>
          ))}
        </ul>
        <p className="muted">
          {pickup ? "Самовывоз" : `Доставка${order.delivery_service ? ` (${order.delivery_service})` : ""}: ${order.address}`}
          {!pickup && ` · ${formatPrice(order.delivery_cost)}`}
        </p>
        {!pickup && details && <p className="muted">{details}</p>}
        {order.delivery_approximate && (
          <p className="muted">Стоимость доставки предварительная, при необходимости мы её уточним.</p>
        )}
        <p className="muted">Оплата: {paymentMethodLabel(order.payment_method)}</p>
        <p className="order-total">Оплачено: {formatPrice(order.total_price)}</p>
      </div>

      <div className="done-actions">
        <a className="btn btn-primary" href={`#/order/${id}`}>
          Отследить заказ
        </a>
        <a className="btn btn-ghost" href="#/catalog">
          Продолжить покупки
        </a>
        <a className="btn btn-ghost" href="#/orders">
          Мои заказы
        </a>
      </div>
    </section>
  );
}
