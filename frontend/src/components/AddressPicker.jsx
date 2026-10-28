import { useEffect, useId, useRef, useState } from "react";
import { api } from "../api.js";

const MIN_CHARS = 3;
const PAUSE_MS = 350; // ждём паузу в наборе, чтобы не спрашивать подсказки на каждую букву

// Поле адреса с подсказками: пока человек печатает, под полем раскрывается список адресов
// (только в зоне доставки). Выбранная подсказка даёт точные координаты.
// value: { address, lat, lon }; lat и lon пустые, пока адрес введён вручную.
export default function AddressPicker({ value, onChange }) {
  const listId = useId();
  const timer = useRef(null);
  const request = useRef(null);
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [status, setStatus] = useState("idle"); // idle | loading | ok | error

  useEffect(
    () => () => {
      clearTimeout(timer.current);
      request.current?.abort();
    },
    []
  );

  function close() {
    setOpen(false);
    setActive(-1);
  }

  function schedule(text) {
    clearTimeout(timer.current);
    request.current?.abort();
    if (text.trim().length < MIN_CHARS) {
      setItems([]);
      setStatus("idle");
      close();
      return;
    }
    setStatus("loading");
    timer.current = setTimeout(async () => {
      const controller = new AbortController();
      request.current = controller;
      try {
        const found = await api(`/geo/search?${new URLSearchParams({ q: text.trim(), limit: "5" })}`, {
          signal: controller.signal,
        });
        setItems(found);
        setStatus("ok");
        setOpen(true);
        setActive(-1);
      } catch (err) {
        if (err.name === "AbortError") return;
        setItems([]);
        setStatus("error");
        close();
      }
    }, PAUSE_MS);
  }

  function type(e) {
    // ручной ввод сбрасывает выбранную подсказку: дальше адрес считается по тексту
    onChange({ address: e.target.value, lat: null, lon: null });
    schedule(e.target.value);
  }

  function choose(item) {
    clearTimeout(timer.current);
    request.current?.abort();
    onChange({ address: item.label, lat: item.lat, lon: item.lon });
    setItems([]);
    setStatus("idle");
    close();
  }

  function keys(e) {
    if (!open || items.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % items.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i <= 0 ? items.length - 1 : i - 1));
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      choose(items[active]);
    } else if (e.key === "Escape") {
      close();
    }
  }

  const showList = open && items.length > 0;

  return (
    <div className="field address-picker">
      <label htmlFor="address">Адрес доставки</label>
      <div className="combo">
        <input
          id="address"
          value={value.address}
          onChange={type}
          onKeyDown={keys}
          onFocus={() => items.length > 0 && setOpen(true)}
          onBlur={close}
          placeholder="Санкт-Петербург, Невский проспект 1"
          autoComplete="off"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        />
        {showList && (
          <ul className="suggestions" id={listId} role="listbox" aria-label="Подходящие адреса">
            {items.map((item, i) => (
              <li
                key={`${item.lat},${item.lon}`}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                className={i === active ? "suggestion suggestion-active" : "suggestion"}
                // mousedown раньше blur: иначе список закроется до клика
                onMouseDown={(e) => {
                  e.preventDefault();
                  choose(item);
                }}
              >
                {item.label}
              </li>
            ))}
          </ul>
        )}
      </div>
      <small aria-live="polite">
        {status === "loading" && "Ищем адреса…"}
        {status === "ok" && items.length === 0 && "Подходящих адресов нет. Проверьте написание или введите адрес полностью."}
        {status === "error" && "Подсказки недоступны, введите адрес полностью."}
        {(status === "idle" || (status === "ok" && items.length > 0)) &&
          "Начните вводить адрес и выберите его из списка. Доставляем по Санкт-Петербургу и Ленинградской области."}
      </small>
    </div>
  );
}
