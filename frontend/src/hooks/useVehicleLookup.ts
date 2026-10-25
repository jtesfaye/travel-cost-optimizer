import { useEffect } from "react"
import { useAppState } from "../AppState"
import { lookupVehicle } from "../lib/vehicleService"

// Looks up specs whenever year, make and model are all chosen. Specs are
// cleared by the screen when any field changes, which re-triggers the lookup.
export function useVehicleLookup() {
  const { draft, updateVehicle } = useAppState()
  const { year, make, model, specs } = draft.vehicle

  useEffect(() => {
    if (!year || !make || !model || specs) return
    let cancelled = false
    updateVehicle((current) => ({ ...current, lookupState: "searching" }))
    lookupVehicle(year, make, model).then((match) => {
      if (cancelled) return
      updateVehicle((current) => ({
        ...current,
        lookupState: match ? "found" : "not_found",
        specs: match,
      }))
    })
    return () => {
      cancelled = true
    }
  }, [year, make, model, specs, updateVehicle])
}
