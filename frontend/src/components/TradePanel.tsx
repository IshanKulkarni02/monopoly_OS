import { useState } from 'react'
import { useFormatMoney } from '../hooks/useBoard'
import type { ProposeTradeInput } from '../api/client'
import type { PlayerOut, PropertyOut, TradeOut } from '../api/types'

const fieldClass = 'w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red'

function describeTradeSide(cash: number, propertyCount: number, formatMoney: (amount: number) => string): string {
  const parts: string[] = []
  if (cash > 0) parts.push(formatMoney(cash))
  if (propertyCount > 0) parts.push(`${propertyCount} propert${propertyCount === 1 ? 'y' : 'ies'}`)
  return parts.length > 0 ? parts.join(' + ') : 'nothing'
}

function PropertyChecklist({
  properties,
  selected,
  onToggle,
}: {
  properties: PropertyOut[]
  selected: string[]
  onToggle: (id: string) => void
}) {
  if (properties.length === 0) return <p className="text-xs text-ink-soft">No properties</p>
  return (
    <div className="flex max-h-32 flex-col gap-1 overflow-y-auto rounded border-2 border-ink bg-board-card p-2">
      {properties.map((p) => (
        <label key={p.id} className="flex items-center gap-2 text-sm text-ink">
          <input type="checkbox" checked={selected.includes(p.id)} onChange={() => onToggle(p.id)} />
          {p.name} {p.mortgaged && <span className="text-xs text-ink-soft">(mortgaged)</span>}
        </label>
      ))}
    </div>
  )
}

export function TradePanel({
  players,
  properties,
  myPlayerId,
  pendingTrades,
  busy,
  error,
  onPropose,
  onAccept,
  onDecline,
  onCancel,
  onDeclareBankruptcy,
}: {
  players: PlayerOut[]
  properties: PropertyOut[]
  myPlayerId: string
  pendingTrades: TradeOut[]
  busy: boolean
  error: string | null
  onPropose: (input: ProposeTradeInput) => void
  onAccept: (tradeId: string) => void
  onDecline: (tradeId: string) => void
  onCancel: (tradeId: string) => void
  onDeclareBankruptcy: (creditorPlayerId: string | null) => void
}) {
  const formatMoney = useFormatMoney()
  const others = players.filter((p) => p.id !== myPlayerId && p.status === 'active')
  const [recipientId, setRecipientId] = useState(others[0]?.id ?? '')
  const [offerCash, setOfferCash] = useState('0')
  const [offerProps, setOfferProps] = useState<string[]>([])
  const [requestCash, setRequestCash] = useState('0')
  const [requestProps, setRequestProps] = useState<string[]>([])
  const [creditorId, setCreditorId] = useState('')
  const [confirmingBankruptcy, setConfirmingBankruptcy] = useState(false)

  const myProperties = properties.filter((p) => p.owner_id === myPlayerId)
  const theirProperties = properties.filter((p) => p.owner_id === recipientId)
  const playerName = (id: string) => players.find((p) => p.id === id)?.name ?? 'Unknown'

  function toggle(list: string[], setList: (ids: string[]) => void, id: string) {
    setList(list.includes(id) ? list.filter((x) => x !== id) : [...list, id])
  }

  function submitProposal(e: React.FormEvent) {
    e.preventDefault()
    if (!recipientId) return
    onPropose({
      recipientId,
      offerCash: Number(offerCash) || 0,
      offerPropertyIds: offerProps,
      requestCash: Number(requestCash) || 0,
      requestPropertyIds: requestProps,
    })
    setOfferCash('0')
    setOfferProps([])
    setRequestCash('0')
    setRequestProps([])
  }

  const myTrades = pendingTrades.filter((t) => t.proposer_id === myPlayerId || t.recipient_id === myPlayerId)

  return (
    <div className="flex flex-col gap-4">
      {others.length === 0 ? (
        <p className="text-sm text-ink-soft">No one else to trade with.</p>
      ) : (
        <form onSubmit={submitProposal} className="flex flex-col gap-3 rounded border-2 border-ink bg-board-card p-3">
          <h3 className="text-xs font-bold uppercase tracking-wide text-ink-soft">Propose a trade</h3>
          <div>
            <label className="text-xs font-bold uppercase tracking-wide text-ink-soft">With</label>
            <select
              value={recipientId}
              onChange={(e) => {
                setRecipientId(e.target.value)
                setRequestProps([])
              }}
              className={fieldClass}
            >
              {others.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex flex-col gap-1">
              <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">You offer</p>
              <input type="number" min={0} value={offerCash} onChange={(e) => setOfferCash(e.target.value)} className={fieldClass} placeholder="Cash" />
              <PropertyChecklist properties={myProperties} selected={offerProps} onToggle={(id) => toggle(offerProps, setOfferProps, id)} />
            </div>
            <div className="flex flex-col gap-1">
              <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">You request</p>
              <input type="number" min={0} value={requestCash} onChange={(e) => setRequestCash(e.target.value)} className={fieldClass} placeholder="Cash" />
              <PropertyChecklist properties={theirProperties} selected={requestProps} onToggle={(id) => toggle(requestProps, setRequestProps, id)} />
            </div>
          </div>

          {error && <p className="text-sm font-semibold text-monopoly-red">{error}</p>}
          <button disabled={busy} className="rounded border-2 border-ink bg-monopoly-gold py-2 font-bold text-ink hover:bg-monopoly-gold-dark disabled:opacity-50">
            Propose trade
          </button>
        </form>
      )}

      {myTrades.length > 0 && (
        <div>
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-ink-soft">Pending trades</h3>
          <ul className="flex flex-col gap-2">
            {myTrades.map((t) => {
              const iAmRecipient = t.recipient_id === myPlayerId
              return (
                <li key={t.id} className="flex flex-col gap-1.5 rounded border-2 border-ink bg-board-card p-3 text-sm">
                  <p className="text-ink">
                    {playerName(t.proposer_id)} → {playerName(t.recipient_id)}: offers {describeTradeSide(t.offer_cash, t.offer_property_ids.length, formatMoney)}{' '}
                    for {describeTradeSide(t.request_cash, t.request_property_ids.length, formatMoney)}
                  </p>
                  <div className="flex gap-2">
                    {iAmRecipient ? (
                      <>
                        <button onClick={() => onAccept(t.id)} disabled={busy} className="rounded border-2 border-ink bg-monopoly-green px-3 py-1 text-xs font-bold text-white disabled:opacity-50">
                          Accept
                        </button>
                        <button onClick={() => onDecline(t.id)} disabled={busy} className="rounded border-2 border-ink px-3 py-1 text-xs font-bold text-ink hover:bg-board disabled:opacity-50">
                          Decline
                        </button>
                      </>
                    ) : (
                      <button onClick={() => onCancel(t.id)} disabled={busy} className="rounded border-2 border-ink px-3 py-1 text-xs font-bold text-ink hover:bg-board disabled:opacity-50">
                        Cancel
                      </button>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="rounded border-2 border-monopoly-red bg-board-card p-3">
        <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-monopoly-red">Danger zone</h3>
        {!confirmingBankruptcy ? (
          <button onClick={() => setConfirmingBankruptcy(true)} className="text-sm font-bold text-monopoly-red hover:underline">
            Declare bankruptcy…
          </button>
        ) : (
          <div className="flex flex-col gap-2">
            <p className="text-sm text-ink">
              This sells your houses, mortgages everything you own, hands over what that raises, and takes you out of the game. Who gets it?
            </p>
            <select value={creditorId} onChange={(e) => setCreditorId(e.target.value)} className={fieldClass}>
              <option value="">The bank</option>
              {others.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <div className="flex gap-2">
              <button
                disabled={busy}
                onClick={() => {
                  onDeclareBankruptcy(creditorId || null)
                  setConfirmingBankruptcy(false)
                }}
                className="rounded border-2 border-ink bg-monopoly-red px-3 py-2 text-sm font-bold text-white hover:bg-monopoly-red-dark disabled:opacity-50"
              >
                Confirm bankruptcy
              </button>
              <button onClick={() => setConfirmingBankruptcy(false)} className="rounded border-2 border-ink px-3 py-2 text-sm font-bold text-ink hover:bg-board">
                Never mind
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
