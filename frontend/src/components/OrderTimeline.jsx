import { timelineSteps } from "../orderFlow.js";

// Вертикальная шкала этапов заказа: оформлен -> оплачен -> собирается -> в пути -> доставлен
export default function OrderTimeline({ order }) {
  return (
    <ol className="timeline" aria-label="Этапы заказа">
      {timelineSteps(order).map((step) => (
        <li
          key={step.key}
          className={`timeline-step timeline-${step.state}`}
          aria-current={step.state === "current" ? "step" : undefined}
        >
          <span className="timeline-dot" aria-hidden="true">
            {step.state === "done" ? "✓" : ""}
          </span>
          <span className="timeline-label">{step.label}</span>
        </li>
      ))}
    </ol>
  );
}
