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
