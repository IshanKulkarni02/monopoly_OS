import { useState } from 'react'
import { useBoard } from '../hooks/useBoard'
import type { PlayerOut } from '../api/types'

// No player-color field on the model yet (spec asks for one eventually) —
// assigning from a fixed palette by roster order gives distinct, stable
// tokens without a schema change.
const TOKEN_COLORS = ['#c0392b', '#2f6f4f', '#2f6fb4', '#c9922a', '#7a4fb5', '#0e8a7d']

function tokenColor(index: number): string {
  return TOKEN_COLORS[index % TOKEN_COLORS.length]
}

function perimeterCell(position: number, side: number): { col: number; row: number } {
  if (position <= side) return { col: side - position, row: side }
  if (position <= side * 2) return { col: 0, row: side - (position - side) }
  if (position <= side * 3) return { col: position - side * 2, row: 0 }
  return { col: side, row: position - side * 3 }
}

export function BoardMap({
  players,
  defaultCollapsed = false,
  pickMode = false,
  pickLabel,
  onPickTile,
}: {
  players: PlayerOut[]
  defaultCollapsed?: boolean
  pickMode?: boolean
  pickLabel?: string
  onPickTile?: (position: number) => void
}) {
  const { tiles, groups } = useBoard()
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const side = tiles.length ? tiles.length / 4 : 10

  const playersByPosition = new Map<number, { player: PlayerOut; color: string }[]>()
  players.forEach((p, index) => {
    if (p.status !== 'active') return
    const list = playersByPosition.get(p.position) ?? []
    list.push({ player: p, color: tokenColor(index) })
    playersByPosition.set(p.position, list)
  })

  return (
    <div className="overflow-hidden rounded border-2 border-ink bg-board-card">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-bold uppercase tracking-wide text-ink-soft hover:bg-board"
      >
        <span>{pickMode ? pickLabel || 'Choose a tile' : 'Board map'}</span>
        <span>{collapsed ? 'Show ▾' : 'Hide ▴'}</span>
      </button>
      {!collapsed && (
        <div
          className="mx-auto aspect-square w-full max-w-[440px] p-2"
          style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${side + 1}, 1fr)`,
            gridTemplateRows: `repeat(${side + 1}, 1fr)`,
            gap: 2,
          }}
        >
          {tiles.map((tile) => {
            const { col, row } = perimeterCell(tile.position, side)
            const group = groups.find((g) => g.id === tile.group_id)
            const occupants = playersByPosition.get(tile.position) ?? []
            return (
              <button
                key={tile.id}
                type="button"
                disabled={!pickMode}
                onClick={() => onPickTile?.(tile.position)}
                title={tile.name}
                className={`flex flex-col items-center justify-center gap-0.5 overflow-hidden rounded-sm border p-0.5 text-center transition ${
                  pickMode ? 'cursor-pointer border-monopoly-green bg-monopoly-green/10 hover:bg-monopoly-green/30' : 'border-ink/25 bg-board'
                }`}
                style={{
                  gridColumn: col + 1,
                  gridRow: row + 1,
                  borderTopColor: group?.color,
                  borderTopWidth: group ? 3 : undefined,
                }}
              >
                <span className="line-clamp-2 px-0.5 text-[6.5px] font-bold leading-[1.1] text-ink sm:text-[8px]">
                  {tile.name}
                </span>
                {occupants.length > 0 && (
                  <span className="flex flex-wrap justify-center gap-0.5">
                    {occupants.map(({ player, color }) => (
                      <span
                        key={player.id}
                        title={player.name}
                        className="h-2 w-2 rounded-full border border-ink sm:h-2.5 sm:w-2.5"
                        style={{ background: color }}
                      />
                    ))}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export { TOKEN_COLORS, tokenColor }
