import { tokenColor } from './BoardMap'
import type { PlayerOut } from '../api/types'

export function PlayerTabs({
  players,
  selectedId,
  currentTurnPlayerId,
  onSelect,
}: {
  players: PlayerOut[]
  selectedId: string | null
  currentTurnPlayerId?: string | null
  onSelect: (playerId: string) => void
}) {
  return (
    <div className="flex gap-1.5 overflow-x-auto pb-1" style={{ scrollbarWidth: 'thin' }}>
      {players.map((p, index) => {
        const isSelected = p.id === selectedId
        const isTurn = p.id === currentTurnPlayerId
        return (
          <button
            key={p.id}
            type="button"
            onClick={() => onSelect(p.id)}
            className={`flex shrink-0 items-center gap-1.5 rounded border-2 px-2.5 py-1.5 text-xs font-bold whitespace-nowrap ${
              isSelected
                ? 'border-ink bg-monopoly-red text-white shadow-[2px_2px_0_#1a1a1a]'
                : 'border-ink bg-board-card text-ink hover:bg-board'
            }`}
            style={{ minWidth: `${Math.max(100 / Math.min(players.length, 5), 18)}%` }}
          >
            <span className="h-2 w-2 shrink-0 rounded-full border border-ink" style={{ background: tokenColor(index) }} />
            {p.name}
            {isTurn && <span title="Current turn">🎲</span>}
          </button>
        )
      })}
    </div>
  )
}
