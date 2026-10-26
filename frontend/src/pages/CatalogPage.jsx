import { useEffect, useState } from "react";
import { api } from "../api.js";
import ProductCard from "../components/ProductCard.jsx";
import ProductModal from "../components/ProductModal.jsx";
import { CATEGORIES, SORTS } from "../labels.js";

const DEFAULT_FILTERS = { category: "", min: "", max: "", sort: "popularity" };

function buildQuery({ category, min, max, sort }) {
  const params = new URLSearchParams({ sort });
  if (category) params.set("category", category);
  if (min !== "") params.set("price_min", min);
  if (max !== "") params.set("price_max", max);
  return params.toString();
}

export default function CatalogPage() {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [state, setState] = useState({ status: "loading", items: [] });
  const [selected, setSelected] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const rangeInvalid =
    filters.min !== "" && filters.max !== "" && Number(filters.min) > Number(filters.max);
  const isFiltered = JSON.stringify(filters) !== JSON.stringify(DEFAULT_FILTERS);

  // Список обновляется без перезагрузки страницы при любом изменении фильтров.
  // Небольшая задержка не даёт слать запрос на каждую набранную цифру цены.
  useEffect(() => {
    if (rangeInvalid) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setState((s) => ({ ...s, status: "loading" }));
      try {
        const data = await api(`/goods?${buildQuery(filters)}`, { signal: controller.signal });
        setState({ status: "ok", items: data.items });
      } catch (err) {
        if (err.name !== "AbortError") setState({ status: "error", items: [], message: err.message });
      }
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [filters, rangeInvalid, reloadKey]);

  const set = (field) => (e) => setFilters({ ...filters, [field]: e.target.value });

  return (
    <section>
      <h1 className="page-title">Каталог букетов</h1>

      <form className="filters" onSubmit={(e) => e.preventDefault()} aria-label="Фильтры каталога">
        <div className="filter">
          <label htmlFor="category">Повод</label>
          <select id="category" value={filters.category} onChange={set("category")}>
            <option value="">Любой</option>
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        <div className="filter filter-price">
          <label htmlFor="min">Цена, ₽</label>
          <div className="price-range">
            <input id="min" type="number" min="0" inputMode="numeric" placeholder="от"
                   value={filters.min} onChange={set("min")} aria-label="Цена от" />
            <span aria-hidden="true">—</span>
            <input id="max" type="number" min="0" inputMode="numeric" placeholder="до"
                   value={filters.max} onChange={set("max")} aria-label="Цена до" />
          </div>
        </div>

        <div className="filter">
          <label htmlFor="sort">Сортировка</label>
          <select id="sort" value={filters.sort} onChange={set("sort")}>
            {SORTS.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {isFiltered && (
          <button type="button" className="btn btn-ghost" onClick={() => setFilters(DEFAULT_FILTERS)}>
            Сбросить
          </button>
        )}
      </form>

      {rangeInvalid && (
        <p className="error" role="alert">
          Минимальная цена больше максимальной
        </p>
      )}

      {!rangeInvalid && state.status === "loading" && (
        <div className="grid" aria-busy="true" aria-label="Загрузка">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="card skeleton" />
          ))}
        </div>
      )}

      {!rangeInvalid && state.status === "error" && (
        <div className="notice">
          <p>{state.message}</p>
          <button className="btn btn-primary" onClick={() => setReloadKey((k) => k + 1)}>
            Повторить
          </button>
        </div>
      )}

      {!rangeInvalid && state.status === "ok" && state.items.length === 0 && (
        <div className="notice">
          <p>Товары не найдены</p>
          <small>Попробуйте изменить повод или диапазон цены.</small>
          <button className="btn btn-ghost" onClick={() => setFilters(DEFAULT_FILTERS)}>
            Сбросить фильтры
          </button>
        </div>
      )}

      {!rangeInvalid && state.status === "ok" && state.items.length > 0 && (
        <>
          <p className="result-count">Найдено: {state.items.length}</p>
          <div className="grid">
            {state.items.map((p) => (
              <ProductCard key={p.id} product={p} onOpen={setSelected} />
            ))}
          </div>
        </>
      )}

      {selected && <ProductModal product={selected} onClose={() => setSelected(null)} />}
    </section>
  );
}
