import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { MAX_QUANTITY, useCart } from "../cart.jsx";
import ProductImage from "../components/ProductImage.jsx";
import { formatPrice, pluralDays, weightCategoryFor } from "../labels.js";
import { navigate } from "../router.js";

// Стоимость доставки запрашиваем у сервера, как только введён адрес
function useDeliveryQuote(enabled, address, weightCategory) {
  const [quote, setQuote] = useState({ status: "idle" });

  useEffect(() => {
    if (!enabled || address.trim().length < 3) {
      setQuote({ status: "idle" });
      return;
    }
    const controller = new AbortController();
    setQuote({ status: "loading" });
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ address: address.trim(), weight_category: weightCategory });
        const data = await api(`/delivery/quote?${params}`, { signal: controller.signal });
        setQuote({ status: "ok", data });
      } catch (err) {
        if (err.name !== "AbortError") setQuote({ status: "error" });
      }
    }, 500);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [enabled, address, weightCategory]);

  return quote;
}

export default function CartPage() {
  const { items, count, subtotal, setQuantity, remove, clear, setFlash } = useCart();
  const { user, token } = useAuth();
  const [deliveryType, setDeliveryType] = useState("delivery");
  const [address, setAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const quote = useDeliveryQuote(deliveryType === "delivery", address, weightCategoryFor(count));
  const deliveryCost = deliveryType === "delivery" && quote.status === "ok" ? quote.data.cost : 0;
  const approximate =
    deliveryType === "delivery" && (quote.status !== "ok" || quote.data.approximate);

  if (items.length === 0) {
    return (
      <section>
        <h1 className="page-title">Корзина</h1>
        <div className="notice">
          <p>В корзине пока пусто</p>
          <small>Выберите букет в каталоге.</small>
          <a className="btn btn-primary" href="#/catalog">
            В каталог
          </a>
        </div>
      </section>
    );
  }

  const addressMissing = deliveryType === "delivery" && address.trim().length < 3;

  async function submit(e) {
    e.preventDefault();
    if (addressMissing) {
      setError("Укажите адрес доставки");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const order = await api("/orders", {
        method: "POST",
        token,
        body: {
          items: items.map((i) => ({ product_id: i.id, quantity: i.quantity })),
          delivery_type: deliveryType,
          address: deliveryType === "delivery" ? address.trim() : null,
        },
      });
      clear();
      setFlash(order);
      navigate("/orders");
    } catch (err) {
      setError(err.status === 401 ? "Сессия истекла. Войдите в аккаунт заново." : err.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Корзина</h1>
      <div className="checkout">
        <ul className="cart-list" aria-label="Состав заказа">
          {items.map((item) => (
            <li key={item.id} className="cart-item">
              <ProductImage src={item.image_url} alt={item.name} className="cart-image" />
              <div className="cart-info">
                <strong>{item.name}</strong>
                <span className="muted">{formatPrice(item.price)}</span>
              </div>
              <div className="stepper" role="group" aria-label={`Количество: ${item.name}`}>
                <button type="button" onClick={() => setQuantity(item.id, item.quantity - 1)} aria-label="Меньше">
                  −
                </button>
                <span aria-live="polite">{item.quantity}</span>
                <button
                  type="button"
                  onClick={() => setQuantity(item.id, item.quantity + 1)}
                  disabled={item.quantity >= MAX_QUANTITY}
                  aria-label="Больше"
                >
                  +
                </button>
              </div>
              <span className="cart-line-price">{formatPrice(item.price * item.quantity)}</span>
              <button type="button" className="icon-btn" onClick={() => remove(item.id)} aria-label={`Удалить: ${item.name}`}>
                ×
              </button>
            </li>
          ))}
        </ul>

        <form className="summary" onSubmit={submit} aria-label="Оформление заказа">
          <h2>Получение</h2>
          <div className="segmented" role="radiogroup" aria-label="Способ получения">
            {[
              ["delivery", "Доставка"],
              ["pickup", "Самовывоз"],
            ].map(([value, label]) => (
              <label key={value} className={deliveryType === value ? "segment segment-active" : "segment"}>
                <input
                  type="radio"
                  name="delivery_type"
                  value={value}
                  checked={deliveryType === value}
                  onChange={() => setDeliveryType(value)}
                />
                {label}
              </label>
            ))}
          </div>

          {deliveryType === "delivery" && (
            <div className="field">
              <label htmlFor="address">Адрес доставки</label>
              <input
                id="address"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Город, улица, дом"
                autoComplete="street-address"
              />
              <small className="quote-line" aria-live="polite">
                {quote.status === "loading" && "Считаем стоимость доставки…"}
                {quote.status === "ok" &&
                  `Доставка: ${formatPrice(quote.data.cost)}, срок — ${pluralDays(quote.data.eta_days)}`}
                {quote.status === "error" && "Не удалось рассчитать доставку. Заказ можно оформить, стоимость уточним."}
                {quote.status === "idle" && "Введите адрес, чтобы увидеть стоимость и срок."}
              </small>
            </div>
          )}

          <dl className="totals">
            <div>
              <dt>Букеты ({count})</dt>
              <dd>{formatPrice(subtotal)}</dd>
            </div>
            <div>
              <dt>Доставка</dt>
              <dd>{deliveryType === "pickup" ? "Бесплатно" : quote.status === "ok" ? formatPrice(deliveryCost) : "—"}</dd>
            </div>
            <div className="totals-sum">
              <dt>Итого{approximate ? " (предварительно)" : ""}</dt>
              <dd>{formatPrice(subtotal + deliveryCost)}</dd>
            </div>
          </dl>

          {approximate && quote.status === "ok" && (
            <p className="hint">
              Стоимость доставки предварительная: сервис расчёта сейчас недоступен. Мы уточним её после оформления.
            </p>
          )}

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          {user ? (
            <button className="btn btn-primary btn-block" disabled={submitting}>
              {submitting ? "Оформляем…" : "Оформить заказ"}
            </button>
          ) : (
            <div className="login-prompt">
              <p>Чтобы оформить заказ, войдите в аккаунт. Корзина сохранится.</p>
              <a className="btn btn-primary btn-block" href="#/login">
                Войти или зарегистрироваться
              </a>
            </div>
          )}
        </form>
      </div>
    </section>
  );
}
