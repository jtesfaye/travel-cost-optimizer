import { WizardShell } from "../components/Layout"
import { useState, type SubmitEvent } from "react"
import { useNavigate } from "react-router"
import { Card, Button, Title, Icon, SectionTitle, TextField } from "../components/ui"
import { PlaceAutocompleteField, type PlaceSelection } from "../components/PlaceAutocompleteField"
import { useAppState } from "../AppState"
import { MOCK_USERS } from "../mockData"
import type { PassengerProfile, TripPlan } from "../types"


export function TripDetailsScreen() {

  const navigate = useNavigate()
  const { draft, updateTrip, startNewPlan } = useAppState()
  const [trip, setTrip] = useState<TripPlan>(draft)
  const [submitted, setSubmitted] = useState(false)
  const sameCity = Boolean(
    trip.trip.originId && trip.trip.originId === trip.trip.destinationId,
  )
  const valid = Boolean(
    trip.trip.originId && trip.trip.destinationId && !sameCity,
  )

  const [activePassengerSlot, setActivePassengerSlot] = useState<number | null>(
    null,
  )
  const [passengerSearch, setPassengerSearch] = useState("")
  const invitedPassengers = trip.trip.invitedPassengers ?? []
  const normalizedPassengerSearch = passengerSearch.trim().toLowerCase()
  const matchingUsers = MOCK_USERS.filter((user) => {
    if (!normalizedPassengerSearch) return false
    const matchesSearch =
      user.name.toLowerCase().includes(normalizedPassengerSearch) ||
      user.username.toLowerCase().includes(normalizedPassengerSearch)
    const isAlreadyInvited = invitedPassengers.some(
      (passenger, index) =>
        passenger.id === user.id && index !== activePassengerSlot,
    )
    return matchesSearch && !isAlreadyInvited
  })

  const setPassengers = (passengers: PassengerProfile[]) =>
    setTrip((current) => ({
      ...current,
      trip: {
        ...current.trip,
        invitedPassengers: passengers,
        passengers: passengers.length + 1,
      },
    }))

  const openPassengerSearch = (index: number) => {
    setActivePassengerSlot(index)
    setPassengerSearch("")
  }

  const selectPassenger = (index: number, user: PassengerProfile) => {
    const next = [...invitedPassengers]
    next[index] = user
    setPassengers(next.filter(Boolean))
    setActivePassengerSlot(null)
    setPassengerSearch("")
  }

  const removePassenger = (index: number) => {
    setPassengers(invitedPassengers.filter((_, i) => i !== index))
    setActivePassengerSlot(null)
    setPassengerSearch("")
  }

  const setPlace = (
    field: "origin" | "destination",
    place: PlaceSelection | null,
  ) =>
    setTrip((current) => ({
      ...current,
      trip: {
        ...current.trip,
        [`${field}Id`]: place?.placeId ?? "",
        [`${field}Label`]: place?.label ?? "",
        [`${field}Lat`]: place?.lat ?? null,
        [`${field}Lng`]: place?.lng ?? null,
      },
    }))

  const next = (event: SubmitEvent) => {
    event.preventDefault()
    setSubmitted(true)
    if (!valid) return
    updateTrip(trip.trip)
    navigate("/plans/new/vehicle")
  }

  return (
    <WizardShell>
      <Card className="overflow-hidden">
        <div className="border-b border-border p-6 sm:p-8">
          <Title>Where are you heading?</Title>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Choose your route and who is coming along. You can refine the route
            after we calculate it.
          </p>
        </div>
        <form onSubmit={next} noValidate>
          <div className="space-y-6 p-6 sm:p-8">
            <div className="grid items-end gap-3 md:grid-cols-2">
              <PlaceAutocompleteField
                label="Enter start location..."
                value={
                  trip.trip.originId
                    ? {
                        placeId: trip.trip.originId,
                        label: trip.trip.originLabel,
                        lat: trip.trip.originLat ?? 0,
                        lng: trip.trip.originLng ?? 0,
                      }
                    : null
                }
                onSelect={(place) => setPlace("origin", place)}
                error={submitted && !trip.trip.originId ? "Choose a starting location" : ""}
              />

              <PlaceAutocompleteField
                label="Enter destination location..."
                value={
                  trip.trip.destinationId
                    ? {
                        placeId: trip.trip.destinationId,
                        label: trip.trip.destinationLabel,
                        lat: trip.trip.destinationLat ?? 0,
                        lng: trip.trip.destinationLng ?? 0,
                      }
                    : null
                }
                onSelect={(place) => setPlace("destination", place)}
                error={
                  submitted && !trip.trip.destinationId
                    ? "Choose a destination"
                    : sameCity && submitted
                      ? "Destination must differ from the start"
                      : ""
                }
              />
            </div>
            <fieldset className="space-y-4">
              <div className="flex flex-wrap items-end justify-between gap-2">
                <div>
                  <legend className="text-sm font-semibold text-foreground">
                    Who’s coming?
                  </legend>
                  <p className="mt-1 text-xs text-muted-foreground">
                    You’re included. Add up to four people to your trip.
                  </p>
                </div>
                <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-primary">
                  {trip.trip.passengers}{" "}
                  {trip.trip.passengers === 1 ? "traveler" : "travelers"}
                </span>
              </div>
              <div
                className="grid grid-cols-2 gap-3 sm:grid-cols-4"
                aria-label="Trip passengers"
              >
                {Array.from({ length: 4 }, (_, index) => {
                  const passenger = invitedPassengers[index]
                  return (
                    <Button
                      key={passenger?.id ?? `passenger-slot-${index}`}
                      type="button"
                      variant="secondary"
                      aria-label={
                        passenger
                          ? `Change ${passenger.name}`
                          : `Add passenger ${index + 1}`
                      }
                      aria-pressed={activePassengerSlot === index}
                      className={`h-auto min-h-28 flex-col rounded-2xl px-2 py-3 ${
                        activePassengerSlot === index
                          ? "border-primary bg-indigo-50 ring-2 ring-indigo-100"
                          : passenger
                            ? "border-indigo-100 bg-white"
                            : "border-dashed bg-slate-50/70"
                      }`}
                      onClick={() => openPassengerSearch(index)}
                    >
                      {passenger ? (
                        <>
                          <img
                            src={passenger.avatarUrl}
                            alt=""
                            className="size-14 rounded-full object-cover ring-4 ring-white shadow-sm-soft"
                          />
                          <span className="max-w-full truncate text-xs font-bold text-foreground">
                            {passenger.name}
                          </span>
                        </>
                      ) : (
                        <>
                          <span className="relative flex size-14 items-center justify-center rounded-full border border-dashed border-indigo-200 bg-white text-muted-foreground">
                            <Icon name="user" className="size-6" />
                            <span className="absolute -bottom-1 -right-1 flex size-5 items-center justify-center rounded-full bg-primary text-white ring-2 ring-white">
                              <Icon name="plus" className="size-3" />
                            </span>
                          </span>
                          <span className="text-xs font-bold text-muted-foreground">
                            Add passenger
                          </span>
                        </>
                      )}
                    </Button>
                  )
                })}
              </div>
              {activePassengerSlot !== null && (
                <div className="animate-in rounded-2xl border border-indigo-100 bg-indigo-50/60 p-4 sm:p-5">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <SectionTitle>
                        {invitedPassengers[activePassengerSlot]
                          ? "Change passenger"
                          : "Find a passenger"}
                      </SectionTitle>
                      <p className="mt-1 text-xs text-muted-foreground">
                        Search your Roadtrip Planner connections by name or username.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      className="min-h-9 px-3 py-1.5"
                      onClick={() => setActivePassengerSlot(null)}
                    >
                      Close
                    </Button>
                  </div>
                  <div className="mt-4">
                    <TextField
                      label="Search users"
                      type="search"
                      autoFocus
                      placeholder="Try “Maya” or “@mayac”"
                      value={passengerSearch}
                      onChange={(event) =>
                        setPassengerSearch(event.target.value)
                      }
                    />
                  </div>
                  <div className="mt-3 grid gap-2">
                    {matchingUsers.map((user) => (
                      <Button
                        key={user.id}
                        type="button"
                        variant="secondary"
                        className="h-auto justify-start px-3 py-2.5 text-left"
                        onClick={() =>
                          selectPassenger(activePassengerSlot, user)
                        }
                      >
                        <img
                          src={user.avatarUrl}
                          alt=""
                          className="size-10 rounded-full object-cover"
                        />
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-bold text-foreground">
                            {user.name}
                          </span>
                          <span className="block truncate text-xs font-medium text-muted-foreground">
                            {user.username}
                          </span>
                        </span>
                        <Icon
                          name="plus"
                          className="ml-auto size-4 shrink-0 text-primary"
                        />
                      </Button>
                    ))}
                  </div>
                  {normalizedPassengerSearch && !matchingUsers.length && (
                    <p className="mt-4 rounded-xl bg-white p-4 text-center text-sm text-muted-foreground">
                      No users found. Try another name or username.
                    </p>
                  )}
                  {invitedPassengers[activePassengerSlot] && (
                    <Button
                      type="button"
                      variant="danger"
                      className="mt-3 w-full sm:w-auto"
                      onClick={() => removePassenger(activePassengerSlot)}
                    >
                      Remove{" "}
                      {
                        invitedPassengers[activePassengerSlot]?.name.split(
                          " ",
                        )[0]
                      }
                    </Button>
                  )}
                </div>
              )}
            </fieldset>
          </div>
          <div className="flex flex-col-reverse gap-3 border-t border-border bg-slate-50/70 p-5 sm:flex-row sm:justify-between">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                startNewPlan()
                navigate("/dashboard")
              }}
            >
              Cancel
            </Button>
            <Button type="submit">
              Continue to vehicle <Icon name="arrow" className="size-4" />
            </Button>
          </div>
        </form>
      </Card>
    </WizardShell>
  )
}