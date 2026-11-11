// Чистая логика оформления: маршруты заказа, таймер, этапы доставки, проверка карты.
// Без React и без запросов, поэтому покрыта unit-тестами (orderFlow.test.js).

// ---- Маршруты: #/order/<id>/pay, #/order/<id>/done, #/order/<id> ----
const ORDER_ROUTE = /^\/order\/([0-9a-f-]{36})(?:\/(pay|done))?\/?$/i;

export function parseOrderRoute(path) {
  const match = ORDER_ROUTE.exec(path ?? "");
  if (!match) return null;
  return { id: match[1], page: match[2] ?? "status" };
}

// ---- Таймер ----
// Сервер присылает seconds_left на момент ответа; дальше считаем на клиенте, без лишних запросов
export function remainingSeconds(secondsLeft, receivedAtMs, nowMs) {
  if (secondsLeft == null) return null;
  const passed = Math.max(0, Math.floor((nowMs - receivedAtMs) / 1000));
  return Math.max(0, secondsLeft - passed);
}

// 7500 -> «2 ч 05 мин»; 600 -> «10 мин 00 сек»; 200000 -> «2 д 7 ч»
export function formatCountdown(totalSeconds) {
  const s = Math.max(0, Math.floor(totalSeconds));
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = s % 60;
  const two = (n) => String(n).padStart(2, "0");
  if (days > 0) return `${days} д ${hours} ч`;
  if (hours > 0) return `${hours} ч ${two(minutes)} мин`;
  return `${minutes} мин ${two(seconds)} сек`;
}

const timeFormat = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });
const dayFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long" });

function startOfDay(date) {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

// «сегодня в 18:30», «завтра в 09:10», «13 ноября в 12:00»
export function formatExpected(expectedAt, now = new Date()) {
  const date = new Date(expectedAt);
  const dayDiff = Math.round((startOfDay(date) - startOfDay(now)) / 86400000);
  const time = timeFormat.format(date);
  if (dayDiff === 0) return `сегодня в ${time}`;
  if (dayDiff === 1) return `завтра в ${time}`;
  return `${dayFormat.format(date)} в ${time}`;
}

// ---- Этапы заказа ----
const DELIVERY_STEPS = [
  ["placed", "Заказ оформлен"],
  ["paid", "Заказ оплачен"],
  ["assembling", "Флорист собирает букет"],
  ["shipping", "Курьер в пути"],
  ["delivered", "Заказ доставлен"],
];
const PICKUP_STEPS = [
  ["placed", "Заказ оформлен"],
  ["paid", "Заказ оплачен"],
  ["assembling", "Флорист собирает букет"],
  ["ready", "Готов к выдаче"],
];

// Номер текущего этапа для каждого статуса заказа
const STEP_OF_STATUS = { created: 1, paid: 2, assembling: 2, shipping: 3, delivered: 4, ready: 3 };

export function isFinalStatus(status) {
  return status === "delivered" || status === "ready" || status === "cancelled";
}

// [{ key, label, state: "done" | "current" | "todo" }]. Пока заказ не оплачен, текущий этап — оплата.
export function timelineSteps(order) {
  const steps = order.delivery_type === "pickup" ? PICKUP_STEPS : DELIVERY_STEPS;
  const current = STEP_OF_STATUS[order.status] ?? 0;
  const finished = order.status === "delivered" || order.status === "ready";
  return steps.map(([key, label], i) => ({
    key,
    label,
    state: finished || i < current ? "done" : i === current ? "current" : "todo",
  }));
}

export function paymentMethodLabel(method) {
  return { card: "Банковская карта", sbp: "СБП" }[method] ?? "—";
}

// ---- Карта (симулятор оплаты) ----
export function formatCardNumber(value) {
  const digits = String(value ?? "").replace(/\D/g, "").slice(0, 19);
  return digits.replace(/(.{4})/g, "$1 ").trim();
}

// «1230» -> «12/30»
export function formatExpiry(value) {
  const digits = String(value ?? "").replace(/\D/g, "").slice(0, 4);
  return digits.length > 2 ? `${digits.slice(0, 2)}/${digits.slice(2)}` : digits;
}

function luhnValid(digits) {
  let sum = 0;
  [...digits].reverse().forEach((ch, i) => {
    let n = Number(ch);
    if (i % 2 === 1) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
  });
  return sum % 10 === 0;
}

// Те же правила, что на сервере (payments.py). Возвращает { поле: сообщение }; пустой объект — всё верно.
export function validateCard({ number, expiry, cvc }, now = new Date()) {
  const errors = {};
  const digits = String(number ?? "").replace(/\D/g, "");
  if (digits.length < 13 || digits.length > 19 || !luhnValid(digits)) errors.number = "Проверьте номер карты";

  const match = /^(\d{2})\/(\d{2})$/.exec(String(expiry ?? ""));
  if (!match || Number(match[1]) < 1 || Number(match[1]) > 12) {
    errors.expiry = "Укажите срок в формате ММ/ГГ";
  } else {
    const year = 2000 + Number(match[2]);
    const month = Number(match[1]);
    if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
      errors.expiry = "Срок действия карты истёк";
    }
  }

  if (!/^\d{3}$/.test(String(cvc ?? ""))) errors.cvc = "Три цифры на обороте карты";
  return errors;
}
