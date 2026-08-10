import { useEffect, useRef, useState } from 'react'
import { getGame } from '../api/client'
import type { GameStateOut } from '../api/types'

export function useGameSocket(code: string) {
  const [state, setState] = useState<GameStateOut | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    let cancelled = false
    let retryTimer: number | undefined

    getGame(code)
      .then((g) => {
        if (!cancelled) setState(g)
      })
      .catch(() => {})

    function connect() {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const ws = new WebSocket(`${protocol}://${window.location.host}/ws/games/${code}`)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) retryTimer = window.setTimeout(connect, 1500)
      }
      ws.onerror = () => ws.close()
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data)
        if (msg.type === 'state') setState(msg.game)
      }
    }
    connect()

    return () => {
      cancelled = true
      window.clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [code])

  return { state, connected, setState }
}
