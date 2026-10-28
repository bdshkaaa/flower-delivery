// Unit-тесты чистых функций. Запуск: npm test (встроенный раннер Node, зависимостей нет)
import assert from "node:assert/strict";
import { test } from "node:test";
import {
  formatAddressDetails,
  formatPhone,
  normalizePhone,
  orderStatusLabel,
  pluralDays,
  splitService,
  validateRecipient,
  weightCategoryFor,
} from "./labels.js";

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

test("телефон приводится к виду +7XXXXXXXXXX", () => {
  assert.equal(normalizePhone("8 (900) 123-45-67"), "+79001234567");
  assert.equal(normalizePhone("+7 900 123 45 67"), "+79001234567");
  assert.equal(normalizePhone("9001234567"), "+79001234567");
  assert.equal(normalizePhone("12345"), null);
  assert.equal(normalizePhone(""), null);
  assert.equal(formatPhone("89001234567"), "+7 900 123-45-67");
});

test("проверка формы получателя", () => {
  const ok = { name: "Анна", phone: "+7 900 123-45-67", apartment: "12", privateHouse: false };
  assert.deepEqual(validateRecipient(ok), {});
  assert.deepEqual(Object.keys(validateRecipient({ ...ok, name: "А", phone: "1" })).sort(), ["name", "phone"]);
  assert.ok(validateRecipient({ ...ok, apartment: " " }).apartment);
  assert.deepEqual(validateRecipient({ ...ok, apartment: "", privateHouse: true }), {});
});

test("детали адреса в истории заказов", () => {
  assert.equal(formatAddressDetails({ apartment: "12", entrance: "2", floor: "5", intercom: "12К" }), "кв. 12, подъезд 2, этаж 5, домофон 12К");
  assert.equal(formatAddressDetails({ private_house: true }), "частный дом");
  assert.equal(formatAddressDetails({}), "");
});

test("служба и тариф разделяются по двоеточию", () => {
  assert.deepEqual(splitService("Курьер магазина: экспресс (за 3 часа)"), { group: "Курьер магазина", tariff: "Экспресс (за 3 часа)" });
  assert.deepEqual(splitService("Достависта: курьер"), { group: "Достависта", tariff: "Курьер" });
  assert.deepEqual(splitService("СДЭК"), { group: "СДЭК", tariff: "" });
});
