import { createContext, ReactNode, useContext, useMemo } from "react"
import { TripPlan } from "./types"


interface AppStateValue {
  username: string | null
  plans: TripPlan[]
}

const AppStateContext = createContext<AppStateValue | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const username = "foobar"
  const plans: TripPlan[] = []


  const state = useMemo<AppStateValue>(
    () => ({
      username, plans
    }),
    [username, plans]
  )
  return (
    <AppStateContext.Provider value={state}>
      {children}
    </AppStateContext.Provider>
  )

}

export function useAppState() {
  const val = useContext(AppStateContext)
  if (!val)
    throw new Error("useAppState must be used within AppStateProvider")

  return val
}