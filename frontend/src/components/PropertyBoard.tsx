import { groupPositions, tileAtPosition } from '../boardData'
import { useBoard, useFormatMoney } from '../hooks/useBoard'
import type { PlayerOut, PropertyOut } from '../api/types'

function housePips(houses: number, maxLevel: number): string {
  if (houses >= maxLevel) return '🏨'
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
  const formatMoney = useFormatMoney()
  const { tiles, groups } = useBoard()
  const playerName = (id: string | null) => players.find((p) => p.id === id)?.name

  function ownsFullGroup(groupId: string | null | undefined): boolean {
    if (!groupId || !myPlayerId) return false
    const positions = groupPositions(tiles, groupId)
    const groupProps = properties.filter((p) => positions.includes(p.space_index))
    return groupProps.length > 0 && groupProps.every((p) => p.owner_id === myPlayerId)
  }

  return (
    <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
      {properties.map((prop) => {
        const tile = tileAtPosition(tiles, prop.space_index)
        const group = groups.find((g) => g.id === tile?.group_id)
        const owner = playerName(prop.owner_id)
        const isMine = prop.owner_id === myPlayerId
        const maxLevel = tile ? Math.max(tile.rent_table.length - 1, 0) : 0
        const canUpgrade = Boolean(tile?.upgrade_costs.length)
        const canBuild = isMine && canUpgrade && !prop.mortgaged && prop.houses < maxLevel && ownsFullGroup(tile?.group_id)
        const canSell = isMine && canUpgrade && prop.houses > 0
        const upgradeCost = tile?.upgrade_costs[prop.houses]
        const sellRefund = tile?.upgrade_costs[prop.houses - 1]
        return (
          <div
            key={prop.id}
            className="flex items-center gap-3 overflow-hidden rounded border-2 border-ink bg-board-card"
            style={group ? { borderLeftWidth: 10, borderLeftColor: group.color } : undefined}
          >
            <div className="flex flex-1 flex-wrap items-center gap-2 p-3">
              {tile && !canUpgrade && tile.kind === 'property' && (
                <span className="flex h-8 w-6 shrink-0 items-center justify-center text-lg">
                  {tile.rent_model === 'group_count_table' ? '🚂' : '💡'}
                </span>
              )}
              <div className="flex-1">
                <div className="font-bold text-ink">
                  {prop.name} {housePips(prop.houses, maxLevel)}
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
                  {prop.houses === maxLevel - 1 ? 'Build hotel' : 'Build upgrade'} ({formatMoney(upgradeCost ?? 0)})
                </button>
              )}
              {canSell && onSellHouse && (
                <button
                  onClick={() => onSellHouse(prop.id)}
                  className="rounded border-2 border-ink px-3 py-1.5 text-sm font-bold text-ink hover:bg-board"
                >
                  Sell upgrade (+{formatMoney(Math.floor((sellRefund ?? 0) / 2))})
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
