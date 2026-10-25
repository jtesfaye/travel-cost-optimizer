import { Card, Icon } from "../../components/ui"
import { formatDuration, formatMoney } from "../../lib/format"
import type { RouteOption } from "../../types"

function MetricCard({
  icon,
  label,
  value,
  detail,
}: {
  icon: "bolt" | "fuel" | "road" | "clock"
  label: string
  value: string
  detail: string
}) {
  return (
    <Card className="p-4">
      <span className="flex size-8 items-center justify-center rounded-lg bg-indigo-50 text-primary">
        <Icon name={icon} className="size-4" />
      </span>
      <div className="mt-3 text-xs font-bold text-muted-foreground">{label}</div>
      <div className="mt-1 text-lg font-extrabold text-foreground">{value}</div>
      <div className="mt-1 text-xs text-muted-foreground">{detail}</div>
    </Card>
  )
}

export function CostSummary({
  route,
  passengers,
  isEv,
}: {
  route: RouteOption
  passengers: number
  isEv: boolean
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <Card className="gradient-card col-span-2 p-5 text-white sm:col-span-1">
        <div className="text-xs font-bold text-white/70">Total estimate</div>
        <div className="mt-2 text-3xl font-extrabold">
          {formatMoney(route.totalCost)}
        </div>
        <div className="mt-1 text-xs text-white/70">
          {formatMoney(route.totalCost / passengers)} per person
        </div>
      </Card>
      <MetricCard
        icon={isEv ? "bolt" : "fuel"}
        label={isEv ? "Charging" : "Fuel"}
        value={formatMoney(route.energyCost)}
        detail={isEv ? "Local rates applied" : "Route average applied"}
      />
      <MetricCard
        icon="road"
        label="Tolls"
        value={formatMoney(route.tollCost)}
        detail={route.tollCost ? "Electronic tolls" : "Toll-free route"}
      />
      <MetricCard
        icon="clock"
        label="Drive time"
        value={formatDuration(route.durationMinutes)}
        detail={`${route.distance} miles`}
      />
    </div>
  )
}
