import { useState } from "react";
import "./PlayerPanel.css";

const DIE_FACES = [1, 2, 3, 4, 5, 6];

function DiceRoller({ diceMode, onRoll }) {
  const [dieA, setDieA] = useState(null);
  const [dieB, setDieB] = useState(null);

  if (diceMode === "single") {
    return (
      <div className="dice-row">
        {DIE_FACES.map((n) => (
          <button key={n} type="button" className="die-btn" onClick={() => onRoll(n)}>
            {n}
          </button>
        ))}
      </div>
    );
  }

  const pick = (slot, value) => {
    const a = slot === "a" ? value : dieA;
    const b = slot === "b" ? value : dieB;
    if (a != null && b != null) {
      onRoll(a + b);
      setDieA(null);
      setDieB(null);
    } else if (slot === "a") {
      setDieA(value);
    } else {
      setDieB(value);
    }
  };

  return (
    <div className="dice-double">
      <div className="dice-row">
        {DIE_FACES.map((n) => (
          <button
            key={n}
            type="button"
            className={`die-btn ${dieA === n ? "selected" : ""}`}
            onClick={() => pick("a", n)}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="dice-row">
        {DIE_FACES.map((n) => (
          <button
            key={n}
            type="button"
            className={`die-btn ${dieB === n ? "selected" : ""}`}
            onClick={() => pick("b", n)}
          >
            {n}
          </button>
        ))}
      </div>
      {(dieA != null || dieB != null) && (
        <p className="dice-hint">
          Die A: {dieA ?? "—"} · Die B: {dieB ?? "—"}
        </p>
      )}
    </div>
  );
}

function AuctionForm({ tile, players, onAuction }) {
  const [open, setOpen] = useState(false);
  const [winnerId, setWinnerId] = useState(players[0]?._id || "");
  const [amount, setAmount] = useState("");

  if (!open) {
    return (
      <button type="button" className="auction-toggle-btn" onClick={() => setOpen(true)}>
        Auction instead
      </button>
    );
  }

  return (
    <div className="auction-form">
      <label>
        Winning bidder
        <select value={winnerId} onChange={(e) => setWinnerId(e.target.value)}>
          {players.map((p) => (
            <option key={p._id} value={p._id}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Winning bid
        <input
          type="number"
          min="1"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
      </label>
      <div className="auction-form-actions">
        <button
          type="button"
          className="buy-btn"
          onClick={() => {
            const amt = Number(amount);
            if (winnerId && amt > 0) {
              onAuction(tile.position, winnerId, amt);
              setOpen(false);
              setAmount("");
            }
          }}
        >
          Confirm auction
        </button>
        <button type="button" onClick={() => setOpen(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function HouseBadge({ houses }) {
  if (!houses) return null;
  if (houses >= 5) return <span className="house-badge hotel">🏨 Hotel</span>;
  return <span className="house-badge">{"🏠".repeat(houses)}</span>;
}

export default function PlayerPanel({
  game,
  tiles,
  expandedId,
  onExpand,
  onMove,
  onSetPosition,
  onBuy,
  onAuction,
  onClaimFreeParking,
  onMortgage,
  onUnmortgage,
  onBuildHouse,
  onSellHouse,
  onEndTurn,
  rolledThisTurn,
  pendingRent,
  onPayRent,
  onDismissRent,
}) {
  const tileByPosition = {};
  tiles.forEach((t) => {
    tileByPosition[t.position] = t;
  });

  const locked =
    game.players.length > 0 && game.turnOrder.length === game.players.length;

  return (
    <ul className="player-panel-list">
      {game.players.map((player) => {
        const isOpen = expandedId === player._id;
        const currentTile = tileByPosition[player.position];
        const ownedProperties = game.properties.filter(
          (p) => p.ownerId === player._id
        );
        const canBuyCurrentTile =
          currentTile &&
          game.properties.find(
            (p) => p.position === currentTile.position && !p.ownerId
          );

        const turnIndex = game.turnOrder.indexOf(player._id);
        const turnLabel = turnIndex >= 0 ? `P${turnIndex + 1}` : null;
        const isCurrent = locked && game.currentPlayerId === player._id;
        const hasRolled = isCurrent && rolledThisTurn;
        const owesRent = pendingRent && pendingRent.playerId === player._id;
        const canRoll = (!locked || isCurrent) && !hasRolled && !owesRent;
        const rentOwner = owesRent
          ? game.players.find((p) => p._id === pendingRent.ownerId)
          : null;

        return (
          <li
            key={player._id}
            className={`player-card ${isCurrent ? "current-turn" : ""}`}
          >
            <button
              className="player-card-header"
              onClick={() => onExpand(isOpen ? null : player._id)}
            >
              <span className="player-dot" style={{ backgroundColor: player.color }} />
              {turnLabel && <span className="turn-badge">{turnLabel}</span>}
              <span className="player-name">{player.name}</span>
              {isCurrent && <span className="your-turn-chip">Current turn</span>}
              <span className="player-cash">${player.cash}</span>
              <span className="player-position">
                {currentTile ? currentTile.name : `#${player.position}`}
              </span>
            </button>

            {isOpen && (
              <div className="player-card-body">
                {canRoll && (
                  <DiceRoller
                    diceMode={game.diceMode}
                    onRoll={(steps) => onMove(player, steps)}
                  />
                )}

                {owesRent && (
                  <div className="rent-due-box">
                    <p>
                      Owes <strong>${pendingRent.amount}</strong> rent to{" "}
                      <strong>{rentOwner ? rentOwner.name : "the owner"}</strong> for{" "}
                      {pendingRent.name}
                    </p>
                    <button className="pay-rent-btn" onClick={onPayRent}>
                      Pay ${pendingRent.amount} rent
                    </button>
                    <button className="dismiss-rent-btn" onClick={onDismissRent}>
                      Already settled / dismiss
                    </button>
                  </div>
                )}

                {hasRolled && !owesRent && (
                  <p className="waiting-text">
                    Rolled — resolve any purchase or rent, then end their turn.
                  </p>
                )}

                {locked && !isCurrent && (
                  <p className="waiting-text">Waiting for their turn.</p>
                )}

                {locked && isCurrent && (
                  <button
                    className="end-turn-btn"
                    onClick={() => onEndTurn(player)}
                    disabled={owesRent}
                    title={owesRent ? "Resolve the pending rent first" : undefined}
                  >
                    End turn →
                  </button>
                )}

                <label className="jump-to-label">
                  Jump to tile
                  <select
                    value={player.position}
                    onChange={(e) => onSetPosition(player, Number(e.target.value))}
                  >
                    {tiles.map((t) => (
                      <option key={t._id} value={t.position}>
                        {t.position} — {t.name}
                      </option>
                    ))}
                  </select>
                </label>

                {canBuyCurrentTile && (
                  <div className="buy-or-auction">
                    <button
                      className="buy-btn"
                      onClick={() => onBuy(currentTile.position, player._id)}
                    >
                      Buy {currentTile.name} for ${currentTile.price}
                    </button>
                    <AuctionForm
                      tile={currentTile}
                      players={game.players}
                      onAuction={onAuction}
                    />
                  </div>
                )}

                {currentTile?.type === "free_parking" && game.freeParkingPot > 0 && (
                  <button
                    className="free-parking-claim-btn"
                    onClick={() => onClaimFreeParking(player._id)}
                  >
                    🅿️ Claim Free Parking pot (${game.freeParkingPot})
                  </button>
                )}

                <div className="owned-properties">
                  <h4>Owns ({ownedProperties.length})</h4>
                  {ownedProperties.length === 0 && (
                    <p className="muted">No properties yet.</p>
                  )}
                  <ul>
                    {ownedProperties.map((p) => (
                      <li key={p.position} className="owned-property-row">
                        <div className="owned-property-name">
                          <span>{p.name}</span>
                          <HouseBadge houses={p.houses} />
                        </div>
                        <div className="owned-property-actions">
                          {p.type === "property" && !p.mortgaged && (
                            <>
                              <button
                                className="house-btn"
                                onClick={() => onBuildHouse(p.position)}
                                disabled={p.houses >= 5}
                                title={`Build for $${p.houseCost || 0}`}
                              >
                                + House
                              </button>
                              <button
                                className="house-btn"
                                onClick={() => onSellHouse(p.position)}
                                disabled={p.houses <= 0}
                              >
                                − House
                              </button>
                            </>
                          )}
                          {p.mortgaged ? (
                            <button onClick={() => onUnmortgage(p.position)}>
                              Unmortgage (${Math.round((p.mortgageValue || 0) * 1.1)})
                            </button>
                          ) : (
                            <button
                              onClick={() => onMortgage(p.position)}
                              disabled={p.houses > 0}
                            >
                              Mortgage (+${p.mortgageValue || 0})
                            </button>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
