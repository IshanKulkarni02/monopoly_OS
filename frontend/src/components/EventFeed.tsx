import { useFormatMoney } from '../hooks/useBoard'
import type { EventLogOut } from '../api/types'

export function describe(entry: EventLogOut, formatMoney: (amount: number) => string): string {
  const p = entry.payload as Record<string, string | number | undefined>
  switch (entry.kind) {
    case 'transaction':
      return `${p.from} → ${p.to}: ${formatMoney(Number(p.amount))} (${p.reason})`
    case 'purchase':
      return `${p.property_name} purchased for ${formatMoney(Number(p.price))}`
    case 'player_joined':
      return `${p.name} joined the game`
    case 'game_created':
      return `Game created by ${p.host_name}`
    case 'game_started':
      return `Game started with ${p.player_count} players`
    case 'transfer_requested':
      return `${p.requester} requested ${formatMoney(Number(p.amount))} from ${p.from}${p.reason ? ` (${p.reason})` : ''}`
    case 'transfer_declined':
      return `A ${formatMoney(Number(p.amount))} request was declined`
    case 'jail_free_card':
      return `Drew a get-out-of-jail-free card`
    case 'challenge_failed':
      return `Challenge failed for ${p.property_name} — no purchase`
    case 'bot_added':
      return `${p.name} (bot) joined the game`
    case 'sent_to_jail':
      return 'Sent to jail!'
    case 'house_built': {
      const houseCount = Number(p.houses)
      const label = houseCount >= 5 ? 'a hotel' : `${houseCount} house${houseCount === 1 ? '' : 's'}`
      return `Built on ${p.property_name} — now has ${label} (${formatMoney(Number(p.cost))})`
    }
    case 'house_sold':
      return `Sold a house on ${p.property_name} for ${formatMoney(Number(p.refund))}`
    case 'property_mortgaged':
      return `${p.property_name} mortgaged for ${formatMoney(Number(p.value))}`
    case 'property_unmortgaged':
      return `${p.property_name} unmortgaged (paid ${formatMoney(Number(p.payoff))})`
    case 'auction_started':
      return `🔨 Auction started on ${p.property_name}`
    case 'auction_won':
      return `🔨 ${p.property_name} sold at auction for ${formatMoney(Number(p.amount))}`
    case 'auction_failed':
      return `🔨 No bids — ${p.property_name} stays unowned`
    case 'auction_cancelled':
      return `🔨 Auction on ${p.property_name} cancelled`
    case 'auction_bid':
      return `🔨 New bid: ${formatMoney(Number(p.amount))}`
    case 'auction_passed':
      return `🔨 A player passed on the auction`
    case 'trade_proposed':
      return `🤝 ${p.proposer} proposed a trade to ${p.recipient}`
    case 'trade_accepted':
      return `🤝 Trade between ${p.proposer} and ${p.recipient} completed`
    case 'trade_declined':
      return `🤝 A trade was declined`
    case 'bankruptcy':
      return `💥 ${p.player} went bankrupt (to ${p.creditor})`
    case 'game_over':
      return `🏆 ${p.winner} wins!`
    default:
      return entry.kind
  }
}

export function EventFeed({ entries, emptyLabel }: { entries: EventLogOut[]; emptyLabel: string }) {
  const formatMoney = useFormatMoney()
  const visible = entries.filter((e) => e.kind !== 'turn_ended')
  if (visible.length === 0) {
    return <p className="text-sm font-medium text-ink-soft">{emptyLabel}</p>
  }

  return (
    <ul className="flex flex-col-reverse gap-1.5">
      {visible.map((entry) => (
        <li key={entry.id} className="rounded border-2 border-ink bg-board-card px-3 py-2 text-sm">
          <span className="font-medium text-ink">{describe(entry, formatMoney)}</span>
          <span className="ml-2 text-xs font-medium text-ink-soft">
            {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </li>
      ))}
    </ul>
  )
}
