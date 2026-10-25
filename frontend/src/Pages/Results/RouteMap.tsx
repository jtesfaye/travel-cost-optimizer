import { useEffect, useState } from "react"
import {
  AdvancedMarker,
  Map,
  Pin,
  useMap,
  useMapsLibrary,
} from "@vis.gl/react-google-maps"
import { Card } from "../../components/ui"
import type { RouteStop } from "../../types"

interface LatLng {
  lat: number
  lng: number
}

function EncodedPath({ polyline }: { polyline: string }) {
  const map = useMap()
  const geometry = useMapsLibrary("geometry")

  useEffect(() => {
    if (!map || !geometry) return
    const path = geometry.encoding.decodePath(polyline)
    const line = new google.maps.Polyline({
      path,
      strokeColor: "#4f46e5",
      strokeWeight: 5,
      map,
    })
    const bounds = new google.maps.LatLngBounds()
    path.forEach((point) => bounds.extend(point))
    map.fitBounds(bounds)
    return () => line.setMap(null)
  }, [map, geometry, polyline])

  return null
}

function RoutePath({ origin, destination }: { origin: LatLng; destination: LatLng }) {
  const map = useMap()
  const routesLib = useMapsLibrary("routes")
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!map || !routesLib) return
    let cancelled = false
    let polylines: google.maps.Polyline[] = []
    routesLib.Route.computeRoutes({
      origin,
      destination,
      travelMode: "DRIVING",
      fields: ["path", "viewport"],
    })
      .then(({ routes }) => {
        const route = routes?.[0]
        if (cancelled || !route) return setFailed(!route)
        polylines = route.createPolylines()
        polylines.forEach((line) => {
          line.setOptions({ strokeColor: "#4f46e5", strokeWeight: 5 })
          line.setMap(map)
        })
        if (route.viewport) map.fitBounds(route.viewport)
      })
      .catch(() => !cancelled && setFailed(true))
    return () => {
      cancelled = true
      polylines.forEach((line) => line.setMap(null))
    }
  }, [map, routesLib, origin, destination])

  return failed ? (
    <div className="absolute bottom-5 right-5 rounded-xl bg-white/90 px-3 py-2 text-xs font-medium text-rose-600 shadow-sm">
      Couldn't load the driving route
    </div>
  ) : null
}

export function RouteMap({
  origin,
  destination,
  originLabel,
  destinationLabel,
  polyline,
  stops = [],
}: {
  origin: LatLng
  destination: LatLng
  originLabel: string
  destinationLabel: string
  polyline?: string
  stops?: RouteStop[]
}) {
  return (
    <Card className="relative h-72 overflow-hidden sm:h-80">
      <Map
        mapId="DEMO_MAP_ID"
        defaultCenter={origin}
        defaultZoom={6}
        disableDefaultUI
        gestureHandling="cooperative"
      >
        <AdvancedMarker position={origin} title={originLabel} />
        <AdvancedMarker position={destination} title={destinationLabel} />
        {stops.map((stop) =>
          stop.lat == null || stop.lng == null ? null : (
            <AdvancedMarker
              key={stop.id}
              position={{ lat: stop.lat, lng: stop.lng }}
              title={`${stop.name} · ${stop.location}`}
            >
              <Pin
                background={stop.type === "charging" ? "#059669" : "#f59e0b"}
                borderColor="#ffffff"
                glyphColor="#ffffff"
              />
            </AdvancedMarker>
          ),
        )}
        {polyline ? (
          <EncodedPath polyline={polyline} />
        ) : (
          <RoutePath origin={origin} destination={destination} />
        )}
      </Map>
    </Card>
  )
}
