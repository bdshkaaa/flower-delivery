import { useEffect, useRef } from "react";
import { useAuth } from "../auth.jsx";
import OrderTimeline from "../components/OrderTimeline.jsx";
import { formatAddressDetails, formatPhone, formatPrice, orderStatusLabel } from "../labels.js";
import { formatCountdown, formatExpected, isFinalStatus, paymentMethodLabel } from "../orderFlow.js";
import { useCountdown, useOrder } from "../useOrder.js";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "long", timeStyle: "short" });

const STAGE_TEXT = {
  assembling: "Флорист собирает ваш букет",
  shipping: "Курьер уже в пути",
  delivered: "Заказ доставлен. Спасибо, что выбрали нас!",
  ready: "Заказ готов к выдаче. Ждём вас в магазине!",
  cancelled: "Заказ отменён",
};

// Страница статуса: этапы, таймер до доставки, состав. Обновляется сама каждые 10 секунд.
export default function OrderStatusPage({ id }) {
  const { user, token } = useAuth();
  const { status, order, receivedAt, message, reload } = useOrder(id, token, { poll: true });
  const left = useCountdown(order?.seconds_left ?? null, receivedAt);

  // Таймер дошёл до нуля, а сервер ещё не прислал финальный статус: спрашиваем сразу, не ждём опроса
  const refreshedFor = useRef(0);
  useEffect(() => {
    if (order && left === 0 && !isFinalStatus(order.status) && refreshedFor.current !== receivedAt) {
      refreshedFor.current = receivedAt;
      reload();
    }
  }, [left, order, receivedAt, reload]);

  if (!user) {
    return (
      <section>
        <h1 className="page-title">Статус заказа</h1>
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
        <h1 className="page-title">Статус заказа</h1>
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

  const pickup = order.delivery_type === "pickup";
  const unpaid = order.status === "created";
  const final = isFinalStatus(order.status);
  const expected = order.expected_at && left != null && left > 0 ? formatExpected(new Date(Date.now() + left * 1000)) : null;
  const details = [formatAddressDetails(order), order.recipient_name && `получатель ${order.recipient_name}`,
    order.recipient_phone && formatPhone(order.recipient_phone)].filter(Boolean).join(" · ");

  return (
    <section className="status-page">
      <div className="status-head">
        <h1 className="page-title">Заказ №{order.number}</h1>
        <span className="tag">{orderStatusLabel(order.status)}</span>
      </div>
      <p className="muted">Оформлен {dateFormat.format(new Date(order.created_at))}</p>

      {status === "error" && (
        <p className="error" role="alert">
          Не удалось обновить статус. Показываем последние данные.
        </p>
      )}

      {unpaid ? (
        <div className="eta-card">
          <strong>Заказ ждёт оплаты</strong>
          <span className="muted">Пока он не оплачен, мы не начинаем сборку.</span>
          <a className="btn btn-primary" href={`#/order/${id}/pay`}>
            Оплатить {formatPrice(order.total_price)}
          </a>
        </div>
      ) : final ? (
        <div className="eta-card eta-final" role="status">
          <strong>{STAGE_TEXT[order.status]}</strong>
        </div>
      ) : (
        <div className="eta-card">
          <span className="muted" aria-live="polite">
            {STAGE_TEXT[order.status]}
          </span>
          <span className="muted">{pickup ? "Будет готов через" : "Будет у вас через"}</span>
          <strong className="eta-value" role="timer">
            {formatCountdown(left ?? order.seconds_left ?? 0)}
          </strong>
          {expected && <span className="muted">Ожидаемое время: {expected}</span>}
        </div>
      )}

      {order.status !== "cancelled" && (
        <div className="flow-card">
          <h2>Этапы</h2>
          <OrderTimeline order={order} />
        </div>
      )}

      <div className="flow-card">
        <h2>Состав и доставка</h2>
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
          {!pickup && ` · ${formatPrice(order.delivery_cost)}${order.delivery_approximate ? " (предварительно)" : ""}`}
        </p>
        {!pickup && details && <p className="muted">{details}</p>}
        {order.courier_comment && <p className="muted">Комментарий курьеру: «{order.courier_comment}»</p>}
        {order.paid_at && (
          <p className="muted">
            Оплата: {paymentMethodLabel(order.payment_method)}, {dateFormat.format(new Date(order.paid_at))}
          </p>
        )}
        <p className="order-total">Итого: {formatPrice(order.total_price)}</p>
      </div>

      <div className="done-actions">
        <a className="btn btn-ghost" href="#/orders">
          Мои заказы
        </a>
        <a className="btn btn-ghost" href="#/catalog">
          В каталог
        </a>
      </div>
    </section>
  );
}
