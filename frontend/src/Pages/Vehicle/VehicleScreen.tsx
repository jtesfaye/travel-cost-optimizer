import { useNavigate } from "react-router"
import { useAppState } from "../../AppState"
import { Button, Card, Icon, SelectField, Title } from "../../components/ui"
import { WizardShell } from "../../components/Layout"
import { useVehicleLookup } from "../../hooks/useVehicleLookup"
import { MAKES, MODELS_BY_MAKE, YEARS } from "../../mockData"
import { TripSummary } from "./TripSummary"
import { VehicleLookupStatus } from "./VehicleLookupStatus"

const toOptions = (values: string[]) =>
  values.map((value) => ({ value, label: value }))

export function VehicleScreen() {
  const { draft, updateVehicle, acceptFallback } = useAppState()
  const navigate = useNavigate()
  const vehicle = draft.vehicle
  const models = vehicle.make ? (MODELS_BY_MAKE[vehicle.make] ?? []) : []

  useVehicleLookup()

  const change = (field: "year" | "make" | "model", value: string) => {
    const next = {
      ...vehicle,
      [field]: value,
      lookupState: "idle" as const,
      specs: null,
    }
    if (field === "year") {
      next.make = ""
      next.model = ""
    }
    if (field === "make") next.model = ""
    updateVehicle(next)
  }

  return (
    <WizardShell>
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <Card className="overflow-hidden">
          <div className="border-b border-border p-6 sm:p-8">
            <Title>Choose your vehicle</Title>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              We’ll use your vehicle’s efficiency to make the cost estimate more
              useful.
            </p>
          </div>
          <div className="space-y-6 p-6 sm:p-8">
            <div className="grid gap-4 sm:grid-cols-3">
              <SelectField
                label="Year"
                value={vehicle.year}
                placeholder="Year"
                options={toOptions(YEARS)}
                onChange={(event) => change("year", event.target.value)}
              />
              <SelectField
                label="Make"
                value={vehicle.make}
                placeholder="Make"
                disabled={!vehicle.year}
                options={toOptions(MAKES)}
                onChange={(event) => change("make", event.target.value)}
              />
              <SelectField
                label="Model"
                value={vehicle.model}
                placeholder="Model"
                disabled={!vehicle.make}
                options={toOptions(models)}
                onChange={(event) => change("model", event.target.value)}
              />
            </div>
            <VehicleLookupStatus
              vehicle={vehicle}
              onAcceptFallback={acceptFallback}
            />
          </div>
          <div className="flex flex-col-reverse gap-3 border-t border-border bg-slate-50/70 p-5 sm:flex-row sm:justify-between">
            <Button variant="ghost" onClick={() => navigate("/plans/new/trip")}>
              Back
            </Button>
            <Button
              disabled={!vehicle.specs || vehicle.lookupState === "searching"}
              onClick={() => navigate("/plans/new/results")}
            >
              Calculate trip <Icon name="arrow" className="size-4" />
            </Button>
          </div>
        </Card>
        <TripSummary
          origin={draft.trip.originLabel}
          destination={draft.trip.destinationLabel}
          passengers={draft.trip.passengers}
        />
      </div>
    </WizardShell>
  )
}
