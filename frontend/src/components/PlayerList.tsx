import { formatMoney } from '../boardData'
import type { PlayerOut } from '../api/types'

export function PlayerList({
  players,
  myPlayerId,
  canManageBanker,
  onToggleBanker,
}: {
  players: PlayerOut[]
  myPlayerId?: string
  canManageBanker?: boolean
  onToggleBanker?: (playerId: string, next: boolean) => void
}) {
  return (
    <ul className="flex flex-col gap-2">
      {players.map((p) => (
        <li
          key={p.id}
          className={`flex items-center justify-between rounded-xl border p-3 ${
            p.id === myPlayerId ? 'border-emerald-600 bg-emerald-950/40' : 'border-neutral-800 bg-neutral-900'
          }`}
        >
          <div className="flex items-center gap-2">
            <span className="font-medium">{p.name}</span>
            {p.is_host && <span className="rounded bg-neutral-700 px-1.5 py-0.5 text-xs">Host</span>}
            {p.is_banker && <span className="rounded bg-amber-700 px-1.5 py-0.5 text-xs">Banker</span>}
            {p.status === 'bankrupt' && <span className="rounded bg-red-800 px-1.5 py-0.5 text-xs">Bankrupt</span>}
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg">{formatMoney(p.balance)}</span>
            {canManageBanker && onToggleBanker && (
              <button
                onClick={() => onToggleBanker(p.id, !p.is_banker)}
                className="rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-800"
              >
                {p.is_banker ? 'Remove banker' : 'Make banker'}
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  )
}
