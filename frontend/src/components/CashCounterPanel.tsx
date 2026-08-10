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
      <p className="text-sm text-neutral-400">
        Quick cash-count adjustments — no from/to bookkeeping, just nudge a player's displayed balance
        to match what's in front of them.
      </p>
      {error && <p className="text-sm text-red-400">{error}</p>}
      {players.map((p) => {
        const amount = Number(amounts[p.id] ?? 20)
        return (
          <div key={p.id} className="flex items-center gap-2 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
            <div className="flex-1">
              <div className="font-medium">{p.name}</div>
              <div className="font-mono text-lg text-emerald-400">{formatMoney(p.balance)}</div>
            </div>
            <input
              type="number"
              value={amounts[p.id] ?? 20}
              onChange={(e) => setAmounts({ ...amounts, [p.id]: e.target.value })}
              className="w-20 rounded-lg border border-neutral-700 bg-neutral-950 p-2 text-center"
            />
            <button
              disabled={busy}
              onClick={() => onAdjust(p.id, -amount)}
              className="rounded-lg bg-red-800 px-3 py-2 font-medium hover:bg-red-700 disabled:opacity-50"
            >
              -
            </button>
            <button
              disabled={busy}
              onClick={() => onAdjust(p.id, amount)}
              className="rounded-lg bg-emerald-700 px-3 py-2 font-medium hover:bg-emerald-600 disabled:opacity-50"
            >
              +
            </button>
          </div>
        )
      })}
    </div>
  )
}
