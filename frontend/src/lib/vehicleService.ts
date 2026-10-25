import { findVehicle } from "../mockData"
import type { VehicleSpecs } from "../types"

// Mock lookup. Swap the body for the real vehicle API call later; callers only
// depend on this signature (null means "vehicle not found").
export function lookupVehicle(
  year: string,
  make: string,
  model: string,
): Promise<VehicleSpecs | null> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(findVehicle(year, make, model)), 900)
  })
}
