import { useEffect, useRef } from "react";
import { categoryLabel, formatPrice } from "../labels.js";
import ProductImage from "./ProductImage.jsx";

export default function ProductModal({ product, onClose }) {
  const closeRef = useRef(null);

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
          <p className="modal-note">Оформление заказа появится в следующей версии.</p>
        </div>
      </div>
    </div>
  );
}
