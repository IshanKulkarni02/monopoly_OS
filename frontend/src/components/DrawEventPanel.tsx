import { useState } from 'react'
import { useBoard, useFormatMoney } from '../hooks/useBoard'
import type { DrawEventOutcome, EventSystem } from '../api/types'

function outcomeMessage(outcome: DrawEventOutcome, formatMoney: (amount: number) => string): string {
  switch (outcome.kind) {
    case 'bank_pays':
      return `${outcome.text} Bank pays you ${formatMoney(outcome.amount)}.`
    case 'pay_bank':
      return `${outcome.text} You pay the bank ${formatMoney(outcome.amount)}.`
    case 'pay_each_player':
      return `${outcome.text} You pay each other player ${formatMoney(outcome.amount)}.`
    case 'collect_each_player':
      return `${outcome.text} You collect ${formatMoney(outcome.amount)} from each other player.`
    case 'jail_free':
      return `${outcome.text} You now hold a get-out-of-jail-free card.`
    case 'pass_go':
      return `${outcome.text} You collect ${formatMoney(outcome.amount)} for passing GO.`
    default:
      return outcome.text || 'Nothing happens.'
  }
}

export function DrawEventPanel({
  eventSystem,
  busy,
  lastOutcome,
  onDraw,
}: {
  eventSystem: EventSystem
  busy: boolean
  lastOutcome: DrawEventOutcome | null
  onDraw: (spaceIndex: number) => void
}) {
  const formatMoney = useFormatMoney()
  const { tiles } = useBoard()
  const eventTiles = tiles.filter((t) => t.kind === 'mystery')
  const [spaceIndex, setSpaceIndex] = useState(eventTiles[0]?.position ?? 0)

  return (
    <div className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-3">
      <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">
        {eventSystem === 'wheel' ? 'Spin the wheel for…' : 'Draw a card for…'}
      </label>
      <select
        value={spaceIndex}
        onChange={(e) => setSpaceIndex(Number(e.target.value))}
        className="w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
      >
        {eventTiles.map((t) => (
          <option key={t.position} value={t.position}>
            {t.name} (space {t.position})
          </option>
        ))}
      </select>
      <button
        disabled={busy}
        onClick={() => onDraw(spaceIndex)}
        className="rounded border-2 border-ink bg-monopoly-gold py-2 font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50"
      >
        {eventSystem === 'wheel' ? 'Spin' : 'Draw card'}
      </button>
      {lastOutcome && <p className="text-sm font-semibold text-ink">{outcomeMessage(lastOutcome, formatMoney)}</p>}
    </div>
  )
}
