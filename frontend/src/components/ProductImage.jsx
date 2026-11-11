import { useEffect, useState } from "react";

// Фотография букета. Если файла .jpg нет, пробуем рисованную картинку .svg с тем же именем,
// а если и её нет, показываем аккуратную заглушку.
export default function ProductImage({ src, alt, className = "" }) {
  const [current, setCurrent] = useState(src);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setCurrent(src);
    setFailed(false);
  }, [src]);

  function onError() {
    if (current && /\.jpe?g$/i.test(current)) setCurrent(current.replace(/\.jpe?g$/i, ".svg"));
    else setFailed(true);
  }

  if (!current || failed) {
    return (
      <div className={`image-placeholder ${className}`} role="img" aria-label={alt}>
        🌸
      </div>
    );
  }
  return <img className={className} src={current} alt={alt} loading="lazy" onError={onError} />;
}
