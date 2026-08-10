import { COLOR_SWATCH, HOUSE_COSTS, colorGroupSpaceIndices, formatMoney, spaceByIndex } from '../boardData'
import type { PlayerOut, PropertyOut } from '../api/types'

function housePips(houses: number): string {
  if (houses >= 5) return '🏨'
  if (houses > 0) return '🏠'.repeat(houses)
  return ''
}

export function PropertyBoard({
  properties,
  players,
  myPlayerId,
  onPurchase,
  onBuildHouse,
  onSellHouse,
}: {
  properties: PropertyOut[]
  players: PlayerOut[]
  myPlayerId?: string
  onPurchase?: (propertyId: string) => void
  onBuildHouse?: (propertyId: string) => void
  onSellHouse?: (propertyId: string) => void
}) {
  const playerName = (id: string | null) => players.find((p) => p.id === id)?.name

  function ownsFullGroup(color: string | undefined): boolean {
    if (!color || !myPlayerId) return false
    const groupIndices = colorGroupSpaceIndices(color)
    const groupProps = properties.filter((p) => groupIndices.includes(p.space_index))
    return groupProps.length > 0 && groupProps.every((p) => p.owner_id === myPlayerId)
  }

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {properties.map((prop) => {
        const space = spaceByIndex(prop.space_index)
        const owner = playerName(prop.owner_id)
        const isMine = prop.owner_id === myPlayerId
        const canBuild = isMine && space.type === 'property' && !prop.mortgaged && prop.houses < 5 && ownsFullGroup(space.color)
        const canSell = isMine && space.type === 'property' && prop.houses > 0
        const houseCost = space.color ? HOUSE_COSTS[space.color] : undefined
        return (
          <div
            key={prop.id}
            className="flex items-center gap-3 overflow-hidden rounded border-2 border-ink bg-board-card"
            style={space.color ? { borderLeftWidth: 10, borderLeftColor: COLOR_SWATCH[space.color] } : undefined}
          >
            <div className="flex flex-1 flex-wrap items-center gap-2 p-3">
              {space.type !== 'property' && (
                <span className="flex h-8 w-6 shrink-0 items-center justify-center text-lg">
                  {space.type === 'railroad' ? '🚂' : '💡'}
                </span>
              )}
              <div className="flex-1">
                <div className="font-bold text-ink">
                  {prop.name} {housePips(prop.houses)}
                </div>
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
              {canBuild && onBuildHouse && (
                <button
                  onClick={() => onBuildHouse(prop.id)}
                  className="rounded border-2 border-ink bg-monopoly-gold px-3 py-1.5 text-sm font-bold text-ink hover:bg-monopoly-gold-dark"
                >
                  {prop.houses === 4 ? 'Build hotel' : 'Build house'} ({formatMoney(houseCost ?? 0)})
                </button>
              )}
              {canSell && onSellHouse && (
                <button
                  onClick={() => onSellHouse(prop.id)}
                  className="rounded border-2 border-ink px-3 py-1.5 text-sm font-bold text-ink hover:bg-board"
                >
                  Sell house (+{formatMoney(Math.floor((houseCost ?? 0) / 2))})
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
