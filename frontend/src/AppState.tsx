import { createContext, ReactNode, useContext, useMemo, useState } from "react"
import { FALLBACK_SPECS } from "./mockData"
import { readStorage, removeStorage, STORAGE_KEYS, writeStorage } from "./lib/storage"
import {
  DraftVehicle,
  RouteId,
  RouteOption,
  TripDetails,
  TripPlan,
} from "./types"

const makeEmptyDraft = (): TripPlan => ({
  version: 1,
  id: "",
  name: "",
  createdAt: new Date().toISOString(),
  draft: true,
  trip: {
    originId: "",
    originLabel: "",
    originLat: null,
    originLng: null,
    destinationId: "",
    destinationLabel: "",
    destinationLat: null,
    destinationLng: null,
    passengers: 1,
    invitedPassengers: [],
  },
  vehicle: { year: "", make: "", model: "", lookupState: "idle", specs: null },
  routes: [],
  selectedRouteId: "",
})

interface AppStateValue {
  username: string | null
  plans: TripPlan[]
  draft: TripPlan
  notice: string
  login: (username: string) => void
  logout: () => void
  startNewPlan: () => void
  updateTrip: (trip: TripDetails) => void
  updateVehicle: (
    vehicle: DraftVehicle | ((current: DraftVehicle) => DraftVehicle),
  ) => void
  acceptFallback: () => void
  selectRoute: (id: RouteId) => void
  setRoutes: (routes: RouteOption[], selectedRouteId: RouteId) => void
  savePlan: (routes: RouteOption[]) => TripPlan | null
  clearNotice: () => void
}

const AppStateContext = createContext<AppStateValue | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(() => {
    const auth = readStorage<{ username?: string; signedIn?: boolean } | null>(
      STORAGE_KEYS.auth,
      null,
    )
    return auth?.signedIn && auth.username ? auth.username : null
  })
  const [customPlans, setCustomPlans] = useState<TripPlan[]>(() => {
    const stored = readStorage<TripPlan[]>(STORAGE_KEYS.plans, [])
    return Array.isArray(stored)
      ? stored.filter((plan) => plan.version === 1 && Array.isArray(plan.routes))
      : []
  })
  const [draft, setDraft] = useState<TripPlan>(makeEmptyDraft)
  const [notice, setNotice] = useState("")

  // Stable identities: effects (e.g. the vehicle lookup) depend on these.
  const actions = useMemo(
    () => ({
      login: (next: string) => {
        const trimmed = next.trim()
        setUsername(trimmed)
        writeStorage(STORAGE_KEYS.auth, { username: trimmed, signedIn: true })
      },
      logout: () => {
        setUsername(null)
        removeStorage(STORAGE_KEYS.auth)
      },
      startNewPlan: () => setDraft(makeEmptyDraft()),
      // Changing the trip or vehicle invalidates any calculated routes.
      updateTrip: (trip: TripDetails) =>
        setDraft((current) => ({ ...current, trip, routes: [] })),
      updateVehicle: (
        vehicle: DraftVehicle | ((current: DraftVehicle) => DraftVehicle),
      ) =>
        setDraft((current) => ({
          ...current,
          vehicle:
            typeof vehicle === "function" ? vehicle(current.vehicle) : vehicle,
          routes: [],
        })),
      acceptFallback: () =>
        setDraft((current) => ({
          ...current,
          vehicle: {
            ...current.vehicle,
            lookupState: "not_found",
            specs: FALLBACK_SPECS,
          },
          routes: [],
        })),
      selectRoute: (id: RouteId) =>
        setDraft((current) => ({ ...current, selectedRouteId: id })),
      setRoutes: (routes: RouteOption[], selectedRouteId: RouteId) =>
        setDraft((current) => ({ ...current, routes, selectedRouteId })),
      clearNotice: () => setNotice(""),
    }),
    [],
  )

  const state = useMemo<AppStateValue>(
    () => ({
      username,
      plans: customPlans,
      draft,
      notice,
      ...actions,
      savePlan: (routes) => {
        if (!routes.length) return null
        const from = draft.trip.originLabel.split(",")[0]
        const to = draft.trip.destinationLabel.split(",")[0]
        const plan: TripPlan = {
          ...draft,
          draft: false,
          id: `plan-${Date.now()}`,
          name: `${from} to ${to}`,
          createdAt: new Date().toISOString(),
          routes,
          selectedRouteId: routes.some((r) => r.id === draft.selectedRouteId)
            ? draft.selectedRouteId
            : routes[0].id,
        }
        const next = [...customPlans, plan]
        setCustomPlans(next)
        writeStorage(STORAGE_KEYS.plans, next)
        setNotice("Your trip plan was saved.")
        return plan
      },
    }),
    [username, customPlans, draft, notice, actions],
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
