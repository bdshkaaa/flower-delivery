import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";

// Центр России и масштаб страны: пока точка не выбрана, показываем всю карту
const RUSSIA = [58, 60];
const markerIcon = L.divIcon({ className: "map-pin", html: "📍", iconSize: [28, 28], iconAnchor: [14, 26] });

// Карта OpenStreetMap (Leaflet). Клик по карте отдаёт координаты наверх через onPick.
export default function MapPicker({ point, onPick }) {
  const box = useRef(null);
  const map = useRef(null);
  const marker = useRef(null);
  const pickRef = useRef(onPick);
  pickRef.current = onPick;

  useEffect(() => {
    const instance = L.map(box.current, { worldCopyJump: true }).setView(
      point ? [point.lat, point.lon] : RUSSIA,
      point ? 13 : 4
    );
    L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(instance);
    instance.on("click", (e) => pickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }));
    map.current = instance;
    return () => {
      instance.remove();
      map.current = null;
      marker.current = null;
    };
    // карта создаётся один раз; выбранная точка обновляется отдельным эффектом ниже
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!map.current) return;
    if (!point) {
      marker.current?.remove();
      marker.current = null;
      return;
    }
    const latlng = [point.lat, point.lon];
    if (marker.current) marker.current.setLatLng(latlng);
    else marker.current = L.marker(latlng, { icon: markerIcon, keyboard: false }).addTo(map.current);
  }, [point]);

  return <div ref={box} className="map" role="application" aria-label="Карта: нажмите на место доставки" />;
}
