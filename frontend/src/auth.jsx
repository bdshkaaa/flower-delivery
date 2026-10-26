import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { api } from "./api.js";

const STORAGE_KEY = "flower-delivery-auth";
const AuthContext = createContext(null);

// localStorage может быть недоступен (приватный режим), поэтому всё в try/catch
function loadSaved() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && saved.token && saved.user) return saved;
  } catch {
    /* нет сохранённого входа */
  }
  return { token: null, user: null };
}

function save(value) {
  try {
    if (value.token) localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ничего страшного: вход просто не запомнится */
  }
}

export function AuthProvider({ children }) {
  const [auth, setAuth] = useState(loadSaved);

  const apply = useCallback((response) => {
    const value = { token: response.access_token, user: response.user };
    setAuth(value);
    save(value);
  }, []);

  const login = useCallback(
    async (email, password) => apply(await api("/login", { method: "POST", body: { email, password } })),
    [apply]
  );

  const register = useCallback(
    async (name, email, password) =>
      apply(await api("/register", { method: "POST", body: { name, email, password } })),
    [apply]
  );

  const logout = useCallback(async () => {
    const token = auth.token;
    setAuth({ token: null, user: null });
    save({ token: null, user: null });
    try {
      await api("/logout", { method: "POST", token });
    } catch {
      /* токен уже удалён у клиента, этого достаточно */
    }
  }, [auth.token]);

  const value = useMemo(
    () => ({ user: auth.user, token: auth.token, login, register, logout }),
    [auth, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
