import { COLOR_SWATCH, formatMoney, spaceByIndex } from '../boardData'
import type { PlayerOut, PropertyOut } from '../api/types'

export function PropertyBoard({
  properties,
  players,
  myPlayerId,
  onPurchase,
}: {
  properties: PropertyOut[]
  players: PlayerOut[]
  myPlayerId?: string
  onPurchase?: (propertyId: string) => void
}) {
  const playerName = (id: string | null) => players.find((p) => p.id === id)?.name

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {properties.map((prop) => {
        const space = spaceByIndex(prop.space_index)
        const owner = playerName(prop.owner_id)
        const isMine = prop.owner_id === myPlayerId
        return (
          <div
            key={prop.id}
            className="flex items-center gap-3 overflow-hidden rounded border-2 border-ink bg-board-card"
            style={space.color ? { borderLeftWidth: 10, borderLeftColor: COLOR_SWATCH[space.color] } : undefined}
          >
            <div className="flex flex-1 items-center gap-2 p-3">
              {space.type !== 'property' && (
                <span className="flex h-8 w-6 shrink-0 items-center justify-center text-lg">
                  {space.type === 'railroad' ? '🚂' : '💡'}
                </span>
              )}
              <div className="flex-1">
                <div className="font-bold text-ink">{prop.name}</div>
                <div className="text-xs font-medium text-ink-soft">
                  {formatMoney(prop.price)}
                  {owner ? ` · owned by ${owner}` : ' · unowned'}
                  {prop.mortgaged ? ' · mortgaged' : ''}
                </div>
              </div>
              {!prop.owner_id && onPurchase && (
                <button
                  onClick={() => onPurchase(prop.id)}
                  className="rounded border-2 border-ink bg-monopoly-green px-3 py-1.5 text-sm font-bold text-white hover:bg-monopoly-green-dark"
                >
                  Buy
                </button>
              )}
              {isMine && <span className="text-xs font-bold text-monopoly-green">Yours</span>}
            </div>
          </div>
        )
      })}
    </div>
  )
}
