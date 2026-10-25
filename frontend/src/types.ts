
export type VehicleType = "gas" | "hybrid" | "ev"
export type LookupState = "idle" | "searching" | "found" | "not_found"
export type RouteId = string

export interface VehicleSelection {
  year: string
  make: string
  model: string
}

export interface VehicleSpecs {
  type: VehicleType
  mpg?: number
  rangeMi?: number
  tankGal?: number
  batteryKwh?: number
}

export interface DraftVehicle extends VehicleSelection {
  lookupState: LookupState
  specs: VehicleSpecs | null
}

export interface PassengerProfile {
  id: string
  name: string
  username: string
  avatarUrl: string
}

export interface TripDetails {
  originId: string
  originLabel: string
  originLat: number | null
  originLng: number | null
  destinationId: string
  destinationLabel: string
  destinationLat: number | null
  destinationLng: number | null
  passengers: number
  invitedPassengers?: PassengerProfile[]
}

export interface RouteStop {
  id: string
  type: "fuel" | "charging" | "rest" | "toll"
  name: string
  location: string
  detail: string
  lat?: number
  lng?: number
}

export interface RouteOption {
  id: RouteId
  distance: number
  durationMinutes: number
  energyCost: number
  tollCost: number
  totalCost: number
  polyline?: string
  stops: RouteStop[]
}

export interface TripPlan {
  version: 1
  id: string
  name: string
  createdAt: string
  draft: boolean
  trip: TripDetails
  vehicle: DraftVehicle
  routes: RouteOption[]
  selectedRouteId: RouteId
}

export interface City {
  id: string
  label: string
  latitude: number
  longitude: number
  gasPrice: number
  evRate: number
}
