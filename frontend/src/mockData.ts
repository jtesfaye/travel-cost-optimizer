import { City, PassengerProfile, VehicleSpecs } from "./types"
export const CITIES: City[] = [
  {
    id: "los-angeles",
    label: "Los Angeles, CA",
    latitude: 34.0522,
    longitude: -118.2437,
    gasPrice: 4.89,
    evRate: 0.43,
  },
  {
    id: "las-vegas",
    label: "Las Vegas, NV",
    latitude: 36.1699,
    longitude: -115.1398,
    gasPrice: 4.21,
    evRate: 0.39,
  },
  {
    id: "phoenix",
    label: "Phoenix, AZ",
    latitude: 33.4484,
    longitude: -112.074,
    gasPrice: 3.98,
    evRate: 0.41,
  },
  {
    id: "salt-lake-city",
    label: "Salt Lake City, UT",
    latitude: 40.7608,
    longitude: -111.891,
    gasPrice: 3.74,
    evRate: 0.36,
  },
  {
    id: "denver",
    label: "Denver, CO",
    latitude: 39.7392,
    longitude: -104.9903,
    gasPrice: 3.59,
    evRate: 0.38,
  },
]

// TODO: replace with the origin/destination chosen via Places autocomplete.
export const SAMPLE_ROUTE = {
  origin: CITIES[0],
  destination: CITIES[1],
}

// TODO: replace with the vehicle API.
export const VEHICLE_DB: Record<string, VehicleSpecs> = {
  "2023 Toyota Camry": { type: "gas", mpg: 32, tankGal: 15.8 },
  "2022 Toyota Camry": { type: "gas", mpg: 32, tankGal: 15.8 },
  "2023 Toyota Prius": { type: "hybrid", mpg: 57, tankGal: 11.3 },
  "2023 Toyota RAV4": { type: "gas", mpg: 27, tankGal: 14.5 },
  "2024 Tesla Model 3": { type: "ev", rangeMi: 358, batteryKwh: 82 },
  "2023 Tesla Model 3": { type: "ev", rangeMi: 341, batteryKwh: 82 },
  "2024 Tesla Model Y": { type: "ev", rangeMi: 330, batteryKwh: 75 },
  "2023 Ford F-150": { type: "gas", mpg: 20, tankGal: 26 },
  "2023 Ford Mustang Mach-E": { type: "ev", rangeMi: 312, batteryKwh: 91 },
  "2023 Honda Civic": { type: "gas", mpg: 36, tankGal: 12.4 },
  "2023 Honda CR-V Hybrid": { type: "hybrid", mpg: 40, tankGal: 14 },
  "2024 Chevrolet Bolt EV": { type: "ev", rangeMi: 259, batteryKwh: 65 },
  "2023 BMW 3 Series": { type: "gas", mpg: 26, tankGal: 15.6 },
  "2023 Jeep Wrangler": { type: "gas", mpg: 17, tankGal: 21.5 },
}

export const MAKES = [
  "Toyota",
  "Tesla",
  "Ford",
  "Honda",
  "Chevrolet",
  "BMW",
  "Jeep",
]

export const MODELS_BY_MAKE: Record<string, string[]> = {
  Toyota: ["Camry", "Prius", "RAV4"],
  Tesla: ["Model 3", "Model Y"],
  Ford: ["F-150", "Mustang Mach-E"],
  Honda: ["Civic", "CR-V Hybrid"],
  Chevrolet: ["Bolt EV"],
  BMW: ["3 Series"],
  Jeep: ["Wrangler"],
}

export const YEARS = Array.from({ length: 8 }, (_, index) =>
  String(2024 - index),
)

export const FALLBACK_SPECS: VehicleSpecs = {
  type: "gas",
  mpg: 25,
  tankGal: 15,
}

export function findVehicle(year: string, make: string, model: string) {
  const exact = VEHICLE_DB[`${year} ${make} ${model}`]
  if (exact) return exact
  return (
    Object.entries(VEHICLE_DB).find(([key]) =>
      key.includes(`${make} ${model}`),
    )?.[1] ?? null
  )
}

// TODO: replace with the user/connections API. Empty until real users exist,
// so passenger search returns no results.
export const MOCK_USERS: PassengerProfile[] = []
