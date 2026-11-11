import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { isFinalStatus, remainingSeconds } from "./orderFlow.js";

const POLL_MS = 10_000;

// Загружает заказ по id. С poll: true обновляет его каждые 10 секунд, пока заказ не доставлен,
// так страница статуса сама показывает новый этап без перезагрузки.
export function useOrder(id, token, { poll = false } = {}) {
  const [state, setState] = useState({ status: "loading", order: null, receivedAt: 0, message: "" });
  const [reloadKey, setReloadKey] = useState(0);
  const reload = useCallback(() => setReloadKey((k) => k + 1), []);

  useEffect(() => {
    if (!token) return undefined;
    let stopped = false;
    let timer;
    const controller = new AbortController();

    async function load() {
      try {
        const order = await api(`/orders/${id}`, { token, signal: controller.signal });
        if (stopped) return;
        setState({ status: "ok", order, receivedAt: Date.now(), message: "" });
        if (poll && !isFinalStatus(order.status)) timer = setTimeout(load, POLL_MS);
      } catch (err) {
        if (stopped || err.name === "AbortError") return;
        setState((s) => ({ ...s, status: err.status === 404 ? "notfound" : "error", message: err.message }));
        // при временном сбое связи продолжаем опрашивать, пока открыта страница
        if (poll && err.status !== 404 && err.status !== 401) timer = setTimeout(load, POLL_MS);
      }
    }

    load();
    return () => {
      stopped = true;
      clearTimeout(timer);
      controller.abort();
    };
  }, [id, token, poll, reloadKey]);

  return { ...state, reload };
}

// Секунды до доставки, обновляются раз в секунду. null, пока заказ не оплачен.
export function useCountdown(secondsLeft, receivedAt) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (secondsLeft == null) return undefined;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [secondsLeft, receivedAt]);
  return remainingSeconds(secondsLeft, receivedAt, now);
}
