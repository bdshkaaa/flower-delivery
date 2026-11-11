import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { formatCardNumber, formatExpiry, validateCard } from "../orderFlow.js";
import { formatPrice } from "../labels.js";
import { navigate } from "../router.js";
import { useOrder } from "../useOrder.js";

// Симулятор оплаты: деньги не списываются, но проверки как у настоящего эквайринга.
export default function PaymentPage({ id }) {
  const { user, token } = useAuth();
  const { status, order, message, reload } = useOrder(id, token);
  const [method, setMethod] = useState("card");
  const [card, setCard] = useState({ number: "", expiry: "", cvc: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [paying, setPaying] = useState(false);

  // Заказ уже оплачен (например, открыли старую ссылку): показываем его статус
  useEffect(() => {
    if (order && order.status !== "created") navigate(`/order/${id}`);
  }, [order, id]);

  if (!user) {
    return (
      <section>
        <h1 className="page-title">Оплата</h1>
        <div className="notice">
          <p>Войдите, чтобы оплатить заказ</p>
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
        <h1 className="page-title">Оплата</h1>
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
  if (order.status !== "created") return null; // идёт переход на страницу статуса

  const set = (field, format) => (e) => {
    setCard({ ...card, [field]: format ? format(e.target.value) : e.target.value.replace(/\D/g, "").slice(0, 3) });
    setErrors({ ...errors, [field]: undefined });
    setError("");
  };

  async function pay(e) {
    e.preventDefault();
    if (method === "card") {
      const problems = validateCard(card);
      setErrors(problems);
      if (Object.keys(problems).length > 0) return;
    }
    setPaying(true);
    setError("");
    try {
      await api(`/orders/${id}/pay`, {
        method: "POST",
        token,
        body: method === "card" ? { method, card_number: card.number, expiry: card.expiry, cvc: card.cvc } : { method },
      });
      navigate(`/order/${id}/done`);
    } catch (err) {
      if (err.status === 409) navigate(`/order/${id}`); // уже оплачен в другой вкладке
      else setError(err.status === 401 ? "Сессия истекла. Войдите в аккаунт заново." : err.message);
    } finally {
      setPaying(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Оплата заказа №{order.number}</h1>
      <div className="checkout">
        <form className="summary" onSubmit={pay} aria-label="Оплата">
          <h2>Способ оплаты</h2>
          <div className="segmented" role="radiogroup" aria-label="Способ оплаты">
            {[
              ["card", "Банковская карта"],
              ["sbp", "СБП"],
            ].map(([value, label]) => (
              <label key={value} className={method === value ? "segment segment-active" : "segment"}>
                <input type="radio" name="method" value={value} checked={method === value} onChange={() => setMethod(value)} />
                {label}
              </label>
            ))}
          </div>

          {method === "card" ? (
            <>
              <div className="field">
                <label htmlFor="card-number">Номер карты</label>
                <input
                  id="card-number"
                  inputMode="numeric"
                  autoComplete="cc-number"
                  placeholder="0000 0000 0000 0000"
                  value={card.number}
                  onChange={set("number", formatCardNumber)}
                  aria-invalid={Boolean(errors.number)}
                />
                {errors.number && <small className="text-error" role="alert">{errors.number}</small>}
              </div>
              <div className="pay-row">
                <div className="field">
                  <label htmlFor="card-expiry">Срок действия</label>
                  <input
                    id="card-expiry"
                    inputMode="numeric"
                    autoComplete="cc-exp"
                    placeholder="ММ/ГГ"
                    value={card.expiry}
                    onChange={set("expiry", formatExpiry)}
                    aria-invalid={Boolean(errors.expiry)}
                  />
                  {errors.expiry && <small className="text-error" role="alert">{errors.expiry}</small>}
                </div>
                <div className="field">
                  <label htmlFor="card-cvc">CVC</label>
                  <input
                    id="card-cvc"
                    inputMode="numeric"
                    autoComplete="cc-csc"
                    placeholder="123"
                    type="password"
                    value={card.cvc}
                    onChange={set("cvc")}
                    aria-invalid={Boolean(errors.cvc)}
                  />
                  {errors.cvc && <small className="text-error" role="alert">{errors.cvc}</small>}
                </div>
              </div>
            </>
          ) : (
            <p className="pay-sbp">
              Нажмите «Оплатить», чтобы подтвердить платёж по СБП. В настоящем магазине здесь был бы QR-код для
              приложения вашего банка.
            </p>
          )}

          <p className="test-hint">
            <strong>Тестовая оплата:</strong> деньги не списываются. Карта 4242 4242 4242 4242 проходит, карта
            4000 0000 0000 0002 отклоняется банком. Срок и CVC любые.
          </p>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          <button className="btn btn-primary btn-block" disabled={paying}>
            {paying ? "Проводим платёж…" : `Оплатить ${formatPrice(order.total_price)}`}
          </button>
          <a className="pay-later" href={`#/order/${id}`}>
            Оплатить позже
          </a>
        </form>

        <aside className="summary" aria-label="Состав заказа">
          <h2>Ваш заказ</h2>
          <ul className="order-items">
            {order.items.map((item) => (
              <li key={item.product_id}>
                {item.name} × {item.quantity}
                <span>{formatPrice(item.unit_price * item.quantity)}</span>
              </li>
            ))}
          </ul>
          <dl className="totals">
            <div>
              <dt>Доставка</dt>
              <dd>{order.delivery_type === "pickup" ? "Бесплатно" : formatPrice(order.delivery_cost)}</dd>
            </div>
            <div className="totals-sum">
              <dt>К оплате{order.delivery_approximate ? " (предварительно)" : ""}</dt>
              <dd>{formatPrice(order.total_price)}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
