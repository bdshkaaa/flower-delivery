import { useState } from "react";
import { api } from "../api.js";
import MapPicker from "./MapPicker.jsx";

// Адрес можно ввести текстом (с поиском по карте) или выбрать точку на карте.
// value: { address, lat, lon }; lat и lon пустые, пока адрес введён вручную.
export default function AddressPicker({ value, onChange }) {
  const [mode, setMode] = useState("text");
  const [found, setFound] = useState({ status: "idle", items: [] });
  const [mapState, setMapState] = useState({ status: "idle", message: "" });

  const hasPoint = value.lat != null && value.lon != null;

  function typeAddress(e) {
    // ручной ввод сбрасывает ранее выбранную точку: цена считается по тексту
    onChange({ address: e.target.value, lat: null, lon: null });
    setFound({ status: "idle", items: [] });
  }

  async function search() {
    const query = value.address.trim();
    if (query.length < 3) return;
    setFound({ status: "loading", items: [] });
    try {
      const items = await api(`/geo/search?${new URLSearchParams({ q: query, limit: "5" })}`);
      setFound({ status: "ok", items });
    } catch (err) {
      setFound({ status: "error", items: [], message: err.message });
    }
  }

  async function pickOnMap({ lat, lon }) {
    // сразу показываем маркер, адрес подставится после ответа сервера
    onChange({ address: value.address, lat, lon });
    setMapState({ status: "loading", message: "" });
    try {
      const place = await api(`/geo/reverse?${new URLSearchParams({ lat, lon })}`);
      onChange({ address: place.label, lat: place.lat, lon: place.lon });
      setMapState({ status: "idle", message: "" });
    } catch (err) {
      setMapState({ status: "error", message: err.message });
      onChange({ address: "", lat: null, lon: null });
    }
  }

  return (
    <div className="address-picker">
      <div className="mode-tabs" role="tablist" aria-label="Способ выбора адреса">
        {[
          ["text", "Ввести адрес"],
          ["map", "Выбрать на карте"],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={mode === id}
            className={mode === id ? "mode-tab mode-tab-active" : "mode-tab"}
            onClick={() => setMode(id)}
          >
            {id === "map" ? "🗺️ " : "⌨️ "}
            {label}
          </button>
        ))}
      </div>

      {mode === "text" && (
        <div className="field">
          <label htmlFor="address">Адрес доставки</label>
          <div className="address-row">
            <input
              id="address"
              value={value.address}
              onChange={typeAddress}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  search();
                }
              }}
              placeholder="Город, улица, дом"
              autoComplete="street-address"
            />
            <button type="button" className="btn btn-ghost" onClick={search} disabled={value.address.trim().length < 3}>
              Найти
            </button>
          </div>
          <small>Можно просто ввести адрес или нажать «Найти» и выбрать из списка.</small>

          {found.status === "loading" && <small aria-live="polite">Ищем…</small>}
          {found.status === "error" && (
            <small className="text-error" role="alert">
              {found.message}
            </small>
          )}
          {found.status === "ok" && found.items.length === 0 && <small>Ничего не найдено. Уточните адрес.</small>}
          {found.items.length > 0 && (
            <ul className="suggestions" aria-label="Найденные адреса">
              {found.items.map((item) => (
                <li key={`${item.lat},${item.lon}`}>
                  <button
                    type="button"
                    onClick={() => {
                      onChange({ address: item.label, lat: item.lat, lon: item.lon });
                      setFound({ status: "idle", items: [] });
                    }}
                  >
                    {item.label}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {mode === "map" && (
        <div className="field">
          <MapPicker point={hasPoint ? { lat: value.lat, lon: value.lon } : null} onPick={pickOnMap} />
          <small aria-live="polite">
            {mapState.status === "loading" && "Определяем адрес…"}
            {mapState.status === "error" && <span className="text-error">{mapState.message}</span>}
            {mapState.status === "idle" &&
              (value.address ? `Выбрано: ${value.address}` : "Нажмите на карту в месте доставки.")}
          </small>
        </div>
      )}
    </div>
  );
}
