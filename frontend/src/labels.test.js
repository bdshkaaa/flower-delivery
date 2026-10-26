// Unit-тесты чистых функций. Запуск: npm test (встроенный раннер Node, зависимостей нет)
import assert from "node:assert/strict";
import { test } from "node:test";
import { orderStatusLabel, pluralDays, weightCategoryFor } from "./labels.js";

test("весовая категория совпадает с правилом сервера", () => {
  assert.equal(weightCategoryFor(1), "light");
  assert.equal(weightCategoryFor(2), "medium");
  assert.equal(weightCategoryFor(3), "medium");
  assert.equal(weightCategoryFor(4), "heavy");
});

test("склонение дней", () => {
  assert.equal(pluralDays(1), "1 день");
  assert.equal(pluralDays(2), "2 дня");
  assert.equal(pluralDays(5), "5 дней");
  assert.equal(pluralDays(11), "11 дней");
  assert.equal(pluralDays(21), "21 день");
});

test("неизвестный статус заказа показывается как есть", () => {
  assert.equal(orderStatusLabel("created"), "Создан");
  assert.equal(orderStatusLabel("weird"), "weird");
});
