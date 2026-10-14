import { AppHeader, Page, WizardShell } from "../components/Layout"
import { useNavigate } from "react-router"
import { Card, Button, Title, SelectField, Icon } from "../components/ui"
import { CITIES } from "../mockData"
const cityOptions = CITIES.map((city) => ({
  value: city.id,
  label: city.label,
}))

export function TripDetailsScreen() {

  const navigate = useNavigate()
  const [trip, setTrip] = useState(draft.trip)
  const [submitted, setSubmitted] = useState(false)
  const sameCity = Boolean(
    trip.originId && trip.originId === trip.destinationId,
  )
  const valid = Boolean(trip.originId && trip.destinationId && !sameCity)

  const next = (event: FormEvent) => {
    event.preventDefault()
    setSubmitted(true)
    if (!valid) return
    updateTrip(trip)
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
            <div className="grid items-end gap-3 md:grid-cols-[1fr_auto_1fr]">
              <SelectField
                label="Starting city"
                value={trip.originId}
                placeholder="Choose a starting city"
                options={cityOptions.map((option) => ({
                  ...option,
                  disabled: option.value === trip.destinationId,
                }))}
                error={
                  submitted && !trip.originId
                    ? "Choose where your trip starts."
                    : undefined
                }
                onChange={(event) =>
                  setTrip({ ...trip, originId: event.target.value })
                }
              />
              <Button
                type="button"
                variant="secondary"
                aria-label="Swap starting city and destination"
                className="mb-0 size-12 px-0"
                disabled={!trip.originId || !trip.destinationId}
                onClick={() =>
                  setTrip({
                    ...trip,
                    originId: trip.destinationId,
                    destinationId: trip.originId,
                  })
                }
              >
                <Icon name="swap" className="size-4 md:rotate-90" />
              </Button>
              <SelectField
                label="Destination"
                value={trip.destinationId}
                placeholder="Choose a destination"
                options={cityOptions.map((option) => ({
                  ...option,
                  disabled: option.value === trip.originId,
                }))}
                error={
                  submitted && (!trip.destinationId || sameCity)
                    ? "Choose a different destination."
                    : undefined
                }
                onChange={(event) =>
                  setTrip({ ...trip, destinationId: event.target.value })
                }
              />
            </div>
            <fieldset>
              <legend className="mb-3 text-sm font-semibold text-foreground">
                Passengers
              </legend>
              <div
                className="grid grid-cols-5 gap-2"
                aria-label="Number of passengers"
              >
                {[1, 2, 3, 4, 5].map((number) => (
                  <Button
                    key={number}
                    type="button"
                    variant={
                      trip.passengers === number ? "primary" : "secondary"
                    }
                    aria-pressed={trip.passengers === number}
                    onClick={() => setTrip({ ...trip, passengers: number })}
                  >
                    {number}
                  </Button>
                ))}
              </div>
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