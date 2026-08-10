import { QRCodeSVG } from 'qrcode.react'

export function JoinCodeBadge({ code }: { code: string }) {
  const joinUrl = `${window.location.origin}/g/${code}`

  return (
    <div className="flex flex-col items-center gap-3 rounded border-4 border-ink bg-board-card p-6 shadow-[4px_4px_0_#1a1a1a]">
      <span className="text-xs font-bold uppercase tracking-widest text-ink-soft">Join code</span>
      <span className="font-display text-5xl tracking-[0.15em] text-monopoly-red">{code}</span>
      <div className="rounded border-2 border-ink bg-white p-3">
        <QRCodeSVG value={joinUrl} size={144} />
      </div>
      <span className="max-w-[220px] break-all text-center text-xs font-medium text-ink-soft">{joinUrl}</span>
    </div>
  )
}
