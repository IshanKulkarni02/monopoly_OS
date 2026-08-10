import { useState } from 'react'
import { formatMoney } from '../boardData'
import type { EventLogOut, PlayerOut } from '../api/types'

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
      <form onSubmit={submit} className="flex flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-neutral-400">From</label>
            <select value={from} onChange={(e) => setFrom(e.target.value)} className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-2">
              <option value="">Bank</option>
              {players.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-neutral-400">To</label>
            <select value={to} onChange={(e) => setTo(e.target.value)} className="w-full rounded-lg border border-neutral-700 bg-neutral-950 p-2">
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
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
          />
          <input
            placeholder="Reason (rent, tax, ...)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button disabled={busy} className="rounded-lg bg-amber-700 py-2 font-medium hover:bg-amber-600 disabled:opacity-50">
          Log transaction
        </button>
      </form>

      <div>
        <h3 className="mb-2 text-sm font-medium text-neutral-400">Recent transactions</h3>
        <ul className="flex flex-col gap-1.5">
          {transactions.map((entry) => {
            const p = entry.payload as { from: string; to: string; amount: number; reason: string; transaction_id: string }
            return (
              <li key={entry.id} className="flex items-center justify-between rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-sm">
                <span>{p.from} → {p.to}: {formatMoney(p.amount)} ({p.reason})</span>
                <button
                  onClick={() => onReverse(p.transaction_id)}
                  className="rounded border border-neutral-700 px-2 py-1 text-xs text-neutral-300 hover:bg-neutral-800"
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
