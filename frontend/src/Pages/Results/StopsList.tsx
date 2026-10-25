import { Card, Icon, SectionTitle } from "../../components/ui"
import type { RouteStop } from "../../types"

const stopStyles = {
  charging: { icon: "bolt", tone: "bg-emerald-50 text-emerald-600" },
  fuel: { icon: "fuel", tone: "bg-orange-50 text-orange-600" },
  toll: { icon: "road", tone: "bg-indigo-50 text-primary" },
  rest: { icon: "pin", tone: "bg-indigo-50 text-primary" },
} as const

export function StopsList({ stops }: { stops: RouteStop[] }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <SectionTitle>Stops along the way</SectionTitle>
        <span className="rounded-full bg-muted px-2.5 py-1 text-xs font-bold text-muted-foreground">
          {stops.length} stops
        </span>
      </div>
      <div className="mt-4 max-h-96 space-y-3 overflow-y-auto pr-1">
        {stops.map((stop, index) => (
          <div
            key={stop.id}
            className="flex gap-3 rounded-xl border border-border p-3.5"
          >
            <span
              className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${stopStyles[stop.type].tone}`}
            >
              <Icon name={stopStyles[stop.type].icon} className="size-4" />
            </span>
            <span className="min-w-0">
              <span className="block text-xs font-bold uppercase tracking-wide text-muted-foreground">
                Stop {index + 1} · {stop.location}
              </span>
              <span className="mt-0.5 block text-sm font-extrabold text-foreground">
                {stop.name}
              </span>
              <span className="mt-0.5 block text-xs text-muted-foreground">
                {stop.detail}
              </span>
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}
