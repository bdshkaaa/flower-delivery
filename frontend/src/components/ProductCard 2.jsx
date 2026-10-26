import { categoryLabel, formatPrice } from "../labels.js";
import ProductImage from "./ProductImage.jsx";

export default function ProductCard({ product, onOpen }) {
  return (
    <article className="card">
      <button className="card-button" onClick={() => onOpen(product)} aria-label={`Открыть: ${product.name}`}>
        <ProductImage src={product.image_url} alt={product.name} className="card-image" />
        <div className="card-body">
          <span className="tag">{categoryLabel(product.category)}</span>
          <h3 className="card-title">{product.name}</h3>
          <p className="card-price">{formatPrice(product.price)}</p>
        </div>
      </button>
    </article>
  );
}
