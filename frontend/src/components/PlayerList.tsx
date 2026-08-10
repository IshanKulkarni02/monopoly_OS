import { denominationSummary } from '../boardData'
import { useBoard, useFormatMoney } from '../hooks/useBoard'
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
  const formatMoney = useFormatMoney()
  const { currency } = useBoard()
  return (
    <ul className="flex flex-col gap-2">
      {players.map((p) => {
        const notes = denominationSummary(p.denominations, currency.symbol)
        return (
        <li
          key={p.id}
          className={`flex items-center justify-between rounded border-2 p-3 ${
            p.id === myPlayerId ? 'border-monopoly-green bg-monopoly-green/10' : 'border-ink bg-board-card'
          }`}
        >
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-ink">{p.name}</span>
              {p.is_bot && <span className="rounded border border-ink bg-monopoly-green px-1.5 py-0.5 text-xs font-bold text-white">🤖 Bot</span>}
              {p.is_host && <span className="rounded border border-ink bg-monopoly-gold px-1.5 py-0.5 text-xs font-bold text-ink">Host</span>}
              {p.is_banker && <span className="rounded border border-ink bg-ink px-1.5 py-0.5 text-xs font-bold text-white">Banker</span>}
              {p.status === 'bankrupt' && (
                <span className="rounded border border-ink bg-monopoly-red px-1.5 py-0.5 text-xs font-bold text-white">Bankrupt</span>
              )}
            </div>
            {notes && <span className="font-mono text-[10px] text-ink-soft">{notes}</span>}
          </div>
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg font-bold text-monopoly-green">{formatMoney(p.balance)}</span>
            {canManageBanker && onToggleBanker && !p.is_bot && (
              <button
                onClick={() => onToggleBanker(p.id, !p.is_banker)}
                className="rounded border-2 border-ink px-2 py-1 text-xs font-bold text-ink hover:bg-board"
              >
                {p.is_banker ? 'Remove banker' : 'Make banker'}
              </button>
            )}
          </div>
        </li>
        )
      })}
    </ul>
  )
}
