import { useCallback, useEffect, useState } from 'react'

export interface Session {
  code: string
  playerId: string
  playerToken: string
  playerName: string
  hostToken?: string
}

function storageKey(code: string) {
  return `monopoly_os:${code.toUpperCase()}`
}

export function loadSession(code: string): Session | null {
  const raw = localStorage.getItem(storageKey(code))
  if (!raw) return null
  try {
    return JSON.parse(raw) as Session
  } catch {
    return null
  }
}

export function saveSession(session: Session) {
  localStorage.setItem(storageKey(session.code), JSON.stringify(session))
}

export function clearSession(code: string) {
  localStorage.removeItem(storageKey(code))
}

export function useSession(code: string) {
  const [session, setSession] = useState<Session | null>(() => loadSession(code))

  useEffect(() => {
    setSession(loadSession(code))
  }, [code])

  const persist = useCallback((next: Session) => {
    saveSession(next)
    setSession(next)
  }, [])

  return { session, saveSession: persist }
}
