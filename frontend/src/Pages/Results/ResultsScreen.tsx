import { useEffect, useState } from "react"
import { Navigate, useNavigate, useParams } from "react-router"
import { useAppState } from "../../AppState"
import { Button, Card, Icon, Title } from "../../components/ui"
import { Page, WizardShell } from "../../components/Layout"
import { optimizeTrip, type OptimizeProgress } from "../../lib/optimizeApi"
import type { RouteId } from "../../types"
import { CostBreakdown } from "./CostBreakdown"
import { CostSummary } from "./CostSummary"
import { RecommendedStops } from "./RecommendedStops"
import { RouteMap } from "./RouteMap"
import { RouteOptionPicker } from "./RouteOptionPicker"
import { StopsList } from "./StopsList"

export function ResultsScreen() {
  const { planId } = useParams()
  const { plans, draft, selectRoute, setRoutes, savePlan } = useAppState()
  const navigate = useNavigate()
  const saved = Boolean(planId)
  const plan = saved ? (plans.find((item) => item.id === planId) ?? null) : draft
  const routes = plan?.routes ?? []

  const [savedRouteId, setSavedRouteId] = useState<RouteId | null>(null)
  const [progress, setProgress] = useState<OptimizeProgress>({ stage: "queued", progress: 0 })
  const [failure, setFailure] = useState("")
  const [attempt, setAttempt] = useState(0)

  const { trip: draftTrip, vehicle: draftVehicle } = draft
  const needsCalculation = !saved && routes.length === 0
  useEffect(() => {
    const specs = draftVehicle.specs
    const { originLat, originLng, destinationLat, destinationLng } = draftTrip
    if (
      !needsCalculation ||
      !specs ||
      originLat == null ||
      originLng == null ||
      destinationLat == null ||
      destinationLng == null
    )
      return
    const controller = new AbortController()
    // Deferred so React Strict Mode's mount/unmount/mount doesn't start two jobs.
    const timer = window.setTimeout(() => {
      setFailure("")
      setProgress({ stage: "queued", progress: 0 })
      optimizeTrip(
        { lat: originLat, lng: originLng },
        { lat: destinationLat, lng: destinationLng },
        specs,
        { signal: controller.signal, onProgress: setProgress },
      )
        .then((result) => setRoutes(result.routes, result.recommendedRouteId))
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setFailure(
            error instanceof Error ? error.message : "Something went wrong.",
          )
        })
    }, 0)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [needsCalculation, draftTrip, draftVehicle.specs, attempt, setRoutes])

  if (!plan)
    return (
      <Page className="max-w-xl">
        <Card className="p-8 text-center">
          <Icon name="map" className="mx-auto size-9 text-primary" />
          <div className="mt-4">
            <Title>Plan not found</Title>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            This saved plan may no longer be available.
          </p>
          <Button className="mt-6" onClick={() => navigate("/dashboard")}>
            Back to dashboard
          </Button>
        </Card>
      </Page>
    )

  const { trip, vehicle } = plan
  const originPoint =
    trip.originLat != null && trip.originLng != null
      ? { lat: trip.originLat, lng: trip.originLng }
      : null
  const destinationPoint =
    trip.destinationLat != null && trip.destinationLng != null
      ? { lat: trip.destinationLat, lng: trip.destinationLng }
      : null

  if (!originPoint || !destinationPoint)
    return <Navigate to="/plans/new/trip" replace />
  if (!vehicle.specs) return <Navigate to="/plans/new/vehicle" replace />
  const selectedRouteId = saved
    ? (savedRouteId ?? plan.selectedRouteId)
    : plan.selectedRouteId
  const route = routes.find((item) => item.id === selectedRouteId) ?? routes[0]
  if (!route) {
    return (
      <WizardShell>
        <CalculationStatus
          progress={progress}
          failure={failure}
          onRetry={() => setAttempt((n) => n + 1)}
          onBack={() => navigate("/plans/new/vehicle")}
        />
      </WizardShell>
    )
  }
  const routeNumber = routes.indexOf(route) + 1
  const chooseRoute = (id: RouteId) =>
    saved ? setSavedRouteId(id) : selectRoute(id)
  const isEv = vehicle.specs.type === "ev"
  const content = (
    <>
      <div className="mb-7 flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-widest text-primary">
            {saved ? "Saved travel plan" : "Your trip estimate"}
          </div>
          <Title size="hero">
            {trip.originLabel.split(",")[0]} to {trip.destinationLabel.split(",")[0]}
          </Title>
          <p className="mt-2 text-sm text-muted-foreground">
            {vehicle.year} {vehicle.make} {vehicle.model} · {trip.passengers}{" "}
            {trip.passengers === 1 ? "passenger" : "passengers"}
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          {saved ? (
            <>
              <Button variant="secondary" onClick={() => navigate("/dashboard")}>
                Back to dashboard
              </Button>
              <Button
                onClick={() =>
                  navigate(`/plans/${plan.id}/split`, {
                    state: { routeId: route.id },
                  })
                }
              >
                <Icon name="people" className="size-4" />
                Split costs
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="secondary"
                onClick={() => navigate("/plans/new/vehicle")}
              >
                Back to vehicle
              </Button>
              <Button
                onClick={() => {
                  const result = savePlan(routes)
                  if (result) navigate(`/plans/${result.id}`)
                }}
              >
                <Icon name="check" className="size-4" /> Save plan
              </Button>
            </>
          )}
        </div>
      </div>

      <RouteOptionPicker
        routes={routes}
        selectedRouteId={route.id}
        onSelect={chooseRoute}
      />

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1.65fr)_minmax(19rem,0.75fr)]">
        <div className="space-y-5">
          <RouteMap
            origin={originPoint}
            destination={destinationPoint}
            originLabel={trip.originLabel}
            destinationLabel={trip.destinationLabel}
            polyline={route.polyline}
            stops={route.stops}
          />
          <CostSummary
            route={route}
            passengers={trip.passengers}
            isEv={isEv}
          />
          <CostBreakdown route={route} routeNumber={routeNumber} isEv={isEv} />
        </div>
        <div className="space-y-5">
          <StopsList stops={route.stops} />
          <RecommendedStops />
        </div>
      </div>
    </>
  )
  return saved ? <Page>{content}</Page> : <WizardShell>{content}</WizardShell>
}

const STAGE_LABELS: Record<OptimizeProgress["stage"], string> = {
  queued: "Getting started",
  routing: "Finding routes",
  pricing: "Checking prices at stations along each route",
  optimizing: "Planning the cheapest stops",
  done: "Almost there",
}

function CalculationStatus({
  progress,
  failure,
  onRetry,
  onBack,
}: {
  progress: OptimizeProgress
  failure: string
  onRetry: () => void
  onBack: () => void
}) {
  if (failure)
    return (
      <Card className="p-8 text-center">
        <Icon name="road" className="mx-auto size-9 text-rose-500" />
        <div className="mt-4">
          <Title>We couldn’t calculate this trip</Title>
        </div>
        <p role="alert" className="mt-2 text-sm text-muted-foreground">
          {failure}
        </p>
        <div className="mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button variant="secondary" onClick={onBack}>
            Back to vehicle
          </Button>
          <Button onClick={onRetry}>Try again</Button>
        </div>
      </Card>
    )
  return (
    <Card className="p-8 text-center">
      <Icon name="map" className="mx-auto size-9 text-primary" />
      <div className="mt-4">
        <Title>Calculating your trip</Title>
      </div>
      <p role="status" className="mt-2 text-sm text-muted-foreground">
        {STAGE_LABELS[progress.stage]}…
      </p>
      <div className="mx-auto mt-6 h-2 max-w-sm overflow-hidden rounded-full bg-muted">
        <div
          className="gradient-primary h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.max(5, Math.round(progress.progress * 100))}%` }}
        />
      </div>
    </Card>
  )
}
