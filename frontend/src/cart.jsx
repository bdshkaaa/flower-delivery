import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "flower-delivery-cart";
const MAX_QUANTITY = 20;
const CartContext = createContext(null);

// Корзина хранится в браузере, поэтому переживает перезагрузку и вход в аккаунт.
// localStorage может быть недоступен, поэтому всё в try/catch
function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (Array.isArray(saved)) return saved.filter((i) => i && i.id && i.quantity > 0);
  } catch {
    /* пустая корзина */
  }
  return [];
}

export function CartProvider({ children }) {
  const [items, setItems] = useState(load);
  // Сообщение «заказ оформлен» для страницы истории заказов
  const [flash, setFlash] = useState(null);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
    } catch {
      /* корзина просто не запомнится */
    }
  }, [items]);

  const add = useCallback((product, quantity = 1) => {
    setItems((current) => {
      const existing = current.find((i) => i.id === product.id);
      if (existing) {
        return current.map((i) =>
          i.id === product.id ? { ...i, quantity: Math.min(MAX_QUANTITY, i.quantity + quantity) } : i
        );
      }
      const { id, name, price, image_url } = product;
      return [...current, { id, name, price, image_url, quantity: Math.min(MAX_QUANTITY, quantity) }];
    });
  }, []);

  const setQuantity = useCallback((id, quantity) => {
    setItems((current) =>
      quantity <= 0
        ? current.filter((i) => i.id !== id)
        : current.map((i) => (i.id === id ? { ...i, quantity: Math.min(MAX_QUANTITY, quantity) } : i))
    );
  }, []);

  const remove = useCallback((id) => setItems((c) => c.filter((i) => i.id !== id)), []);
  const clear = useCallback(() => setItems([]), []);

  const value = useMemo(
    () => ({
      items,
      count: items.reduce((sum, i) => sum + i.quantity, 0),
      subtotal: items.reduce((sum, i) => sum + i.price * i.quantity, 0),
      add,
      setQuantity,
      remove,
      clear,
      flash,
      setFlash,
    }),
    [items, add, setQuantity, remove, clear, flash]
  );
  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  return useContext(CartContext);
}

export { MAX_QUANTITY };
