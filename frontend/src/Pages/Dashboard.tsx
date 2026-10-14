import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate} from 'react-router'
import { Page } from "../components/Layout";
import { useAppState } from '../AppState';
import { Button, Title, Icon, Card, SectionTitle } from '../components/ui';

export function DashboardScreen() {
  const {username, plans} = useAppState()
  const navigate = useNavigate();
  return (
    <Page>
      <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 text-xs font-bold uppercase tracking-widest text-primary">
            Your travel workspace
          </div>
          <Title size="hero">Plan the road ahead</Title>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Compare route costs, local prices, and the stops that make every
            trip easier.
          </p>
        </div>
        <Button
          onClick={() => {
            navigate("/plans/new/trip")
          }}
        >
          <Icon name="plus" className="size-4" /> Create new plan
        </Button>
      </div>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(18rem,0.8fr)]">
        <Card className="p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <SectionTitle>Planned travel</SectionTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                {plans.length} trips ready to review
              </p>
            </div>
            <span className="rounded-full bg-indigo-50 px-3 py-1 text-xs font-bold text-primary">
              Saved plans
            </span>
          </div>
          <div className="space-y-3">
            
            <div className="rounded-2xl border border-dashed border-border p-8 text-center">
              <Icon name="map" className="mx-auto size-8 text-primary" />
              <div className="mt-3 font-bold">No plans yet</div>
              <p className="mt-1 text-sm text-muted-foreground">
                Create your first route to see it here.
              </p>
            </div>
            
          </div>
        </Card>

        <div className="space-y-5">
          <Card className="overflow-hidden p-6">
            <div className="flex items-start justify-between">
              <span className="flex size-11 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <Icon name="fuel" />
              </span>
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground">
                To DO
              </span>
            </div>
            <div className="mt-5">
              <SectionTitle>Monthly travel overview</SectionTitle>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              See fuel, toll, and charging spend across every saved trip.
            </p>
            <div
              className="mt-5 flex h-16 items-end gap-2 opacity-60"
              aria-hidden="true"
            >
              {[32, 50, 38, 62, 46, 72, 58].map((height, index) => (
                <span
                  key={index}
                  className="flex-1 rounded-t bg-indigo-100"
                  style={{ height: `${height}%` }}
                />
              ))}
            </div>
          </Card>
          <Card className="p-6">
            <div className="flex items-start justify-between">
              <span className="flex size-11 items-center justify-center rounded-xl bg-orange-50 text-secondary">
                <Icon name="bolt" />
              </span>
              <span className="rounded-full bg-muted px-3 py-1 text-xs font-bold text-muted-foreground">
                Coming soon
              </span>
            </div>
            <div className="mt-5">
              <SectionTitle>Price alerts</SectionTitle>
            </div>
            <p className="mt-2 text-sm leading-6 text-muted-foreground">
              Get notified when prices drop along routes you travel most.
            </p>
          </Card>
        </div>
      </div>
    </Page>
  )

}