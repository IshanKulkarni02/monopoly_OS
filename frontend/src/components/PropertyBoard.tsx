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
          <div key={prop.id} className="flex items-center gap-3 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
            {space.color && (
              <span
                className="h-8 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: COLOR_SWATCH[space.color] }}
              />
            )}
            {space.type !== 'property' && (
              <span className="flex h-8 w-2 shrink-0 items-center justify-center text-neutral-500">
                {space.type === 'railroad' ? '🚂' : '💡'}
              </span>
            )}
            <div className="flex-1">
              <div className="font-medium">{prop.name}</div>
              <div className="text-xs text-neutral-400">
                {formatMoney(prop.price)}
                {owner ? ` · owned by ${owner}` : ' · unowned'}
                {prop.mortgaged ? ' · mortgaged' : ''}
              </div>
            </div>
            {!prop.owner_id && onPurchase && (
              <button
                onClick={() => onPurchase(prop.id)}
                className="rounded-lg bg-emerald-700 px-3 py-1.5 text-sm font-medium hover:bg-emerald-600"
              >
                Buy
              </button>
            )}
            {isMine && <span className="text-xs text-emerald-400">Yours</span>}
          </div>
        )
      })}
    </div>
  )
}
