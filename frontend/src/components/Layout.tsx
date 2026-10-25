import { useNavigate, useLocation } from "react-router";
import { ReactNode } from "react"
import { AppLogo, Button, Icon } from "./ui";
import { useAppState } from "../AppState";

export function AppHeader() {

  const { username, logout } = useAppState()
  const navigate = useNavigate();
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6">
        <AppLogo />
        <div className="flex items-center gap-2 sm:gap-3">
          <span className="hidden text-sm font-semibold text-foreground md:inline">
            {username}
          </span>
          <span className="gradient-primary flex size-9 items-center justify-center rounded-full text-xs font-extrabold text-white">
            {(username ?? "U").slice(0, 2).toUpperCase()}
          </span>
          <Button
            variant="ghost"
            aria-label="Log out"
            className="px-3"
            onClick={() => {
              logout()
              navigate("/login", { replace: true })
            }}
          >
            <Icon name="logout" className="size-4" />
            <span className="hidden sm:inline">Log out</span>
          </Button>
        </div>
      </div>
    </header>
  )
}

export function Page({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div className="min-h-screen bg-background">
      <AppHeader />
      <main
        className={`mx-auto w-full max-w-7xl px-4 py-7 sm:px-6 md:py-10 ${className}`}
      >
        {children}
      </main>
    </div>
  )
}

const steps = [
  { path: "/plans/new/trip", label: "Trip details" },
  { path: "/plans/new/vehicle", label: "Vehicle" },
  { path: "/plans/new/results", label: "Results" },
]

export function WizardShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const current = location.pathname.includes("vehicle")
    ? 1
    : location.pathname.includes("trip")
      ? 0
      : 2
  return (
    <Page className="max-w-4xl">
      <div className="mb-8">
        <div className="mb-3 text-xs font-bold uppercase tracking-widest text-primary">
          Create a new plan
        </div>
        <div
          className="grid grid-cols-3 gap-2"
          aria-label={`Step ${current + 1} of 3`}
        >
          {steps.map((step, index) => (
            <div key={step.path} className="min-w-0">
              <div
                className={`mb-2 h-1.5 rounded-full ${
                  index <= current ? "gradient-primary" : "bg-border"
                }`}
              />
              <div
                className={`truncate text-xs font-bold sm:text-sm ${
                  index <= current ? "text-foreground" : "text-muted-foreground"
                }`}
              >
                <span className="mr-1 text-primary">{index + 1}.</span>{" "}
                {step.label}
              </div>
            </div>
          ))}
        </div>
      </div>
      {children}
    </Page>
  )
}
