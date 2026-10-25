import { Card, SectionTitle } from "../../components/ui"
import { formatMoney } from "../../lib/format"
import type { RouteOption } from "../../types"

export function CostBreakdown({
  route,
  routeNumber,
  isEv,
}: {
  route: RouteOption
  routeNumber: number
  isEv: boolean
}) {
  const percent = (value: number) => `${(value / route.totalCost) * 100}%`
  return (
    <Card className="p-5 sm:p-6">
      <div className="flex items-center justify-between gap-4">
        <SectionTitle>Cost breakdown</SectionTitle>
        <span className="text-xs font-semibold text-muted-foreground">
          Route {routeNumber}
        </span>
      </div>
      <div className="mt-5 flex h-3 overflow-hidden rounded-full bg-muted">
        <span
          className="gradient-orange h-full"
          style={{ width: percent(route.energyCost) }}
        />
        <span
          className="h-full bg-violet-400"
          style={{ width: percent(route.tollCost) }}
        />
      </div>
      <div className="mt-4 flex flex-wrap gap-5 text-xs font-semibold text-muted-foreground">
        <span className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-orange-400" />
          {isEv ? "Charging" : "Fuel"} {formatMoney(route.energyCost)}
        </span>
        <span className="flex items-center gap-2">
          <span className="size-2.5 rounded-full bg-violet-400" />
          Tolls {formatMoney(route.tollCost)}
        </span>
      </div>
    </Card>
  )
}
