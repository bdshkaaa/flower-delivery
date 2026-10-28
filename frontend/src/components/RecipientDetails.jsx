import { formatPhone } from "../labels.js";

// Получатель и детали адреса: квартира, подъезд, этаж, домофон, комментарий курьеру.
// details: { name, phone, privateHouse, apartment, entrance, floor, intercom, comment }
export default function RecipientDetails({ details, onChange, errors }) {
  const set = (field) => (e) => onChange({ ...details, [field]: e.target.value });

  return (
    <fieldset className="details">
      <legend>Получатель и адрес</legend>

      <div className="field">
        <label htmlFor="r-name">Имя получателя</label>
        <input id="r-name" value={details.name} onChange={set("name")} autoComplete="name" aria-invalid={Boolean(errors.name)} />
        {errors.name && <small className="text-error" role="alert">{errors.name}</small>}
      </div>

      <div className="field">
        <label htmlFor="r-phone">Телефон получателя</label>
        <input
          id="r-phone"
          type="tel"
          inputMode="tel"
          value={details.phone}
          onChange={set("phone")}
          onBlur={() => onChange({ ...details, phone: formatPhone(details.phone) })}
          placeholder="+7 900 123-45-67"
          autoComplete="tel"
          aria-invalid={Boolean(errors.phone)}
        />
        {errors.phone && <small className="text-error" role="alert">{errors.phone}</small>}
      </div>

      <label className="check">
        <input
          type="checkbox"
          checked={details.privateHouse}
          onChange={(e) => onChange({ ...details, privateHouse: e.target.checked, apartment: e.target.checked ? "" : details.apartment })}
        />
        Частный дом (без квартиры)
      </label>

      <div className="grid-4">
        <div className="field">
          <label htmlFor="r-apartment">Квартира</label>
          <input
            id="r-apartment"
            value={details.apartment}
            onChange={set("apartment")}
            disabled={details.privateHouse}
            aria-invalid={Boolean(errors.apartment)}
          />
        </div>
        <div className="field">
          <label htmlFor="r-entrance">Подъезд</label>
          <input id="r-entrance" value={details.entrance} onChange={set("entrance")} />
        </div>
        <div className="field">
          <label htmlFor="r-floor">Этаж</label>
          <input id="r-floor" value={details.floor} onChange={set("floor")} />
        </div>
        <div className="field">
          <label htmlFor="r-intercom">Домофон</label>
          <input id="r-intercom" value={details.intercom} onChange={set("intercom")} />
        </div>
      </div>
      {errors.apartment && <small className="text-error" role="alert">{errors.apartment}</small>}

      <div className="field">
        <label htmlFor="r-comment">Комментарий курьеру</label>
        <textarea
          id="r-comment"
          value={details.comment}
          onChange={set("comment")}
          maxLength={300}
          rows={2}
          placeholder="Например: позвонить за 10 минут, оставить у двери"
        />
      </div>
    </fieldset>
  );
}
