import { useEffect, useState } from "react";

// Простая маршрутизация по адресу после #: #/login, #/catalog и т.д.
// Работает без дополнительных библиотек и без настройки сервера.
function currentPath() {
  return window.location.hash.replace(/^#/, "") || "/";
}

export function useRoute() {
  const [path, setPath] = useState(currentPath);
  useEffect(() => {
    const onChange = () => setPath(currentPath());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return path;
}

export function navigate(path) {
  window.location.hash = path;
}
