import { useState } from "react";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { MAX_QUANTITY, useCart } from "../cart.jsx";
import AddressPicker from "../components/AddressPicker.jsx";
import DeliveryOptions from "../components/DeliveryOptions.jsx";
import ProductImage from "../components/ProductImage.jsx";
import { formatPrice, weightCategoryFor } from "../labels.js";
import { navigate } from "../router.js";

export default function CartPage() {
  const { items, count, subtotal, setQuantity, remove, clear, setFlash } = useCart();
  const { user, token } = useAuth();
  const [deliveryType, setDeliveryType] = useState("delivery");
  const [place, setPlace] = useState({ address: "", lat: null, lon: null });
  const [optionId, setOptionId] = useState(null);
  const [delivery, setDelivery] = useState({ status: "idle", options: [], selected: null });
  const [reloadKey, setReloadKey] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const weight = weightCategoryFor(count);
  const chosen = deliveryType === "delivery" ? delivery.selected : null;
  const deliveryCost = chosen ? chosen.cost : 0;
  const approximate = Boolean(chosen && (chosen.approximate || delivery.source === "fallback"));
  // заказ с доставкой нельзя оформить, пока нет доступного варианта
  const deliveryBlocked =
    deliveryType === "delivery" && (!chosen || delivery.status === "loading" || delivery.available === false);

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

  const addressMissing = deliveryType === "delivery" && place.address.trim().length < 3;

  async function submit(e) {
    e.preventDefault();
    if (addressMissing) {
      setError("Укажите адрес доставки");
      return;
    }
    if (deliveryBlocked) {
      setError("Выберите доступный вариант доставки или самовывоз");
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
          address: deliveryType === "delivery" ? place.address.trim() : null,
          lat: deliveryType === "delivery" ? place.lat : null,
          lon: deliveryType === "delivery" ? place.lon : null,
          delivery_option_id: chosen ? chosen.id : null,
        },
      });
      clear();
      setFlash(order);
      navigate("/orders");
    } catch (err) {
      setError(err.status === 401 ? "Сессия истекла. Войдите в аккаунт заново." : err.message);
      // вариант мог пропасть или цена измениться: обновляем расчёт
      if (err.status === 409 || err.status === 422) setReloadKey((k) => k + 1);
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
            <>
              <AddressPicker value={place} onChange={setPlace} />
              <DeliveryOptions
                place={place}
                weightCategory={weight}
                selectedId={optionId}
                onSelect={setOptionId}
                onState={setDelivery}
                reloadKey={reloadKey}
              />
            </>
          )}

          <dl className="totals">
            <div>
              <dt>Букеты ({count})</dt>
              <dd>{formatPrice(subtotal)}</dd>
            </div>
            <div>
              <dt>Доставка</dt>
              <dd>{deliveryType === "pickup" ? "Бесплатно" : chosen ? formatPrice(deliveryCost) : "—"}</dd>
            </div>
            <div className="totals-sum">
              <dt>Итого{approximate ? " (предварительно)" : ""}</dt>
              <dd>{formatPrice(subtotal + deliveryCost)}</dd>
            </div>
          </dl>

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}

          {user ? (
            <button className="btn btn-primary btn-block" disabled={submitting || deliveryBlocked}>
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
