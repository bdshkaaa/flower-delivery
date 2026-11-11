// Unit-тесты оформления заказа. Запуск: npm test (встроенный раннер Node, зависимостей нет)
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formatCardNumber,
  formatCountdown,
  formatExpected,
  formatExpiry,
  isFinalStatus,
  parseOrderRoute,
  remainingSeconds,
  timelineSteps,
  validateCard,
} from "./orderFlow.js";

const ID = "3f2b8c1e-5a47-4d1b-9c3e-0a1b2c3d4e5f";

test("маршруты заказа распознаются, лишнее нет", () => {
  assert.deepEqual(parseOrderRoute(`/order/${ID}`), { id: ID, page: "status" });
  assert.deepEqual(parseOrderRoute(`/order/${ID}/pay`), { id: ID, page: "pay" });
  assert.deepEqual(parseOrderRoute(`/order/${ID}/done`), { id: ID, page: "done" });
  assert.equal(parseOrderRoute("/orders"), null);
  assert.equal(parseOrderRoute("/order/123"), null);
  assert.equal(parseOrderRoute(`/order/${ID}/hack`), null);
});

test("таймер уменьшается на прошедшие секунды и не уходит в минус", () => {
  assert.equal(remainingSeconds(600, 1000, 1000 + 45_000), 555);
  assert.equal(remainingSeconds(10, 0, 60_000), 0);
  assert.equal(remainingSeconds(null, 0, 5_000), null);
  assert.equal(remainingSeconds(100, 5_000, 1_000), 100); // часы «назад» не добавляют времени
});

test("обратный отсчёт читается по-человечески", () => {
  assert.equal(formatCountdown(0), "0 мин 00 сек");
  assert.equal(formatCountdown(125), "2 мин 05 сек");
  assert.equal(formatCountdown(3600 + 5 * 60), "1 ч 05 мин");
  assert.equal(formatCountdown(2 * 86400 + 3 * 3600 + 59), "2 д 3 ч");
  assert.equal(formatCountdown(-5), "0 мин 00 сек");
});

test("ожидаемое время: сегодня, завтра, дальше датой", () => {
  const now = new Date(2026, 10, 11, 15, 0);
  assert.match(formatExpected(new Date(2026, 10, 11, 18, 30), now), /^сегодня в 18:30$/);
  assert.match(formatExpected(new Date(2026, 10, 12, 9, 10), now), /^завтра в 09:10$/);
  assert.match(formatExpected(new Date(2026, 10, 14, 12, 0), now), /^14 ноября в 12:00$/);
});

test("этапы доставки: неоплаченный заказ ждёт оплаты", () => {
  const steps = timelineSteps({ delivery_type: "delivery", status: "created" });
  assert.deepEqual(steps.map((s) => s.state), ["done", "current", "todo", "todo", "todo"]);
  assert.equal(steps[1].key, "paid");
});

test("этапы доставки: сборка, в пути, доставлен", () => {
  const states = (status) => timelineSteps({ delivery_type: "delivery", status }).map((s) => s.state);
  assert.deepEqual(states("assembling"), ["done", "done", "current", "todo", "todo"]);
  assert.deepEqual(states("shipping"), ["done", "done", "done", "current", "todo"]);
  assert.deepEqual(states("delivered"), ["done", "done", "done", "done", "done"]);
});

test("этапы самовывоза короче и заканчиваются выдачей", () => {
  const steps = timelineSteps({ delivery_type: "pickup", status: "assembling" });
  assert.equal(steps.length, 4);
  assert.deepEqual(steps.map((s) => s.state), ["done", "done", "current", "todo"]);
  assert.ok(timelineSteps({ delivery_type: "pickup", status: "ready" }).every((s) => s.state === "done"));
});

test("конечные статусы", () => {
  assert.ok(isFinalStatus("delivered") && isFinalStatus("ready") && isFinalStatus("cancelled"));
  assert.ok(!isFinalStatus("shipping") && !isFinalStatus("created"));
});

test("номер карты и срок форматируются при вводе", () => {
  assert.equal(formatCardNumber("4242424242424242"), "4242 4242 4242 4242");
  assert.equal(formatCardNumber("4242-abc 42"), "4242 42");
  assert.equal(formatExpiry("1230"), "12/30");
  assert.equal(formatExpiry("12"), "12");
});

test("проверка карты совпадает с правилами сервера", () => {
  const now = new Date(2026, 10, 11);
  const ok = { number: "4242 4242 4242 4242", expiry: "12/30", cvc: "123" };
  assert.deepEqual(validateCard(ok, now), {});
  assert.ok(validateCard({ ...ok, number: "4242 4242 4242 4241" }, now).number); // не сходится контрольная сумма
  assert.ok(validateCard({ ...ok, number: "4242" }, now).number);
  assert.equal(validateCard({ ...ok, expiry: "10/26" }, now).expiry, "Срок действия карты истёк");
  assert.deepEqual(validateCard({ ...ok, expiry: "11/26" }, now), {}); // до конца месяца действует
  assert.ok(validateCard({ ...ok, expiry: "13/30" }, now).expiry);
  assert.ok(validateCard({ ...ok, cvc: "12" }, now).cvc);
});
