// Поводы для фильтра: значение уходит в API (category), подпись показывается покупателю
export const CATEGORIES = [
  { value: "birthday", label: "День рождения" },
  { value: "anniversary", label: "Годовщина" },
  { value: "wedding", label: "Свадьба" },
  { value: "thanks", label: "Благодарность" },
  { value: "love", label: "Признание" },
];

export const SORTS = [
  { value: "popularity", label: "Сначала популярные" },
  { value: "price_asc", label: "Сначала дешевле" },
  { value: "price_desc", label: "Сначала дороже" },
];

export function categoryLabel(value) {
  return CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

const priceFormat = new Intl.NumberFormat("ru-RU", {
  style: "currency",
  currency: "RUB",
  maximumFractionDigits: 0,
});

export function formatPrice(value) {
  return priceFormat.format(value);
}

// Весовая категория заказа для расчёта доставки. Правило то же, что на сервере:
// 1 букет — light, 2–3 — medium, 4 и больше — heavy
export function weightCategoryFor(totalQuantity) {
  if (totalQuantity <= 1) return "light";
  return totalQuantity <= 3 ? "medium" : "heavy";
}

export function pluralDays(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n} день`;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return `${n} дня`;
  return `${n} дней`;
}

export function orderStatusLabel(status) {
  return { created: "Создан", paid: "Оплачен", delivered: "Доставлен", cancelled: "Отменён" }[status] ?? status;
}

// Срок доставки: «за 3 часа» для доставки в день заказа, иначе «2 дня»
export function formatEta(option) {
  if (option.eta_hours) return `за ${option.eta_hours} ч.`;
  return pluralDays(option.eta_days);
}

// ---- Получатель и детали адреса ----

// «8 (900) 123-45-67», «+7 900 123 45 67», «9001234567» -> «+79001234567»; null, если номер неверный
export function normalizePhone(value) {
  let digits = String(value ?? "").replace(/\D/g, "");
  if (digits.length === 11 && (digits[0] === "7" || digits[0] === "8")) digits = digits.slice(1);
  return digits.length === 10 ? `+7${digits}` : null;
}

// Показывает номер как «+7 900 123-45-67»
export function formatPhone(value) {
  const phone = normalizePhone(value);
  if (!phone) return String(value ?? "");
  const d = phone.slice(2);
  return `+7 ${d.slice(0, 3)} ${d.slice(3, 6)}-${d.slice(6, 8)}-${d.slice(8)}`;
}

// Ошибки формы получателя: { поле: сообщение }. Пустой объект — всё верно.
export function validateRecipient({ name, phone, privateHouse, apartment }) {
  const errors = {};
  if (String(name ?? "").trim().length < 2) errors.name = "Укажите имя получателя";
  if (!normalizePhone(phone)) errors.phone = "Укажите телефон в формате +7 900 123-45-67";
  if (!privateHouse && !String(apartment ?? "").trim()) errors.apartment = "Укажите квартиру или отметьте «Частный дом»";
  return errors;
}

// «кв. 12, подъезд 2, этаж 5, домофон 12К» для истории заказов
export function formatAddressDetails(order) {
  const parts = [];
  if (order.private_house) parts.push("частный дом");
  else if (order.apartment) parts.push(`кв. ${order.apartment}`);
  if (order.entrance) parts.push(`подъезд ${order.entrance}`);
  if (order.floor) parts.push(`этаж ${order.floor}`);
  if (order.intercom) parts.push(`домофон ${order.intercom}`);
  return parts.join(", ");
}

// Название службы и тариф из «Курьер магазина: экспресс (за 3 часа)»
export function splitService(service) {
  const i = service.indexOf(": ");
  if (i < 0) return { group: service, tariff: "" };
  const tariff = service.slice(i + 2);
  return { group: service.slice(0, i), tariff: tariff.charAt(0).toUpperCase() + tariff.slice(1) };
}
