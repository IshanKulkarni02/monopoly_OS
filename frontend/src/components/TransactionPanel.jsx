import { useState } from "react";
import "./TransactionPanel.css";

const CATEGORIES = [
  "rent",
  "purchase",
  "tax",
  "salary",
  "mortgage",
  "unmortgage",
  "loan",
  "loan_repayment",
  "fine",
  "other",
];

function partyLabel(players, type, id) {
  if (type === "bank") return "Bank";
  const p = players.find((pl) => pl._id === id);
  return p ? p.name : "Unknown";
}

export default function TransactionPanel({ players, transactions, onSubmit }) {
  const [fromKey, setFromKey] = useState("bank");
  const [toKey, setToKey] = useState(players[0]?._id || "bank");
  const [amount, setAmount] = useState("");
  const [category, setCategory] = useState("rent");
  const [note, setNote] = useState("");
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const amt = Number(amount);
    if (!amt || amt <= 0) {
      setError("Amount must be greater than 0");
      return;
    }
    if (fromKey === toKey) {
      setError("From and To can't be the same");
      return;
    }
    try {
      await onSubmit({
        fromType: fromKey === "bank" ? "bank" : "player",
        fromPlayer: fromKey === "bank" ? null : fromKey,
        toType: toKey === "bank" ? "bank" : "player",
        toPlayer: toKey === "bank" ? null : toKey,
        amount: amt,
        category,
        note,
      });
      setAmount("");
      setNote("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="transaction-panel">
      <form className="transaction-form" onSubmit={handleSubmit}>
        <div className="tx-row">
          <label>
            From
            <select value={fromKey} onChange={(e) => setFromKey(e.target.value)}>
              <option value="bank">Bank</option>
              {players.map((p) => (
                <option key={p._id} value={p._id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            To
            <select value={toKey} onChange={(e) => setToKey(e.target.value)}>
              <option value="bank">Bank</option>
              {players.map((p) => (
                <option key={p._id} value={p._id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="tx-row">
          <label>
            Amount
            <input
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              min="1"
            />
          </label>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>
                  {c.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label>
          Note
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="optional" />
        </label>

        {error && <p className="error-text">{error}</p>}

        <button type="submit" className="primary">
          Log transaction
        </button>
      </form>

      <ul className="transaction-log">
        {transactions.length === 0 && <li className="muted">No transactions yet.</li>}
        {transactions.map((t) => (
          <li key={t._id} className="transaction-row">
            <span className="tx-parties">
              {partyLabel(players, t.fromType, t.fromPlayer)} →{" "}
              {partyLabel(players, t.toType, t.toPlayer)}
            </span>
            <span className="tx-amount">${t.amount}</span>
            <span className="tx-category">{t.category.replace("_", " ")}</span>
            {t.note && <span className="tx-note">{t.note}</span>}
          </li>
        ))}
      </ul>
    </div>
  );
}
