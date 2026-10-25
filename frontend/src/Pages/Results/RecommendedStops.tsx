import { Card, Icon, SectionTitle } from "../../components/ui"

export function RecommendedStops() {
  return (
    <Card className="p-5">
      <SectionTitle>Recommended stops</SectionTitle>
      <div className="mt-4 rounded-2xl border border-dashed border-border p-8 text-center">
        <Icon name="pin" className="mx-auto size-8 text-primary" />
        <div className="mt-3 font-bold">No recommendations yet</div>
        <p className="mt-1 text-sm text-muted-foreground">
          Stops suggested for this trip will show up here.
        </p>
      </div>
    </Card>
  )
}
