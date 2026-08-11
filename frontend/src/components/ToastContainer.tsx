import { useEffect, useRef, useState } from 'react'
import { describe } from './EventFeed'
import { useFormatMoney } from '../hooks/useBoard'
import type { EventLogOut } from '../api/types'

const NOTIFY_KINDS = new Set([
  'auction_started', 'auction_won', 'auction_failed', 'auction_cancelled',
  'trade_proposed', 'trade_accepted',
  'bankruptcy', 'game_over', 'sent_to_jail', 'house_built',
])

const TOAST_LIFETIME_MS = 5000

export function ToastContainer({ entries }: { entries: EventLogOut[] }) {
  const formatMoney = useFormatMoney()
  const [toasts, setToasts] = useState<{ id: string; text: string }[]>([])
  const seenIds = useRef<Set<string> | null>(null)

  useEffect(() => {
    if (seenIds.current === null) {
      // First render after mount (or after a reload): these entries are
      // history, not news — remember them without toasting the whole feed.
      seenIds.current = new Set(entries.map((e) => e.id))
      return
    }
    const fresh = entries.filter((e) => !seenIds.current!.has(e.id))
    fresh.forEach((e) => seenIds.current!.add(e.id))
    const worthNotifying = fresh.filter((e) => NOTIFY_KINDS.has(e.kind))
    if (worthNotifying.length === 0) return

    const newToasts = worthNotifying.map((e) => ({ id: e.id, text: describe(e, formatMoney) }))
    setToasts((prev) => [...prev, ...newToasts])
    newToasts.forEach((t) => {
      setTimeout(() => setToasts((prev) => prev.filter((x) => x.id !== t.id)), TOAST_LIFETIME_MS)
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries])

  if (toasts.length === 0) return null

  return (
    <div className="pointer-events-none fixed left-1/2 top-4 z-50 flex w-full max-w-md -translate-x-1/2 flex-col gap-2 px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          className="pointer-events-auto rounded border-2 border-ink bg-ink px-4 py-2 text-center text-sm font-bold text-white shadow-[3px_3px_0_#1a1a1a]"
        >
          {t.text}
        </div>
      ))}
    </div>
  )
}
