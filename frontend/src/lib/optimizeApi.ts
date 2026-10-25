import type { RouteOption, RouteStop, VehicleSpecs } from "../types"

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/$/, "")
const OPTIMIZATIONS_URL = `${API_BASE_URL}/api/v1/optimizations`
const POLL_INTERVAL_MS = 1000
const TIMEOUT_MS = 3 * 60 * 1000

export type OptimizeStage = "queued" | "routing" | "pricing" | "optimizing" | "done"

export interface OptimizeProgress {
  stage: OptimizeStage
  progress: number
}

export interface Point {
  lat: number
  lng: number
}

export class OptimizeError extends Error {
  code: string
  constructor(code: string, message: string) {
    super(message)
    this.code = code
  }
}

interface ApiStop {
  id: string
  type: "fuel" | "charging"
  name: string
  address: string
  lat: number
  lng: number
  mileMarker: number
  price: number
  priceUnit: "gal" | "kWh"
  amount: number
  cost: number
  detourMin: number
  priceSource: "live" | "estimated"
}

interface ApiRoute {
  id: string
  description: string
  distanceMi: number
  durationMin: number
  cost: { energy: number; tolls: number; total: number }
  polyline: string
  stops: ApiStop[]
  tolls: { name: string; cost: number }[]
}

interface ApiJob {
  id: string
  status: "queued" | "running" | "succeeded" | "failed"
  stage: OptimizeStage
  progress: number
  result: { routes: ApiRoute[]; recommendedRouteId: string } | null
  error: { code: string; message: string } | null
}

export interface OptimizeResult {
  routes: RouteOption[]
  recommendedRouteId: string
}

const round = (value: number, digits: number) => Number(value.toFixed(digits))

function toRouteStops(route: ApiRoute): RouteStop[] {
  const energyStops = [...route.stops]
    .sort((a, b) => a.mileMarker - b.mileMarker)
    .map<RouteStop>((stop) => ({
      id: stop.id,
      type: stop.type,
      name: stop.name,
      lat: stop.lat,
      lng: stop.lng,
      location: `Mile ${Math.round(stop.mileMarker)}`,
      detail: [
        `$${stop.price.toFixed(stop.priceUnit === "kWh" ? 2 : 3)}/${stop.priceUnit}`,
        `${stop.amount.toFixed(1)} ${stop.priceUnit} · $${stop.cost.toFixed(2)}`,
        stop.detourMin >= 1 ? `${Math.round(stop.detourMin)} min detour` : "",
        stop.priceSource === "estimated" ? "estimated price" : "",
      ]
        .filter(Boolean)
        .join(" · "),
    }))
  const tollStops = route.tolls.map<RouteStop>((toll, index) => ({
    id: `${route.id}-toll-${index + 1}`,
    type: "toll",
    name: toll.name,
    location: "Along the route",
    detail: `$${toll.cost.toFixed(2)} · Electronic payment`,
  }))
  return [...energyStops, ...tollStops]
}

export function toRouteOption(route: ApiRoute): RouteOption {
  return {
    id: route.id,
    distance: Math.round(route.distanceMi),
    durationMinutes: Math.round(route.durationMin),
    energyCost: round(route.cost.energy, 2),
    tollCost: round(route.cost.tolls, 2),
    totalCost: round(route.cost.total, 2),
    polyline: route.polyline,
    stops: toRouteStops(route),
  }
}

function wait(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const abort = () => {
      window.clearTimeout(timer)
      reject(new DOMException("Aborted", "AbortError"))
    }
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", abort)
      resolve()
    }, ms)
    if (signal?.aborted) return abort()
    signal?.addEventListener("abort", abort, { once: true })
  })
}

async function request(url: string, init: RequestInit): Promise<ApiJob> {
  let response: Response
  try {
    response = await fetch(url, init)
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error
    throw new OptimizeError(
      "network_error",
      "Couldn’t reach the server. Check that the backend is running.",
    )
  }
  if (!response.ok) {
    const message =
      response.status === 422
        ? "The trip details weren’t accepted. Check your locations and vehicle."
        : "The server couldn’t process this request."
    throw new OptimizeError("request_failed", message)
  }
  return response.json()
}

/**
 * Starts an optimization job and polls it until it finishes. Rejects with an
 * OptimizeError (job failure / network) or an AbortError (cancelled).
 */
export async function optimizeTrip(
  origin: Point,
  destination: Point,
  vehicle: VehicleSpecs,
  { signal, onProgress }: { signal?: AbortSignal; onProgress?: (p: OptimizeProgress) => void } = {},
): Promise<OptimizeResult> {
  let job = await request(OPTIMIZATIONS_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ origin, destination, vehicle }),
    signal,
  })
  const jobUrl = `${OPTIMIZATIONS_URL}/${job.id}`
  const deadline = Date.now() + TIMEOUT_MS

  for (;;) {
    onProgress?.({ stage: job.stage, progress: job.progress })
    if (job.status === "failed") {
      throw new OptimizeError(
        job.error?.code ?? "internal_error",
        job.error?.message ?? "Something went wrong.",
      )
    }
    if (job.status === "succeeded" && job.result) {
      return {
        routes: job.result.routes.map(toRouteOption),
        recommendedRouteId: job.result.recommendedRouteId,
      }
    }
    if (Date.now() > deadline)
      throw new OptimizeError("timeout", "This is taking longer than expected.")
    await wait(POLL_INTERVAL_MS, signal)
    job = await request(jobUrl, { signal })
  }
}
