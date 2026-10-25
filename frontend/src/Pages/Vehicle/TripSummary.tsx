import { Card, Icon } from "../../components/ui"

export function TripSummary({
  origin,
  destination,
  passengers,
}: {
  origin: string
  destination: string
  passengers: number
}) {
  return (
    <Card className="h-fit p-5">
      <div className="text-xs font-bold uppercase tracking-widest text-muted-foreground">
        Trip summary
      </div>
      <div className="mt-5 space-y-4">
        <div className="flex gap-3">
          <Icon name="pin" className="mt-0.5 size-4 shrink-0 text-primary" />
          <div>
            <div className="text-xs text-muted-foreground">From</div>
            <div className="mt-0.5 text-sm font-bold">{origin}</div>
          </div>
        </div>
        <div className="ml-2 h-4 border-l border-dashed border-indigo-200" />
        <div className="flex gap-3">
          <Icon name="pin" className="mt-0.5 size-4 shrink-0 text-secondary" />
          <div>
            <div className="text-xs text-muted-foreground">To</div>
            <div className="mt-0.5 text-sm font-bold">{destination}</div>
          </div>
        </div>
        <div className="border-t border-border pt-4 text-sm text-muted-foreground">
          <span className="font-bold text-foreground">{passengers}</span>{" "}
          {passengers === 1 ? "passenger" : "passengers"}
        </div>
      </div>
    </Card>
  )
}
