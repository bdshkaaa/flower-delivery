import { useEffect, useRef, useState } from "react";
import { MAX_QUANTITY, useCart } from "../cart.jsx";
import { categoryLabel, formatPrice } from "../labels.js";
import ProductImage from "./ProductImage.jsx";

export default function ProductModal({ product, onClose }) {
  const closeRef = useRef(null);
  const { add } = useCart();
  const [quantity, setQuantity] = useState(1);
  const [added, setAdded] = useState(false);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previous;
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <button ref={closeRef} className="modal-close" onClick={onClose} aria-label="Закрыть">
          ×
        </button>
        <ProductImage src={product.image_url} alt={product.name} className="modal-image" />
        <div className="modal-body">
          <span className="tag">{categoryLabel(product.category)}</span>
          <h2 id="modal-title">{product.name}</h2>
          {product.description && <p className="modal-description">{product.description}</p>}
          <p className="modal-price">{formatPrice(product.price)}</p>
          <div className="modal-buy">
            <div className="stepper" role="group" aria-label="Количество">
              <button type="button" onClick={() => setQuantity((q) => Math.max(1, q - 1))} aria-label="Меньше">
                −
              </button>
              <span aria-live="polite">{quantity}</span>
              <button type="button" onClick={() => setQuantity((q) => Math.min(MAX_QUANTITY, q + 1))} aria-label="Больше">
                +
              </button>
            </div>
            <button
              className="btn btn-primary"
              onClick={() => {
                add(product, quantity);
                setAdded(true);
              }}
            >
              В корзину
            </button>
          </div>
          {added && (
            <p className="modal-added" role="status">
              Добавлено в корзину. <a href="#/cart" onClick={onClose}>Перейти в корзину</a>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
