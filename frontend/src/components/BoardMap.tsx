import { useState } from 'react'
import { useBoard } from '../hooks/useBoard'
import type { PlayerOut, PropertyOut } from '../api/types'

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
  properties = [],
  defaultCollapsed = false,
  pickMode = false,
  pickLabel,
  onPickTile,
  fullScreen = false,
  center,
}: {
  players: PlayerOut[]
  /** Colors each tile's owner strip. Omit where there's no live game (e.g. the board template editor). */
  properties?: PropertyOut[]
  defaultCollapsed?: boolean
  pickMode?: boolean
  pickLabel?: string
  onPickTile?: (position: number) => void
  /** Fill the available width edge-to-edge instead of living in a collapsible card — the board itself becomes the screen. */
  fullScreen?: boolean
  /** Rendered in the tile ring's interior, like the logo/card decks on a real board. Ignored unless `fullScreen`. */
  center?: React.ReactNode
}) {
  const { tiles, groups } = useBoard()
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const side = tiles.length ? tiles.length / 4 : 10

  const colorByPlayerId = new Map(players.map((p, index) => [p.id, tokenColor(index)]))

  const playersByPosition = new Map<number, { player: PlayerOut; color: string }[]>()
  players.forEach((p) => {
    if (p.status !== 'active') return
    const list = playersByPosition.get(p.position) ?? []
    list.push({ player: p, color: colorByPlayerId.get(p.id)! })
    playersByPosition.set(p.position, list)
  })

  const ownerByPosition = new Map<number, { name: string; color: string }>()
  properties.forEach((prop) => {
    if (!prop.owner_id) return
    const owner = players.find((p) => p.id === prop.owner_id)
    const color = colorByPlayerId.get(prop.owner_id)
    if (owner && color) ownerByPosition.set(prop.space_index, { name: owner.name, color })
  })

  const grid = (
    <div
      data-board-map
      className={fullScreen ? 'w-full aspect-square p-1' : 'mx-auto aspect-square w-full max-w-[440px] p-2'}
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
        const owner = ownerByPosition.get(tile.position)
        return (
          <button
            key={tile.id}
            type="button"
            disabled={!pickMode}
            onClick={() => onPickTile?.(tile.position)}
            title={owner ? `${tile.name} — owned by ${owner.name}` : tile.name}
            className={`relative flex flex-col items-center justify-center gap-0.5 overflow-hidden rounded-sm border p-0.5 text-center transition ${
              pickMode ? 'cursor-pointer border-monopoly-green bg-monopoly-green/10 hover:bg-monopoly-green/30' : 'border-ink/25 bg-board'
            }`}
            style={{
              gridColumn: col + 1,
              gridRow: row + 1,
              borderTopColor: group?.color,
              borderTopWidth: group ? 3 : undefined,
              borderBottomColor: owner?.color,
              borderBottomWidth: owner ? 4 : undefined,
            }}
          >
            <span className="line-clamp-2 px-0.5 text-[6.5px] font-bold leading-[1.1] text-ink sm:text-[8px]">
              {tile.name}
            </span>
            {occupants.length > 0 && (
              <span className="flex flex-wrap justify-center gap-px">
                {occupants.map(({ player, color }) => (
                  <span
                    key={player.id}
                    title={player.name}
                    className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border border-ink text-[6px] font-bold text-white shadow-[1px_1px_0_#1a1a1a] sm:h-4 sm:w-4 sm:text-[7px]"
                    style={{ background: color }}
                  >
                    {player.name.charAt(0).toUpperCase()}
                  </span>
                ))}
              </span>
            )}
          </button>
        )
      })}
      {fullScreen && center && (
        <div
          className="flex min-h-0 flex-col overflow-y-auto rounded border-2 border-ink bg-board-card p-2"
          style={{ gridColumn: `2 / span ${side - 1}`, gridRow: `2 / span ${side - 1}` }}
        >
          {center}
        </div>
      )}
    </div>
  )

  if (fullScreen) {
    return grid
  }

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
      {!collapsed && grid}
    </div>
  )
}

export { TOKEN_COLORS, tokenColor }
