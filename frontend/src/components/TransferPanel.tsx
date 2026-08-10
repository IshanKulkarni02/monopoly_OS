import { useState } from 'react'
import { formatMoney } from '../boardData'
import type { PlayerOut, TransactionOut } from '../api/types'

export function TransferPanel({
  players,
  myPlayerId,
  pendingTransfers,
  busy,
  error,
  onSend,
  onRequest,
  onConfirm,
  onDecline,
}: {
  players: PlayerOut[]
  myPlayerId: string
  pendingTransfers: TransactionOut[]
  busy: boolean
  error: string | null
  onSend: (input: { otherPlayerId: string; amount: number; reason: string }) => void
  onRequest: (input: { otherPlayerId: string; amount: number; reason: string }) => void
  onConfirm: (transactionId: string) => void
  onDecline: (transactionId: string) => void
}) {
  const others = players.filter((p) => p.id !== myPlayerId)
  const [mode, setMode] = useState<'send' | 'request'>('send')
  const [otherPlayerId, setOtherPlayerId] = useState(others[0]?.id ?? '')
  const [amount, setAmount] = useState('')
  const [reason, setReason] = useState('')

  const awaitingMe = pendingTransfers.filter((t) => t.from_player_id === myPlayerId)
  const awaitingOthers = pendingTransfers.filter((t) => t.to_player_id === myPlayerId && t.from_player_id !== myPlayerId)
  const playerName = (id: string | null) => players.find((p) => p.id === id)?.name ?? 'Unknown'

  function submit(e: React.FormEvent) {
    e.preventDefault()
    const amt = Number(amount)
    if (!amt || amt <= 0 || !otherPlayerId) return
    const input = { otherPlayerId, amount: amt, reason }
    if (mode === 'send') onSend(input)
    else onRequest(input)
    setAmount('')
    setReason('')
  }

  return (
    <div className="flex flex-col gap-4">
      {awaitingMe.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-amber-400">Waiting on you to confirm</h3>
          {awaitingMe.map((t) => (
            <div key={t.id} className="flex items-center justify-between rounded-lg border border-amber-800 bg-amber-950/30 px-3 py-2">
              <span className="text-sm">
                {playerName(t.to_player_id)} is requesting {formatMoney(t.amount)}
                {t.reason ? ` (${t.reason})` : ''}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={busy}
                  onClick={() => onConfirm(t.id)}
                  className="rounded bg-emerald-700 px-2 py-1 text-xs font-medium hover:bg-emerald-600"
                >
                  Confirm
                </button>
                <button
                  disabled={busy}
                  onClick={() => onDecline(t.id)}
                  className="rounded border border-neutral-700 px-2 py-1 text-xs hover:bg-neutral-800"
                >
                  Decline
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {awaitingOthers.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-sm font-medium text-neutral-400">Your pending requests</h3>
          {awaitingOthers.map((t) => (
            <div key={t.id} className="rounded-lg border border-neutral-800 bg-neutral-900/60 px-3 py-2 text-sm">
              Waiting on {playerName(t.from_player_id)} for {formatMoney(t.amount)}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={submit} className="flex flex-col gap-2 rounded-xl border border-neutral-800 bg-neutral-900 p-3">
        <div className="flex rounded-lg border border-neutral-700 p-1">
          <button
            type="button"
            onClick={() => setMode('send')}
            className={`flex-1 rounded py-1.5 text-sm font-medium ${mode === 'send' ? 'bg-emerald-700' : 'text-neutral-400'}`}
          >
            Send
          </button>
          <button
            type="button"
            onClick={() => setMode('request')}
            className={`flex-1 rounded py-1.5 text-sm font-medium ${mode === 'request' ? 'bg-emerald-700' : 'text-neutral-400'}`}
          >
            Request
          </button>
        </div>
        <select
          value={otherPlayerId}
          onChange={(e) => setOtherPlayerId(e.target.value)}
          className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
        >
          {others.map((p) => (
            <option key={p.id} value={p.id}>
              {mode === 'send' ? `Pay ${p.name}` : `Request from ${p.name}`}
            </option>
          ))}
        </select>
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
            placeholder="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="rounded-lg border border-neutral-700 bg-neutral-950 p-2"
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <button disabled={busy || !otherPlayerId} className="rounded-lg bg-emerald-700 py-2 font-medium hover:bg-emerald-600 disabled:opacity-50">
          {mode === 'send' ? 'Send money' : 'Request money'}
        </button>
      </form>
    </div>
  )
}
