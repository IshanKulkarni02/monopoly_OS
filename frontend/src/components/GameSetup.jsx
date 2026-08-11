import { useEffect, useState } from "react";
import { listGames, createGame, deleteGame, getVariants } from "../gamesApi";
import "./GameSetup.css";

const PLAYER_COLORS = [
  "#c0142c",
  "#0072bb",
  "#1fb25a",
  "#fef200",
  "#f7941d",
  "#d93a96",
  "#955436",
  "#0a2e1c",
];

const emptyPlayer = (idx) => ({
  name: "",
  color: PLAYER_COLORS[idx % PLAYER_COLORS.length],
  startingCash: 1500,
});

const DEFAULT_RULES = {
  goBonus: 200,
  freeParkingJackpot: false,
  jailRentSuspended: false,
  buildingLimits: "standard",
};

export default function GameSetup({ onGameStart }) {
  const [games, setGames] = useState([]);
  const [variants, setVariants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [players, setPlayers] = useState([emptyPlayer(0), emptyPlayer(1)]);
  const [diceMode, setDiceMode] = useState("double");
  const [variant, setVariant] = useState("classic");
  const [rules, setRules] = useState(DEFAULT_RULES);
  const [error, setError] = useState(null);

  const refresh = () => listGames().then(setGames).catch(() => {});

  useEffect(() => {
    Promise.all([refresh(), getVariants().then(setVariants).catch(() => {})]).finally(() =>
      setLoading(false)
    );
  }, []);

  const updatePlayer = (idx, key, value) => {
    setPlayers((prev) =>
      prev.map((p, i) => (i === idx ? { ...p, [key]: value } : p))
    );
  };

  const addPlayerRow = () => setPlayers((prev) => [...prev, emptyPlayer(prev.length)]);
  const removePlayerRow = (idx) =>
    setPlayers((prev) => prev.filter((_, i) => i !== idx));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    const cleanPlayers = players
      .map((p) => ({ ...p, name: p.name.trim(), startingCash: Number(p.startingCash) }))
      .filter((p) => p.name);

    if (!name.trim() || cleanPlayers.length === 0) {
      setError("Give the game a name and at least one player.");
      return;
    }

    try {
      const game = await createGame({
        name: name.trim(),
        players: cleanPlayers,
        diceMode,
        variant,
        rules,
      });
      onGameStart(game._id);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="game-setup">
      <section className="game-setup-panel">
        <h2>Existing games</h2>
        {loading && <p>Loading...</p>}
        {!loading && games.length === 0 && <p className="muted">No games yet.</p>}
        <ul className="game-list">
          {games.map((g) => (
            <li key={g._id} className="game-list-item">
              <div>
                <strong>{g.name}</strong>
                <span className="muted"> · {g.playerCount} players · {g.status}</span>
              </div>
              <div className="game-list-actions">
                <button onClick={() => onGameStart(g._id)}>Resume</button>
                <button
                  className="danger"
                  onClick={async () => {
                    await deleteGame(g._id);
                    refresh();
                  }}
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section className="game-setup-panel">
        <h2>
          <button className="link-btn" onClick={() => setCreating((v) => !v)}>
            {creating ? "− Cancel new game" : "+ New game"}
          </button>
        </h2>

        {creating && (
          <form className="game-form" onSubmit={handleSubmit}>
            <label>
              Game name
              <input value={name} onChange={(e) => setName(e.target.value)} required />
            </label>

            <fieldset className="variant-field">
              <legend>Edition</legend>
              <div className="variant-list">
                {variants.map((v) => (
                  <label
                    key={v.key}
                    className={`variant-option ${!v.implemented ? "disabled" : ""} ${
                      variant === v.key ? "selected" : ""
                    }`}
                  >
                    <input
                      type="radio"
                      name="variant"
                      value={v.key}
                      checked={variant === v.key}
                      disabled={!v.implemented}
                      onChange={() => setVariant(v.key)}
                    />
                    <div>
                      <div className="variant-label">
                        {v.label}
                        {!v.implemented && <span className="coming-soon">Coming soon</span>}
                      </div>
                      <div className="variant-desc">{v.description}</div>
                    </div>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="player-rows">
              {players.map((p, idx) => (
                <div className="player-row" key={idx}>
                  <input
                    type="color"
                    value={p.color}
                    onChange={(e) => updatePlayer(idx, "color", e.target.value)}
                  />
                  <input
                    placeholder={`Player ${idx + 1} name`}
                    value={p.name}
                    onChange={(e) => updatePlayer(idx, "name", e.target.value)}
                  />
                  <input
                    type="number"
                    value={p.startingCash}
                    onChange={(e) => updatePlayer(idx, "startingCash", e.target.value)}
                  />
                  <button
                    type="button"
                    className="danger small"
                    onClick={() => removePlayerRow(idx)}
                    disabled={players.length <= 1}
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            <button type="button" className="secondary" onClick={addPlayerRow}>
              + Add player
            </button>

            <fieldset className="dice-mode-field">
              <legend>Dice</legend>
              <label>
                <input
                  type="radio"
                  name="diceMode"
                  value="double"
                  checked={diceMode === "double"}
                  onChange={() => setDiceMode("double")}
                />
                Two dice (standard Monopoly)
              </label>
              <label>
                <input
                  type="radio"
                  name="diceMode"
                  value="single"
                  checked={diceMode === "single"}
                  onChange={() => setDiceMode("single")}
                />
                One die
              </label>
            </fieldset>

            <fieldset className="rules-field">
              <legend>House rules</legend>

              <label className="rule-row">
                <span>Go bonus</span>
                <select
                  value={rules.goBonus}
                  onChange={(e) =>
                    setRules((r) => ({ ...r, goBonus: Number(e.target.value) }))
                  }
                >
                  <option value={200}>$200 (standard)</option>
                  <option value={400}>$400 (double)</option>
                </select>
              </label>

              <label className="rule-row checkbox">
                <input
                  type="checkbox"
                  checked={rules.freeParkingJackpot}
                  onChange={(e) =>
                    setRules((r) => ({ ...r, freeParkingJackpot: e.target.checked }))
                  }
                />
                <span>Free Parking jackpot (taxes/fines pool up, paid out on landing)</span>
              </label>

              <label className="rule-row checkbox">
                <input
                  type="checkbox"
                  checked={rules.jailRentSuspended}
                  onChange={(e) =>
                    setRules((r) => ({ ...r, jailRentSuspended: e.target.checked }))
                  }
                />
                <span>Suspend rent collection while the owner is in jail</span>
              </label>

              <label className="rule-row">
                <span>Building supply</span>
                <select
                  value={rules.buildingLimits}
                  onChange={(e) =>
                    setRules((r) => ({ ...r, buildingLimits: e.target.value }))
                  }
                >
                  <option value="standard">Standard (32 houses / 12 hotels)</option>
                  <option value="infinite">Infinite</option>
                </select>
              </label>
            </fieldset>

            {error && <p className="error-text">{error}</p>}

            <button type="submit" className="primary">
              Start game
            </button>
          </form>
        )}
      </section>
    </div>
  );
}
