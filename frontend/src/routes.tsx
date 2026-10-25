import { createBrowserRouter, Navigate, Outlet, useLocation } from "react-router"
import { useAppState } from "./AppState"
import { LoginScreen } from "./pages/Login"
import { DashboardScreen } from "./pages/Dashboard"
import { TripDetailsScreen } from "./pages/TripDetails"
import { VehicleScreen } from "./pages/Vehicle/VehicleScreen"
import { ResultsScreen } from "./pages/Results/ResultsScreen"
import { CostSplitScreen } from "./pages/CostSplit"
import { NotFoundScreen } from "./pages/NotFound"

function HomeRedirect() {
  const { username } = useAppState()
  return <Navigate to={username ? "/dashboard" : "/login"} replace />
}

function AuthGuard() {
  const { username } = useAppState()
  const location = useLocation()
  return username ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace state={{ from: location.pathname }} />
  )
}

function VehicleGuard() {
  const { draft } = useAppState()
  const { originId, destinationId } = draft.trip
  return originId && destinationId && originId !== destinationId ? (
    <VehicleScreen />
  ) : (
    <Navigate to="/plans/new/trip" replace />
  )
}

function DraftResultsGuard() {
  const { draft } = useAppState()
  const { originId, destinationId } = draft.trip
  if (!originId || !destinationId || originId === destinationId)
    return <Navigate to="/plans/new/trip" replace />
  if (!draft.vehicle.specs) return <Navigate to="/plans/new/vehicle" replace />
  return <ResultsScreen />
}

export const router = createBrowserRouter([
  { path: "/", Component: HomeRedirect },
  { path: "/login", Component: LoginScreen },
  {
    Component: AuthGuard,
    children: [
      { path: "/dashboard", Component: DashboardScreen },
      { path: "/plans/new/trip", Component: TripDetailsScreen },
      { path: "/plans/new/vehicle", Component: VehicleGuard },
      { path: "/plans/new/results", Component: DraftResultsGuard },
      { path: "/plans/:planId/split", Component: CostSplitScreen },
      { path: "/plans/:planId", Component: ResultsScreen },
      { path: "*", Component: NotFoundScreen },
    ],
  },
])
