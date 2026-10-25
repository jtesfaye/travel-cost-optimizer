import { useState, type SubmitEvent } from "react"
import { Navigate, useLocation, useNavigate } from "react-router"
import { useAppState } from "../AppState"
import { AppLogo, Button, Card, Icon, TextField, Title } from "../components/ui"

// TODO: mock sign-in (any non-empty username and password); replace with real auth.
export function LoginScreen() {
  const { username, login } = useAppState()
  const navigate = useNavigate()
  const location = useLocation()
  const [form, setForm] = useState({ username: "", password: "" })
  const [errors, setErrors] = useState({ username: "", password: "" })
  if (username) return <Navigate to="/dashboard" replace />

  const submit = (event: SubmitEvent) => {
    event.preventDefault()
    const nextErrors = {
      username: form.username.trim() ? "" : "Enter your username.",
      password: form.password ? "" : "Enter your password.",
    }
    setErrors(nextErrors)
    if (nextErrors.username || nextErrors.password) return
    login(form.username)
    const from = (location.state as { from?: string } | null)?.from
    navigate(from && from !== "/login" ? from : "/dashboard", { replace: true })
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-background px-4 py-10">
      <div className="ambient-orb -left-28 -top-24 bg-indigo-300" />
      <div className="ambient-orb -bottom-32 -right-20 bg-orange-200" />
      <Card className="relative w-full max-w-md p-7 sm:p-9">
        <div className="mb-8">
          <AppLogo />
        </div>
        <Title>Welcome back</Title>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Sign in to plan smarter road trips and keep every estimate in one
          place.
        </p>
        <form className="mt-7 space-y-5" onSubmit={submit} noValidate>
          <TextField
            label="Username"
            autoComplete="username"
            value={form.username}
            error={errors.username}
            onChange={(event) =>
              setForm({ ...form, username: event.target.value })
            }
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            value={form.password}
            error={errors.password}
            onChange={(event) =>
              setForm({ ...form, password: event.target.value })
            }
          />
          <Button type="submit" className="w-full">
            Sign in <Icon name="arrow" className="size-4" />
          </Button>
        </form>
      </Card>
    </div>
  )
}
