import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react"

import { Link } from "react-router"

type IconName = "arrow" | "bolt" | "car" | "check" | "chevron" | "clock" | "fuel" | "logout" | "map" | "people" | "pin" | "plus" | "road" | "swap" | "user"

export function Icon({
  name,
  className = "size-5",
}: {
  name: IconName
  className?: string
}) {
  const paths: Record<IconName, ReactNode> = {
    arrow: <path d="m9 18 6-6-6-6" />,
    bolt: <path d="m13 2-9 12h7l-1 8 9-12h-7l1-8Z" />,
    car: (
      <>
        <path d="M5 17h14l-1.5-6h-11L5 17Z" />
        <path d="M7 11 9 6h6l2 5M7 17v2m10-2v2M8 14h.01M16 14h.01" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    chevron: <path d="m9 18 6-6-6-6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    fuel: (
      <>
        <path d="M5 21V4h9v17M3 21h13M7 8h5" />
        <path d="M14 7h2l3 3v8a2 2 0 0 0 2 2V9l-2-2" />
      </>
    ),
    logout: (
      <>
        <path d="M10 17 15 12 10 7M15 12H3" />
        <path d="M14 4h5a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-5" />
      </>
    ),
    map: (
      <>
        <path d="m3 6 5-2 8 3 5-2v13l-5 2-8-3-5 2V6Z" />
        <path d="M8 4v13m8-10v13" />
      </>
    ),
    people: (
      <>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75" />
      </>
    ),
    pin: (
      <>
        <path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z" />
        <circle cx="12" cy="10" r="2.5" />
      </>
    ),
    plus: <path d="M12 5v14M5 12h14" />,
    road: (
      <>
        <path d="M9 22 11 2M15 22 13 2M12 7v3m0 4v3" />
      </>
    ),
    swap: <path d="m7 7 3-3 3 3M10 4v13m7 0-3 3-3-3m3 3V7" />,
    user: (
      <>
        <circle cx="12" cy="8" r="4" />
        <path d="M4 21a8 8 0 0 1 16 0" />
      </>
    ),
  }
  return (
    <svg
      aria-hidden="true"
      className={className}
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  )
}

export function Button({
  children,
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger"
}) {
  const styles = {
    primary:
      "bg-primary text-primary-foreground shadow-lg shadow-indigo-200 hover:bg-indigo-600",
    secondary:
      "border border-border bg-card text-foreground hover:border-indigo-200 hover:bg-indigo-50",
    ghost: "text-muted-foreground hover:bg-muted hover:text-foreground",
    danger: "text-rose-600 hover:bg-rose-50",
  }
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <div
      className={`rounded-2xl border border-border bg-card shadow-card ${className}`}
    >
      {children}
    </div>
  )
}

export function TextField({
  label,
  error,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string, error?: string }) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-foreground">
        {label}
      </span>
      <input
        className={`min-h-12 w-full rounded-xl border bg-white px-4 text-sm outline-none transition placeholder:text-slate-400 focus:border-primary focus:ring-4 focus:ring-indigo-100 ${
          error ? "border-rose-400" : "border-border"
        }`}
        {...props}
      />
      {error && (
        <span className="mt-1.5 block text-xs font-medium text-rose-600">
          {error}
        </span>
      )}
    </label>
  )
}

export function SelectField({
  label,
  options,
  placeholder,
  error,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string
  options: { value: string, label: string, disabled?: boolean }[]
  placeholder: string
  error?: string
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-sm font-semibold text-foreground">
        {label}
      </span>
      <span className="relative block">
        <select
          className={`min-h-12 w-full appearance-none rounded-xl border bg-white px-4 pr-10 text-sm font-medium outline-none transition focus:border-primary focus:ring-4 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-muted disabled:text-muted-foreground ${
            error ? "border-rose-400" : "border-border"
          }`}
          {...props}
        >
          <option value="" disabled>
            {placeholder}
          </option>
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        <Icon
          name="chevron"
          className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 rotate-90 text-muted-foreground"
        />
      </span>
      {error && (
        <span className="mt-1.5 block text-xs font-medium text-rose-600">
          {error}
        </span>
      )}
    </label>
  )
}

export function AppLogo() {
  return (
    <Link
      to="/"
      className="flex items-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="gradient-primary flex size-9 items-center justify-center rounded-xl text-white shadow-md shadow-indigo-200">
        <Icon name="map" className="size-5" />
      </span>
      <span className="text-base font-extrabold tracking-tight text-foreground">
        RouteCost
      </span>
    </Link>
  )
}

export function Title({
  children,
  size = "large",
}: {
  children: ReactNode
  size?: "small" | "large" | "hero"
}) {
  const styles = {
    small: "text-lg",
    large: "text-2xl md:text-3xl",
    hero: "text-3xl md:text-4xl",
  }
  return (
    <div
      role="heading"
      aria-level={1}
      className={`${styles[size]} font-extrabold tracking-tight text-foreground`}
    >
      {children}
    </div>
  )
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <div
      role="heading"
      aria-level={2}
      className="text-base font-bold text-foreground"
    >
      {children}
    </div>
  )
}

export function LiveBadge() {
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700">
      <span className="live-dot size-1.5 rounded-full bg-emerald-500" />
      Live prices
    </span>
  )
}
