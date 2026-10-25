import { useEffect } from "react"
import { Link, useNavigate } from "react-router"
import { Page } from "../components/Layout"
import { useAppState } from "../AppState"
import { Button, Title, Icon, Card, SectionTitle } from "../components/ui"
import { formatDuration, formatMoney } from "../lib/format"
import type { TripPlan } from "../types"

function PlanRow({ plan }: { plan: TripPlan }) {
  const route =
    plan.routes.find((item) => item.id === plan.selectedRouteId) ??
    plan.routes[0]
  return (
    <Link
      to={`/plans/${plan.id}`}
      className="group grid gap-4 rounded-2xl border border-border p-4 transition hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:grid-cols-[1fr_auto] sm:items-center"
    >
      <div className="flex min-w-0 items-start gap-4">
        <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-indigo-50 text-primary">
          <Icon name="road" />
        </span>
        <span className="min-w-0">
          <span className="block truncate text-sm font-extrabold text-foreground">
            {plan.name}
          </span>
          <span className="mt-1 block truncate text-sm text-muted-foreground">
            {plan.trip.originLabel} → {plan.trip.destinationLabel}
          </span>
          <span className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-medium text-muted-foreground">
            <span>
              {plan.vehicle.year} {plan.vehicle.make} {plan.vehicle.model}
            </span>
            <span>
              {plan.trip.passengers}{" "}
              {plan.trip.passengers === 1 ? "passenger" : "passengers"}
            </span>
            <span>
              {new Date(plan.createdAt).toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          </span>
        </span>
      </div>
      {route && (
        <span className="flex items-center justify-between gap-5 sm:justify-end">
          <span className="text-right">
            <span className="block text-lg font-extrabold text-foreground">
              {formatMoney(route.totalCost)}
            </span>
            <span className="block text-xs text-muted-foreground">
              {route.distance} mi · {formatDuration(route.durationMinutes)}
            </span>
          </span>
          <Icon
            name="arrow"
            className="size-5 text-muted-foreground transition group-hover:translate-x-1 group-hover:text-primary"
          />
        </span>
      )}
    </Link>
  )
}

export function DashboardScreen() {
  const { plans, startNewPlan, notice, clearNotice } = useAppState()
  const navigate = useNavigate()
  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(clearNotice, 4000)
    return () => window.clearTimeout(timer)
  }, [clearNotice, notice])

  return (
    <Page>
      {notice && (
        <div
          role="status"
          className="mb-5 flex items-center gap-2 rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700"
        >
          <Icon name="check" className="size-4" /> {notice}
        </div>
      )}
      <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-widest text-primary">
            Your travel workspace
          </div>
          <Title size="hero">Plan the road ahead</Title>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Compare route costs, local prices, and the stops that make every
            trip easier.
          </p>
        </div>
        <Button
          onClick={() => {
            startNewPlan()
            navigate("/plans/new/trip")
          }}
        >
          <Icon name="plus" className="size-4" /> Create new plan
        </Button>
      </div>

      <Card className="p-5 sm:p-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <SectionTitle>Planned travel</SectionTitle>
            <p className="mt-1 text-sm text-muted-foreground">
              {plans.length} trips ready to review
            </p>
          </div>
          <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-primary">
            Saved plans
          </span>
        </div>
        <div className="space-y-3">
          {plans.length ? (
            plans.map((plan) => <PlanRow key={plan.id} plan={plan} />)
          ) : (
            <div className="rounded-2xl border border-dashed border-border p-8 text-center">
              <Icon name="map" className="mx-auto size-8 text-primary" />
              <div className="mt-3 font-bold">No plans yet</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Create your first route to see it here.
              </p>
            </div>
          )}
        </div>
      </Card>
    </Page>
  )
}
