import { Link } from "react-router"
import { Page } from "../components/Layout"
import { Card, Icon, Title } from "../components/ui"

export function NotFoundScreen() {
  return (
    <Page className="max-w-xl">
      <Card className="p-8 text-center">
        <Icon name="road" className="mx-auto size-9 text-primary" />
        <div className="mt-4">
          <Title>That route doesn’t exist</Title>
        </div>
        <p className="mt-2 text-sm text-muted-foreground">
          Let’s get you back to your travel plans.
        </p>
        <Link
          to="/dashboard"
          className="mt-6 inline-flex min-h-11 items-center justify-center rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-200"
        >
          Back to dashboard
        </Link>
      </Card>
    </Page>
  )
}
