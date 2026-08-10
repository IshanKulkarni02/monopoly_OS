import { useState } from 'react'
import { formatMoney } from '../boardData'
import type { EventLogOut, PlayerOut } from '../api/types'

const fieldClass = 'w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red'

export function BankerPanel({
  players,
  recentLog,
  busy,
  error,
  onLogTransaction,
  onReverse,
}: {
  players: PlayerOut[]
  recentLog: EventLogOut[]
  busy: boolean
  error: string | null
  onLogTransaction: (input: { fromPlayerId: string | null; toPlayerId: string | null; amount: number; reason: string }) => void
  onReverse: (transactionId: string) => void
}) {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')

  const transactions = recentLog.filter((e) => e.kind === 'transaction').slice(-15).reverse()

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const amt = Number(amount)
    if (!amt || amt <= 0) return
    onLogTransaction({ fromPlayerId: from || null, toPlayerId: to || null, amount: amt, reason })
    setAmount('')
    setReason('')
  }

  return (
    <div className="flex flex-col gap-4">
      <form onSubmit={submit} className="flex flex-col gap-2 rounded border-2 border-ink bg-board-card p-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">From</label>
            <select value={from} onChange={(e) => setFrom(e.target.value)} className={fieldClass}>
              <option value="">Bank</option>
              {players.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">To</label>
            <select value={to} onChange={(e) => setTo(e.target.value)} className={fieldClass}>
              <option value="">Bank</option>
              {players.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input
            type="number"
            min={1}
            placeholder="Amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className={fieldClass}
          />
          <input
            placeholder="Reason (rent, tax, ...)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className={fieldClass}
          />
        </div>
        {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
        <button disabled={busy} className="rounded border-2 border-ink bg-monopoly-gold py-2 font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50">
          Log transaction
        </button>
      </form>

      <div>
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Recent transactions</h3>
        <ul className="flex flex-col gap-1.5">
          {transactions.map((entry) => {
            const p = entry.payload as { from: string; to: string; amount: number; reason: string; transaction_id: string }
            return (
              <li key={entry.id} className="flex items-center justify-between rounded border-2 border-ink bg-board-card px-3 py-2 text-sm">
                <span className="font-medium text-ink">
                  {p.from} → {p.to}: {formatMoney(p.amount)} ({p.reason})
                </span>
                <button
                  onClick={() => onReverse(p.transaction_id)}
                  className="rounded border-2 border-ink px-2 py-1 text-xs font-bold text-ink hover:bg-board"
                >
                  Reverse
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}
