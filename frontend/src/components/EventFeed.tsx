import { formatMoney } from '../boardData'
import type { EventLogOut } from '../api/types'

function describe(entry: EventLogOut): string {
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
    default:
      return entry.kind
  }
}

export function EventFeed({ entries, emptyLabel }: { entries: EventLogOut[]; emptyLabel: string }) {
  if (entries.length === 0) {
    return <p className="text-sm text-neutral-500">{emptyLabel}</p>
  }

  return (
    <ul className="flex flex-col-reverse gap-1.5">
      {entries.map((entry) => (
        <li key={entry.id} className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-sm">
          <span className="text-neutral-200">{describe(entry)}</span>
          <span className="ml-2 text-xs text-neutral-500">
            {new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </li>
      ))}
    </ul>
  )
}
