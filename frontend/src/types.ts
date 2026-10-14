
export interface VehicleSelection {
  year: string
  make: string
  model: string
}

export interface TripDetails {
  originId: string
  destinationId: string
  passengers: number
}

export interface TripPlan {
  version: 1
  id: string
  name: string
  createdAt: string
  trip: TripDetails
  vehicle: VehicleSelection
}

export interface City {
  id: string
  label: string
  latitude: number
  longitude: number
  gasPrice: number
  evRate: number
}
