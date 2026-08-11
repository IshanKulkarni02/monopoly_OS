import { useFormatMoney } from '../hooks/useBoard'
import type { GameStateOut } from '../api/types'

export function GmConsole({
  state,
  busy,
  onForceEndTurn,
  onCancelAuction,
  onAdvanceRound,
  onCancelTrade,
  onExport,
}: {
  state: GameStateOut
  busy: boolean
  onForceEndTurn: () => void
  onCancelAuction: () => void
  onAdvanceRound: () => void
  onCancelTrade: (tradeId: string) => void
  onExport: () => void
}) {
  const formatMoney = useFormatMoney()
  const current = state.players.find((p) => p.id === state.current_turn_player_id)
  const playerName = (id: string) => state.players.find((p) => p.id === id)?.name ?? 'Unknown'
  const showAdvanceRound = state.ruleset.inflation?.enabled && state.ruleset.inflation?.trigger === 'per_round'

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded border-2 border-ink bg-board-card p-3">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Turn control</h3>
        <p className="mb-2 text-sm text-ink">
          {current ? `Current turn: ${current.name}` : 'Turn order not set yet'}
        </p>
        <div className="flex flex-wrap gap-2">
          {current && (
            <button
              disabled={busy}
              onClick={onForceEndTurn}
              className="rounded border-2 border-ink px-3 py-1.5 text-xs font-bold text-ink hover:bg-board disabled:opacity-50"
            >
              Force end current turn
            </button>
          )}
          {showAdvanceRound && (
            <button
              disabled={busy}
              onClick={onAdvanceRound}
              className="rounded border-2 border-ink bg-monopoly-gold px-3 py-1.5 text-xs font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50"
            >
              Advance to round {state.round_number + 1}
            </button>
          )}
        </div>
      </div>

      {state.active_auction && 'property_id' in state.active_auction && (
        <div className="rounded border-2 border-ink bg-board-card p-3">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Active auction</h3>
          <p className="mb-2 text-sm text-ink">{state.active_auction.property_name} — current bid {formatMoney(state.active_auction.current_bid)}</p>
          <button
            disabled={busy}
            onClick={onCancelAuction}
            className="rounded border-2 border-monopoly-red px-3 py-1.5 text-xs font-bold text-monopoly-red hover:bg-board disabled:opacity-50"
          >
            Cancel auction
          </button>
        </div>
      )}

      <div className="rounded border-2 border-ink bg-board-card p-3">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">All pending trades ({state.pending_trades.length})</h3>
        {state.pending_trades.length === 0 ? (
          <p className="text-sm text-ink-soft">None right now.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {state.pending_trades.map((t) => (
              <li key={t.id} className="flex items-center justify-between rounded border border-ink bg-board px-2 py-1.5 text-sm">
                <span className="text-ink">{playerName(t.proposer_id)} → {playerName(t.recipient_id)}</span>
                <button
                  disabled={busy}
                  onClick={() => onCancelTrade(t.id)}
                  className="rounded border border-ink px-2 py-0.5 text-xs font-bold text-ink hover:bg-board-card disabled:opacity-50"
                >
                  Cancel
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <a
          href={`/g/${state.code}/display`}
          target="_blank"
          rel="noreferrer"
          className="rounded border-2 border-ink bg-board-card py-2 text-center text-sm font-bold text-ink hover:bg-board"
        >
          📺 Open public display
        </a>
        <button onClick={onExport} className="rounded border-2 border-ink bg-board-card py-2 text-sm font-bold text-ink hover:bg-board">
          ⬇ Save game to a file
        </button>
      </div>
    </div>
  )
}
