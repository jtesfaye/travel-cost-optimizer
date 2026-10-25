import { Button, Icon } from "../../components/ui"
import { formatDuration, formatMoney } from "../../lib/format"
import type { RouteId, RouteOption } from "../../types"

export function RouteOptionPicker({
  routes,
  selectedRouteId,
  onSelect,
}: {
  routes: RouteOption[]
  selectedRouteId: RouteId
  onSelect: (id: RouteId) => void
}) {
  return (
    <div className="grid gap-3 md:grid-cols-3">
      {routes.map((option, index) => {
        const selected = selectedRouteId === option.id
        return (
          <Button
            key={option.id}
            variant="secondary"
            aria-pressed={selected}
            className={`h-auto items-start justify-start p-4 text-left ${
              selected ? "border-primary bg-indigo-50 ring-2 ring-indigo-100" : ""
            }`}
            onClick={() => onSelect(option.id)}
          >
            <span
              className={`mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-lg ${
                selected
                  ? "bg-primary text-white"
                  : "bg-muted text-muted-foreground"
              }`}
            >
              <Icon name="road" className="size-4" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center justify-between gap-2">
                <span className="font-extrabold">Route {index + 1}</span>
                <span className="text-base font-extrabold">
                  {formatMoney(option.totalCost)}
                </span>
              </span>
              <span className="mt-2 block text-xs text-muted-foreground">
                {option.distance} mi · {formatDuration(option.durationMinutes)}
              </span>
            </span>
          </Button>
        )
      })}
    </div>
  )
}
