import { useState } from 'react'
import { useFormatMoney } from '../hooks/useBoard'
import type { AuctionState, PlayerOut } from '../api/types'

export function AuctionPanel({
  auction,
  players,
  myPlayerId,
  isHost,
  minIncrement,
  busy,
  onBid,
  onPass,
  onCancel,
}: {
  auction: AuctionState
  players: PlayerOut[]
  myPlayerId?: string
  isHost: boolean
  minIncrement: number
  busy: boolean
  onBid: (amount: number) => void
  onPass: () => void
  onCancel: () => void
}) {
  const formatMoney = useFormatMoney()
  const minBid = auction.current_bidder_id ? auction.current_bid + minIncrement : minIncrement
  const [amount, setAmount] = useState(String(minBid))
  const name = (id: string | null) => players.find((p) => p.id === id)?.name ?? '—'

  const iAmEligible = Boolean(myPlayerId && auction.eligible_ids.includes(myPlayerId))
  const iAmHighBidder = myPlayerId === auction.current_bidder_id
  const iHavePassed = Boolean(myPlayerId && auction.passed_ids.includes(myPlayerId))

  return (
    <div className="mb-4 flex flex-col gap-3 rounded border-2 border-ink bg-monopoly-gold p-4 shadow-[3px_3px_0_#1a1a1a]">
      <div className="flex items-center justify-between">
        <h3 className="font-display text-lg tracking-wide text-ink">🔨 Auction: {auction.property_name}</h3>
        {isHost && (
          <button onClick={onCancel} disabled={busy} className="text-xs font-bold text-ink underline decoration-dotted disabled:opacity-50">
            Cancel
          </button>
        )}
      </div>

      <div className="rounded border-2 border-ink bg-board-card p-3">
        <p className="text-xs font-bold uppercase tracking-wide text-ink-soft">Current bid</p>
        <p className="font-mono text-2xl font-bold text-monopoly-green">
          {auction.current_bidder_id ? formatMoney(auction.current_bid) : 'No bids yet'}
        </p>
        {auction.current_bidder_id && <p className="text-sm font-semibold text-ink">by {name(auction.current_bidder_id)}</p>}
      </div>

      <div className="flex flex-wrap gap-1 text-xs font-semibold text-ink">
        {auction.eligible_ids.map((id) => (
          <span
            key={id}
            className={`rounded border border-ink px-2 py-0.5 ${
              auction.passed_ids.includes(id)
                ? 'bg-board-card text-ink-soft line-through'
                : id === auction.current_bidder_id
                  ? 'bg-monopoly-green text-white'
                  : 'bg-board-card'
            }`}
          >
            {name(id)}
          </span>
        ))}
      </div>

      {iAmEligible && !iHavePassed && (
        <div className="flex flex-col gap-2">
          <div className="flex gap-2">
            <input
              type="number"
              min={minBid}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="w-full rounded border-2 border-ink bg-board-card p-2 text-ink focus:outline-none focus:ring-2 focus:ring-monopoly-red"
            />
            <button
              disabled={busy || Number(amount) < minBid}
              onClick={() => onBid(Number(amount))}
              className="whitespace-nowrap rounded border-2 border-ink bg-monopoly-green px-3 py-2 text-sm font-bold text-white hover:bg-monopoly-green-dark disabled:opacity-50"
            >
              Bid
            </button>
          </div>
          <p className="text-xs text-ink">Minimum bid: {formatMoney(minBid)}</p>
          {!iAmHighBidder && (
            <button
              disabled={busy}
              onClick={onPass}
              className="rounded border-2 border-ink bg-board-card py-2 text-sm font-bold text-ink hover:bg-board disabled:opacity-50"
            >
              Pass
            </button>
          )}
        </div>
      )}
      {iHavePassed && <p className="text-sm font-semibold text-ink-soft">You passed — waiting on the others.</p>}
    </div>
  )
}
