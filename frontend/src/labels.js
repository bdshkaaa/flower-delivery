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
