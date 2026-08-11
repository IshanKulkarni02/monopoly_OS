import { useState } from "react";
import "./DebtsPanel.css";

function playerName(players, id) {
  return players.find((p) => p._id === id)?.name || "Unknown";
}

export default function DebtsPanel({ players, debts, onCreate, onSettle }) {
  const [fromPlayer, setFromPlayer] = useState(players[0]?._id || "");
  const [toPlayer, setToPlayer] = useState(players[1]?._id || players[0]?._id || "");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState(null);

  const active = debts.filter((d) => !d.settled);
  const settled = debts.filter((d) => d.settled);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const amt = Number(amount);
    if (!amt || amt <= 0) {
      setError("Amount must be greater than 0");
      return;
    }
    if (fromPlayer === toPlayer) {
      setError("Debtor and creditor can't be the same player");
      return;
    }
    try {
      await onCreate({ fromPlayer, toPlayer, amount: amt, reason });
      setAmount("");
      setReason("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="debts-panel">
      <form className="debt-form" onSubmit={handleSubmit}>
        <div className="tx-row">
          <label>
            Owes (debtor)
            <select value={fromPlayer} onChange={(e) => setFromPlayer(e.target.value)}>
              {players.map((p) => (
                <option key={p._id} value={p._id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Owed to (creditor)
            <select value={toPlayer} onChange={(e) => setToPlayer(e.target.value)}>
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
            <input type="number" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} />
          </label>
          <label>
            Reason
            <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="optional" />
          </label>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button type="submit" className="primary">
          Record IOU
        </button>
      </form>

      <div className="debt-list">
        <h4>Outstanding ({active.length})</h4>
        {active.length === 0 && <p className="muted">No open debts.</p>}
        <ul>
          {active.map((d) => (
            <li key={d._id} className="debt-row">
              <span>
                <strong>{playerName(players, d.fromPlayer)}</strong> owes{" "}
                <strong>{playerName(players, d.toPlayer)}</strong> ${d.amount}
                {d.reason && <span className="muted"> — {d.reason}</span>}
              </span>
              <button onClick={() => onSettle(d._id)}>Settle</button>
            </li>
          ))}
        </ul>

        {settled.length > 0 && (
          <>
            <h4>Settled ({settled.length})</h4>
            <ul>
              {settled.map((d) => (
                <li key={d._id} className="debt-row settled">
                  <span>
                    {playerName(players, d.fromPlayer)} → {playerName(players, d.toPlayer)} $
                    {d.amount}
                  </span>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
