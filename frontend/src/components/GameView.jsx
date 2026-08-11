import { useEffect, useState } from "react";
import Board from "./Board";
import PlayerPanel from "./PlayerPanel";
import TransactionPanel from "./TransactionPanel";
import DebtsPanel from "./DebtsPanel";
import { getTiles } from "../api";
import {
  getGame,
  movePlayer,
  setPlayerPosition,
  createTransaction,
  buyProperty,
  auctionProperty,
  mortgageProperty,
  unmortgageProperty,
  buildHouse,
  sellHouse,
  getTransactions,
  getDebts,
  createDebt,
  settleDebt,
  setDiceMode,
  endTurn,
  claimFreeParking,
} from "../gamesApi";
import "./GameView.css";

export default function GameView({ gameId, onExit }) {
  const [tiles, setTiles] = useState([]);
  const [game, setGame] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [debts, setDebts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("players");
  const [expandedId, setExpandedId] = useState(null);
  const [rolledThisTurn, setRolledThisTurn] = useState(false);
  const [pendingRent, setPendingRent] = useState(null);

  const refreshTransactions = () => getTransactions(gameId).then(setTransactions);
  const refreshDebts = () => getDebts(gameId).then(setDebts);

  useEffect(() => {
    getGame(gameId)
      .then((g) =>
        Promise.all([
          getTiles(g.boardKey),
          getTransactions(gameId),
          getDebts(gameId),
        ]).then(([t, tx, d]) => {
          setGame(g);
          setTiles(t);
          setTransactions(tx);
          setDebts(d);
        })
      )
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [gameId]);

  const locked =
    !!game && game.players.length > 0 && game.turnOrder.length === game.players.length;

  if (loading) return <p className="status-text">Loading game...</p>;
  if (error) return <p className="status-text error">{error}</p>;
  if (!game) return null;

  const handleMove = async (player, steps) => {
    const { game: updated, passedGo, rentDue } = await movePlayer(gameId, player._id, steps);
    setGame(updated);
    setExpandedId(player._id);
    setRolledThisTurn(true);

    if (passedGo) {
      const bonus = game.rules?.goBonus ?? 200;
      const collect = window.confirm(`${player.name} passed GO — collect $${bonus}?`);
      if (collect) {
        const { game: afterSalary } = await createTransaction(gameId, {
          fromType: "bank",
          toType: "player",
          toPlayer: player._id,
          amount: bonus,
          category: "salary",
          note: "Passed GO",
        });
        setGame(afterSalary);
        refreshTransactions();
      }
    }

    if (rentDue) {
      setPendingRent({ ...rentDue, playerId: player._id });
    } else {
      setPendingRent(null);
    }
  };

  const handlePayRent = async () => {
    if (!pendingRent) return;
    const { game: afterRent } = await createTransaction(gameId, {
      fromType: "player",
      fromPlayer: pendingRent.playerId,
      toType: "player",
      toPlayer: pendingRent.ownerId,
      amount: pendingRent.amount,
      category: "rent",
      note: pendingRent.name,
    });
    setGame(afterRent);
    setPendingRent(null);
    refreshTransactions();
  };

  const handleDismissRent = () => setPendingRent(null);

  const handleEndTurn = async (player) => {
    const updated = await endTurn(gameId, player._id);
    setGame(updated);
    setExpandedId(updated.currentPlayerId);
    setRolledThisTurn(false);
    setPendingRent(null);
  };

  const handleSetPosition = async (player, position) => {
    const updated = await setPlayerPosition(gameId, player._id, position);
    setGame(updated);
  };

  const handleBuy = async (position, playerId) => {
    const { game: updated } = await buyProperty(gameId, position, playerId);
    setGame(updated);
    refreshTransactions();
  };

  const handleAuction = async (position, playerId, amount) => {
    try {
      const { game: updated } = await auctionProperty(gameId, position, playerId, amount);
      setGame(updated);
      refreshTransactions();
    } catch (err) {
      window.alert(err.message);
    }
  };

  const handleClaimFreeParking = async (playerId) => {
    const { game: updated } = await claimFreeParking(gameId, playerId);
    setGame(updated);
    refreshTransactions();
  };

  const handleMortgage = async (position) => {
    const { game: updated } = await mortgageProperty(gameId, position);
    setGame(updated);
    refreshTransactions();
  };

  const handleUnmortgage = async (position) => {
    const { game: updated } = await unmortgageProperty(gameId, position);
    setGame(updated);
    refreshTransactions();
  };

  const handleBuildHouse = async (position) => {
    try {
      const { game: updated } = await buildHouse(gameId, position);
      setGame(updated);
      refreshTransactions();
    } catch (err) {
      window.alert(err.message);
    }
  };

  const handleSellHouse = async (position) => {
    try {
      const { game: updated } = await sellHouse(gameId, position);
      setGame(updated);
      refreshTransactions();
    } catch (err) {
      window.alert(err.message);
    }
  };

  const handleTransactionSubmit = async (payload) => {
    const { game: updated } = await createTransaction(gameId, payload);
    setGame(updated);
    refreshTransactions();
  };

  const handleDebtCreate = async (payload) => {
    await createDebt(gameId, payload);
    refreshDebts();
  };

  const handleDebtSettle = async (debtId) => {
    const { game: updated } = await settleDebt(gameId, debtId);
    setGame(updated);
    refreshDebts();
    refreshTransactions();
  };

  const handleDiceModeToggle = async () => {
    const next = game.diceMode === "single" ? "double" : "single";
    const updated = await setDiceMode(gameId, next);
    setGame(updated);
  };

  return (
    <div className="game-view">
      <div className="game-view-topbar">
        <button className="back-btn" onClick={onExit}>
          ← Games
        </button>
        <h2>{game.name}</h2>
        <button className="dice-mode-toggle" onClick={handleDiceModeToggle}>
          🎲 {game.diceMode === "single" ? "One die" : "Two dice"}
        </button>
        {game.rules?.freeParkingJackpot && (
          <span className="free-parking-pot">🅿️ Pot: ${game.freeParkingPot}</span>
        )}
        {!locked && (
          <span className="turn-order-hint">
            Tap each player's dice as they take their first turn to set play order.
          </span>
        )}
      </div>

      <div className="game-view-layout">
        <Board tiles={tiles} players={game.players} properties={game.properties} />

        <div className="game-side-panel">
          <div className="game-tabs">
            <button
              className={tab === "players" ? "active" : ""}
              onClick={() => setTab("players")}
            >
              Players
            </button>
            <button className={tab === "log" ? "active" : ""} onClick={() => setTab("log")}>
              Transactions
            </button>
            <button className={tab === "debts" ? "active" : ""} onClick={() => setTab("debts")}>
              Debts
            </button>
          </div>

          {tab === "players" && (
            <PlayerPanel
              game={game}
              tiles={tiles}
              expandedId={expandedId}
              onExpand={setExpandedId}
              onMove={handleMove}
              onSetPosition={handleSetPosition}
              onBuy={handleBuy}
              onAuction={handleAuction}
              onClaimFreeParking={handleClaimFreeParking}
              onMortgage={handleMortgage}
              onUnmortgage={handleUnmortgage}
              onBuildHouse={handleBuildHouse}
              onSellHouse={handleSellHouse}
              onEndTurn={handleEndTurn}
              rolledThisTurn={rolledThisTurn}
              pendingRent={pendingRent}
              onPayRent={handlePayRent}
              onDismissRent={handleDismissRent}
            />
          )}

          {tab === "log" && (
            <TransactionPanel
              players={game.players}
              transactions={transactions}
              onSubmit={handleTransactionSubmit}
            />
          )}

          {tab === "debts" && (
            <DebtsPanel
              players={game.players}
              debts={debts}
              onCreate={handleDebtCreate}
              onSettle={handleDebtSettle}
            />
          )}
        </div>
      </div>
    </div>
  );
}
