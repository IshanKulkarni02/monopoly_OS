import { useState } from "react";
import { TILE_TYPE_LABELS, COLOR_HEX } from "../boardLayout";

const EMPTY = {
  name: "",
  type: "property",
  color: "",
  price: "",
  rent: "",
  houseCost: "",
  mortgageValue: "",
  taxAmount: "",
};

function toFormState(tile) {
  if (!tile) return EMPTY;
  return {
    name: tile.name ?? "",
    type: tile.type ?? "property",
    color: tile.color ?? "",
    price: tile.price ?? "",
    rent: (tile.rent || []).join(", "),
    houseCost: tile.houseCost ?? "",
    mortgageValue: tile.mortgageValue ?? "",
    taxAmount: tile.taxAmount ?? "",
  };
}

function toPayload(form) {
  const payload = { name: form.name, type: form.type };

  if (form.type === "property") {
    payload.color = form.color || null;
    payload.price = form.price === "" ? null : Number(form.price);
    payload.houseCost = form.houseCost === "" ? null : Number(form.houseCost);
    payload.mortgageValue =
      form.mortgageValue === "" ? null : Number(form.mortgageValue);
    payload.rent = form.rent
      ? form.rent.split(",").map((n) => Number(n.trim())).filter((n) => !Number.isNaN(n))
      : [];
  } else if (form.type === "railroad" || form.type === "utility") {
    payload.price = form.price === "" ? null : Number(form.price);
    payload.mortgageValue =
      form.mortgageValue === "" ? null : Number(form.mortgageValue);
    payload.rent = form.rent
      ? form.rent.split(",").map((n) => Number(n.trim())).filter((n) => !Number.isNaN(n))
      : [];
    payload.color = null;
    payload.houseCost = null;
  } else if (form.type === "tax") {
    payload.taxAmount = form.taxAmount === "" ? null : Number(form.taxAmount);
    payload.color = null;
    payload.price = null;
    payload.rent = [];
    payload.houseCost = null;
    payload.mortgageValue = null;
  } else {
    payload.color = null;
    payload.price = null;
    payload.rent = [];
    payload.houseCost = null;
    payload.mortgageValue = null;
    payload.taxAmount = null;
  }

  return payload;
}

export default function TileForm({ tile, onSubmit, onCancel, onDelete }) {
  const [form, setForm] = useState(toFormState(tile));
  const [saving, setSaving] = useState(false);

  const update = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSubmit(toPayload(form));
    } finally {
      setSaving(false);
    }
  };

  const showPrice = form.type === "property" || form.type === "railroad" || form.type === "utility";
  const showRent = form.type === "property" || form.type === "railroad" || form.type === "utility";
  const showColor = form.type === "property";
  const showHouseCost = form.type === "property";
  const showMortgage = form.type === "property" || form.type === "railroad" || form.type === "utility";
  const showTax = form.type === "tax";

  return (
    <form className="tile-form" onSubmit={handleSubmit}>
      <label>
        Name
        <input value={form.name} onChange={update("name")} required />
      </label>

      <label>
        Type
        <select value={form.type} onChange={update("type")}>
          {Object.entries(TILE_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>

      {showColor && (
        <label>
          Color group
          <select value={form.color} onChange={update("color")}>
            <option value="">None</option>
            {Object.keys(COLOR_HEX).map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      )}

      {showPrice && (
        <label>
          Price
          <input type="number" value={form.price} onChange={update("price")} />
        </label>
      )}

      {showRent && (
        <label>
          Rent tiers (comma-separated)
          <input
            value={form.rent}
            onChange={update("rent")}
            placeholder="e.g. 2, 10, 30, 90, 160, 250"
          />
        </label>
      )}

      {showHouseCost && (
        <label>
          House cost
          <input type="number" value={form.houseCost} onChange={update("houseCost")} />
        </label>
      )}

      {showMortgage && (
        <label>
          Mortgage value
          <input type="number" value={form.mortgageValue} onChange={update("mortgageValue")} />
        </label>
      )}

      {showTax && (
        <label>
          Tax amount
          <input type="number" value={form.taxAmount} onChange={update("taxAmount")} />
        </label>
      )}

      <div className="tile-form-actions">
        <button type="submit" disabled={saving}>
          {saving ? "Saving..." : "Save"}
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {onDelete && (
          <button type="button" className="danger" onClick={onDelete}>
            Remove tile
          </button>
        )}
      </div>
    </form>
  );
}
