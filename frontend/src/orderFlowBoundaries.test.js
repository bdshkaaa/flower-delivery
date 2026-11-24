import assert from "node:assert/strict";
import { test } from "node:test";

import { remainingSeconds, validateCard } from "./orderFlow.js";

test("таймер уменьшает остаток только после полной секунды", () => {
  const receivedAt = 10_000;
  assert.equal(remainingSeconds(2, receivedAt, receivedAt + 999), 2);
  assert.equal(remainingSeconds(2, receivedAt, receivedAt + 1_000), 1);
  assert.equal(remainingSeconds(2, receivedAt, receivedAt + 1_999), 1);
  assert.equal(remainingSeconds(2, receivedAt, receivedAt + 2_000), 0);
});

test("при смене года карта с декабрьским сроком истекает, январская действует", () => {
  const card = { number: "4242 4242 4242 4242", cvc: "012" };
  const december = new Date(2026, 11, 31, 23, 59);
  const january = new Date(2027, 0, 1, 0, 0);

  assert.deepEqual(validateCard({ ...card, expiry: "12/26" }, december), {});
  assert.deepEqual(validateCard({ ...card, expiry: "12/26" }, january), {
    expiry: "Срок действия карты истёк",
  });
  assert.deepEqual(validateCard({ ...card, expiry: "01/27" }, january), {});
});

test("проверка карты показывает ошибки во всех некорректных полях", () => {
  const errors = validateCard(
    { number: "4242", expiry: "00/27", cvc: "12a" },
    new Date(2026, 11, 31),
  );

  assert.deepEqual(Object.keys(errors).sort(), ["cvc", "expiry", "number"]);
});
