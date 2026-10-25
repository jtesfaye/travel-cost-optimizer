import { Button, Icon } from "../../components/ui"
import type { DraftVehicle } from "../../types"

function vehicleSummary({ specs }: DraftVehicle) {
  if (!specs) return ""
  return specs.type === "ev"
    ? `${specs.rangeMi} mi range · ${specs.batteryKwh} kWh battery`
    : `${specs.mpg} MPG · ${specs.tankGal} gal tank`
}

export function VehicleLookupStatus({
  vehicle,
  onAcceptFallback,
}: {
  vehicle: DraftVehicle
  onAcceptFallback: () => void
}) {
  return (
    <div className="min-h-28" aria-live="polite">
      {vehicle.lookupState === "idle" && (
        <div className="flex min-h-28 items-center justify-center rounded-2xl border border-dashed border-border bg-slate-50 px-5 text-center text-sm text-muted-foreground">
          Select a year, make, and model to find efficiency details.
        </div>
      )}
      {vehicle.lookupState === "searching" && (
        <div className="flex min-h-28 items-center justify-center gap-3 rounded-2xl border border-indigo-100 bg-indigo-50 text-sm font-bold text-primary">
          <span className="spinner size-5 rounded-full border-2 border-indigo-200 border-t-primary" />{" "}
          Looking up your vehicle…
        </div>
      )}
      {vehicle.lookupState === "found" && vehicle.specs && (
        <div className="flex min-h-28 items-center gap-4 rounded-2xl border border-emerald-100 bg-emerald-50 p-5">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white text-emerald-600">
            <Icon name={vehicle.specs.type === "ev" ? "bolt" : "car"} />
          </span>
          <span>
            <span className="block text-sm font-extrabold text-foreground">
              {vehicle.year} {vehicle.make} {vehicle.model}
            </span>
            <span className="mt-1 block text-sm font-semibold text-emerald-700">
              {vehicleSummary(vehicle)}
            </span>
          </span>
        </div>
      )}
      {vehicle.lookupState === "not_found" && !vehicle.specs && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <div className="text-sm font-extrabold text-amber-900">
            We don’t have this vehicle yet
          </div>
          <p className="mt-1 text-sm leading-6 text-amber-800">
            Continue with a 25 MPG class average for this estimate.
          </p>
          <Button
            type="button"
            variant="secondary"
            className="mt-3 border-amber-200 bg-white text-amber-900"
            onClick={onAcceptFallback}
          >
            Use class average
          </Button>
        </div>
      )}
      {vehicle.lookupState === "not_found" && vehicle.specs && (
        <div className="flex min-h-28 items-center gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <span className="flex size-11 shrink-0 items-center justify-center rounded-xl bg-white text-amber-700">
            <Icon name="car" />
          </span>
          <span>
            <span className="block text-sm font-extrabold text-amber-900">
              Class average ready
            </span>
            <span className="mt-1 block text-sm text-amber-800">
              We’ll calculate this trip using 25 MPG.
            </span>
          </span>
        </div>
      )}
    </div>
  )
}
