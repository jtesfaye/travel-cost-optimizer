import { useState } from "react"
import { useLocation, useNavigate, useParams } from "react-router"
import { useAppState } from "../AppState"
import { Page } from "../components/Layout"
import { Button, Card, Icon, SectionTitle, Title } from "../components/ui"
import type { RouteId } from "../types"

// TODO: UI preview only; sending split requests needs a backend.
export function CostSplitScreen() {
  const { planId } = useParams()
  const { plans, username } = useAppState()
  const navigate = useNavigate()
  const location = useLocation()
  const [requestsSent, setRequestsSent] = useState(false)
  const plan = plans.find((item) => item.id === planId)

  if (!plan) {
    return (
      <Page className="max-w-xl">
        <Card className="p-8 text-center">
          <Icon name="people" className="mx-auto size-9 text-primary" />
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
  }

  const requestedRouteId = (location.state as { routeId?: RouteId } | null)
    ?.routeId
  const route =
    plan.routes.find(
      (item) => item.id === (requestedRouteId ?? plan.selectedRouteId),
    ) ?? plan.routes[0]
  if (!route) return null
  const routeNumber = plan.routes.findIndex((item) => item.id === route.id) + 1

  const invitedPassengers = plan.trip.invitedPassengers ?? []
  const participants = Array.from(
    { length: plan.trip.passengers },
    (_, index) => {
      if (index === 0) {
        return {
          id: "organizer",
          name: username || "You",
          username: "Trip organizer",
          avatarUrl: "",
        }
      }
      const passenger = invitedPassengers[index - 1]
      return (
        passenger ?? {
          id: `passenger-${index}`,
          name: `Passenger ${index + 1}`,
          username: "Invited traveler",
          avatarUrl: "",
        }
      )
    },
  )
  const totalCents = Math.round(route.totalCost * 100)
  const baseShare = Math.floor(totalCents / participants.length)
  const remainder = totalCents % participants.length
  const shares = participants.map(
    (_, index) => (baseShare + (index < remainder ? 1 : 0)) / 100,
  )
  const canSplit = participants.length > 1

  return (
    <Page className="max-w-3xl">
      <Card className="overflow-hidden">
        <div className="border-b border-border p-6 sm:p-8">
          <div className="flex size-12 items-center justify-center rounded-2xl bg-indigo-50 text-primary">
            <Icon name="people" className="size-6" />
          </div>
          <div className="mt-5">
            <Title>
              {requestsSent ? "Split requests sent" : "Split the trip cost?"}
            </Title>
          </div>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
            {requestsSent
              ? "Everyone’s share is accounted for. In this UI preview, no real payment requests were sent."
              : canSplit
                ? "Divide the selected route equally with everyone on your trip. You can review each share before sending."
                : "Add passengers to this plan before splitting the trip cost."}
          </p>
        </div>

        <div className="space-y-5 p-6 sm:p-8">
          <div className="gradient-card rounded-2xl p-5 text-white sm:p-6">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <div className="text-xs font-bold uppercase tracking-widest text-indigo-100">
                  Route {routeNumber} total
                </div>
                <div className="mt-2 text-3xl font-extrabold">
                  ${route.totalCost.toFixed(2)}
                </div>
                <div className="mt-2 text-xs text-indigo-100">
                  Fuel or charging plus tolls
                </div>
              </div>
              {canSplit && (
                <div className="rounded-xl border border-white/20 bg-white/10 px-4 py-3 sm:text-right">
                  <div className="text-xs font-semibold text-indigo-100">
                    Equal split
                  </div>
                  <div className="mt-1 text-lg font-extrabold">
                    ${shares[0].toFixed(2)} each
                  </div>
                  <div className="mt-1 text-xs text-indigo-100">
                    {participants.length} travelers
                  </div>
                </div>
              )}
            </div>
          </div>

          {canSplit && (
            <div>
              <div className="mb-3 flex items-center justify-between gap-3">
                <SectionTitle>Who pays what</SectionTitle>
                <span className="rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground">
                  Split equally
                </span>
              </div>
              <div className="overflow-hidden rounded-2xl border border-border">
                {participants.map((participant, index) => (
                  <div
                    key={participant.id}
                    className={`flex items-center gap-3 bg-white p-4 ${
                      index ? "border-t border-border" : ""
                    }`}
                  >
                    {participant.avatarUrl ? (
                      <img
                        src={participant.avatarUrl}
                        alt=""
                        className="size-11 rounded-full object-cover"
                      />
                    ) : (
                      <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-primary">
                        <Icon name="user" className="size-5" />
                      </span>
                    )}
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-extrabold text-foreground">
                        {index === 0 ? "You" : participant.name}
                      </div>
                      <div className="mt-0.5 truncate text-xs text-muted-foreground">
                        {participant.username}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-extrabold text-foreground">
                        ${shares[index].toFixed(2)}
                      </div>
                      <div
                        className={`mt-0.5 text-xs font-semibold ${
                          requestsSent && index > 0
                            ? "text-emerald-600"
                            : "text-muted-foreground"
                        }`}
                      >
                        {index === 0
                          ? "Your share"
                          : requestsSent
                            ? "Request sent"
                            : "To request"}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="rounded-xl bg-slate-50 px-4 py-3 text-xs leading-5 text-muted-foreground">
            UI preview only — no payment requests or notifications will be sent.
          </div>
        </div>

        <div className="flex flex-col-reverse gap-3 border-t border-border bg-slate-50/70 p-5 sm:flex-row sm:justify-between">
          <Button
            variant="ghost"
            onClick={() =>
              navigate(requestsSent ? "/dashboard" : `/plans/${plan.id}`)
            }
          >
            {requestsSent ? "Back to dashboard" : "Back to trip"}
          </Button>
          {requestsSent ? (
            <Button onClick={() => navigate(`/plans/${plan.id}`)}>
              View saved plan <Icon name="arrow" className="size-4" />
            </Button>
          ) : (
            <Button disabled={!canSplit} onClick={() => setRequestsSent(true)}>
              <Icon name="people" className="size-4" />
              Send split requests
            </Button>
          )}
        </div>
      </Card>
    </Page>
  )
}
