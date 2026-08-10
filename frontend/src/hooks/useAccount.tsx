import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'
import type { UserOut } from '../api/types'

export interface Account {
  user: UserOut
  sessionToken: string
}

const STORAGE_KEY = 'monopoly_os:account'

function loadAccount(): Account | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as Account
  } catch {
    return null
  }
}

interface AccountContextValue {
  account: Account | null
  saveAccount: (account: Account) => void
  logout: () => void
}

const AccountContext = createContext<AccountContextValue | null>(null)

// A React state hook (not just a localStorage wrapper) needs a single shared
// instance — two independent `useState(() => loadAccount())` calls in
// sibling/parent components (e.g. the sign-in form and the page around it)
// never learn about each other's writes: the browser's `storage` event only
// fires in *other* tabs, never the one that made the change. Context is what
// makes "sign in here" immediately visible "use it over there" in the same tab.
export function AccountProvider({ children }: { children: ReactNode }) {
  const [account, setAccount] = useState<Account | null>(() => loadAccount())

  const saveAccountFn = useCallback((next: Account) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setAccount(next)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setAccount(null)
  }, [])

  return <AccountContext.Provider value={{ account, saveAccount: saveAccountFn, logout }}>{children}</AccountContext.Provider>
}

export function useAccount(): AccountContextValue {
  const ctx = useContext(AccountContext)
  if (!ctx) throw new Error('useAccount() must be used within an <AccountProvider>')
  return ctx
}
