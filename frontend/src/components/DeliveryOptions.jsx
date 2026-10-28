import { useEffect, useState } from "react";
import { api } from "../api.js";
import { formatEta, formatPrice } from "../labels.js";

// Запрашивает у сервера варианты доставки всех служб и даёт выбрать один.
// onState получает { status, available, options, selected } для расчёта итога и блокировки кнопки.
export default function DeliveryOptions({ place, weightCategory, selectedId, onSelect, onState, reloadKey }) {
  const [state, setState] = useState({ status: "idle", options: [] });
  const address = place.address.trim();

  useEffect(() => {
    if (address.length < 3) {
      setState({ status: "idle", options: [] });
      return;
    }
    const controller = new AbortController();
    setState((s) => ({ ...s, status: "loading" }));
    const timer = setTimeout(async () => {
      try {
        const params = new URLSearchParams({ address, weight_category: weightCategory });
        if (place.lat != null && place.lon != null) {
          params.set("lat", place.lat);
          params.set("lon", place.lon);
        }
        const data = await api(`/delivery/options?${params}`, { signal: controller.signal });
        setState({ status: "ok", ...data });
      } catch (err) {
        if (err.name !== "AbortError") setState({ status: "error", options: [], message: err.message });
      }
    }, 500);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [address, place.lat, place.lon, weightCategory, reloadKey]);

  const options = state.options ?? [];
  // если выбранный вариант пропал (или ничего не выбрано), берём самый дешёвый
  const selected = options.find((o) => o.id === selectedId) ?? options[0] ?? null;

  useEffect(() => {
    onState({ status: state.status, available: state.available, options, selected, reason: state.reason, source: state.source });
    if (selected && selected.id !== selectedId) onSelect(selected.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state, selected?.id]);

  if (state.status === "idle") {
    return <p className="quote-line">Введите адрес или выберите точку на карте, чтобы увидеть варианты доставки.</p>;
  }
  if (state.status === "loading" && options.length === 0) {
    return <p className="quote-line" aria-live="polite">Считаем стоимость доставки…</p>;
  }
  if (state.status === "error") {
    return <p className="error" role="alert">Не удалось рассчитать доставку. {state.message}</p>;
  }
  if (!state.available) {
    return (
      <p className="error" role="alert">
        {state.reason} Вы можете выбрать самовывоз или другой адрес.
      </p>
    );
  }

  return (
    <fieldset className="delivery-options" aria-busy={state.status === "loading"}>
      <legend>Варианты доставки</legend>
      {options.map((option) => (
        <label key={option.id} className={option.id === selected?.id ? "option option-active" : "option"}>
          <input
            type="radio"
            name="delivery_option"
            value={option.id}
            checked={option.id === selected?.id}
            onChange={() => onSelect(option.id)}
          />
          <span className="option-main">
            <strong>{option.service}</strong>
            <span className="muted">
              {formatEta(option)}
              {option.approximate && " · предварительно"}
            </span>
          </span>
          <span className="option-price">{formatPrice(option.cost)}</span>
        </label>
      ))}
      {state.source === "fallback" && (
        <p className="hint">Службы доставки сейчас недоступны, показана предварительная стоимость. Мы уточним её после оформления.</p>
      )}
    </fieldset>
  );
}
