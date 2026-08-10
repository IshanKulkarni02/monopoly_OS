import { QRCodeSVG } from 'qrcode.react'

export function JoinCodeBadge({ code }: { code: string }) {
  const joinUrl = `${window.location.origin}/g/${code}`

  return (
    <div className="flex flex-col items-center gap-3 rounded-2xl border border-neutral-800 bg-neutral-900 p-6">
      <span className="text-sm uppercase tracking-widest text-neutral-400">Join code</span>
      <span className="font-mono text-5xl font-bold tracking-[0.2em] text-emerald-400">{code}</span>
      <div className="rounded-lg bg-white p-3">
        <QRCodeSVG value={joinUrl} size={144} />
      </div>
      <span className="max-w-[220px] break-all text-center text-xs text-neutral-500">{joinUrl}</span>
    </div>
  )
}
