import { useCallback, useEffect, useState } from 'react'
import type { UserOut } from '../api/types'

export interface Account {
  user: UserOut
  sessionToken: string
}

const STORAGE_KEY = 'monopoly_os:account'

export function loadAccount(): Account | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Account
  } catch {
    return null
  }
}

export function saveAccount(account: Account) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(account))
}

export function clearAccount() {
  localStorage.removeItem(STORAGE_KEY)
}

// Optional, persistent across games/devices-in-localStorage — distinct from
// `useSession`, which is per-game-code ephemeral player identity. Signing in
// isn't required for anything except owning saved board templates.
export function useAccount() {
  const [account, setAccount] = useState<Account | null>(() => loadAccount())

  useEffect(() => {
    const onStorage = () => setAccount(loadAccount())
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const persist = useCallback((next: Account) => {
    saveAccount(next)
    setAccount(next)
  }, [])

  const logout = useCallback(() => {
    clearAccount()
    setAccount(null)
  }, [])

  return { account, saveAccount: persist, logout }
}
