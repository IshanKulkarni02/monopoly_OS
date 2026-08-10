import { useState } from 'react'
import { formatMoney } from '../boardData'
import type { PlayerOut } from '../api/types'

export function CashCounterPanel({
  players,
  busy,
  error,
  onAdjust,
}: {
  players: PlayerOut[]
  busy: boolean
  error: string | null
  onAdjust: (playerId: string, delta: number) => void
}) {
  const [amounts, setAmounts] = useState<Record<string, string>>({})

  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-medium text-ink-soft">
        Quick cash-count adjustments — no from/to bookkeeping, just nudge a player's displayed balance
        to match what's in front of them.
      </p>
      {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
      {players.map((p) => {
        const amount = Number(amounts[p.id] ?? 20)
        return (
          <div key={p.id} className="flex items-center gap-2 rounded border-2 border-ink bg-board-card p-3">
            <div className="flex-1">
              <div className="font-bold text-ink">{p.name}</div>
              <div className="font-mono text-lg font-bold text-monopoly-green">{formatMoney(p.balance)}</div>
            </div>
            <input
              type="number"
              value={amounts[p.id] ?? 20}
              onChange={(e) => setAmounts({ ...amounts, [p.id]: e.target.value })}
              className="w-20 rounded border-2 border-ink bg-board-card p-2 text-center text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
            />
            <button
              disabled={busy}
              onClick={() => onAdjust(p.id, -amount)}
              className="rounded border-2 border-ink bg-monopoly-red px-3 py-2 font-bold text-white hover:bg-monopoly-red-dark disabled:opacity-50"
            >
              -
            </button>
            <button
              disabled={busy}
              onClick={() => onAdjust(p.id, amount)}
              className="rounded border-2 border-ink bg-monopoly-green px-3 py-2 font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
            >
              +
            </button>
          </div>
        )
      })}
    </div>
  )
}
