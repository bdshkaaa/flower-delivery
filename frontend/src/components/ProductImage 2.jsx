import { useState } from "react";

// Картинка букета; если файла нет или он не загрузился — аккуратная заглушка
export default function ProductImage({ src, alt, className = "" }) {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return (
      <div className={`image-placeholder ${className}`} role="img" aria-label={alt}>
        🌸
      </div>
    );
  }
  return (
    <img className={className} src={src} alt={alt} loading="lazy" onError={() => setFailed(true)} />
  );
}
