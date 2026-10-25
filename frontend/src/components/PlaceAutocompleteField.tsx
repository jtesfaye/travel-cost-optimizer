import { useEffect, useRef, useState } from "react"
import { useMapsLibrary } from "@vis.gl/react-google-maps"
import { TextField } from "./ui"

export interface PlaceSelection {
  placeId: string
  label: string
  lat: number
  lng: number
}

interface Props {
  label: string
  value: PlaceSelection | null
  onSelect: (place: PlaceSelection | null) => void
  error?: string
}

type Suggestion = google.maps.places.PlaceAutocompleteSuggestion

export function PlaceAutocompleteField({ label, value, onSelect, error }: Props) {
  const places = useMapsLibrary("places")
  const [text, setText] = useState(value?.label ?? "")
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [open, setOpen] = useState(false)
  const sessionToken = useRef<google.maps.places.AutocompleteSessionToken | null>(null)

  useEffect(() => {
    const input = text.trim()
    if (!places || !open || input.length < 2) {
      setSuggestions([])
      return
    }
    let cancelled = false
    // Debounce keystrokes so we don't bill a request per character.
    const timer = setTimeout(async () => {
      sessionToken.current ??= new places.AutocompleteSessionToken()
      try {
        const res = await places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
          input,
          sessionToken: sessionToken.current,
        })
        if (!cancelled) setSuggestions(res.suggestions.filter((s) => s.placePrediction))
      } catch {
        if (!cancelled) setSuggestions([])
      }
    }, 200)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [places, text, open])

  const choose = async (suggestion: Suggestion) => {
    const prediction = suggestion.placePrediction
    if (!prediction) return
    const label = prediction.text.toString()
    setText(label)
    setOpen(false)
    setSuggestions([])
    sessionToken.current = null // a selection ends the autocomplete session
    try {
      // A Place made from a prediction inherits its session token, so this
      // details call closes the session and bills it as one unit.
      const place = prediction.toPlace()
      await place.fetchFields({ fields: ["location"] })
      if (!place.location) throw new Error("no location")
      onSelect({
        placeId: prediction.placeId,
        label,
        lat: place.location.lat(),
        lng: place.location.lng(),
      })
    } catch {
      onSelect(null)
    }
  }

  return (
    <div className="relative">
      <TextField
        label={label}
        error={error}
        value={text}
        autoComplete="off"
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-autocomplete="list"
        onChange={(event) => {
          setText(event.target.value)
          setOpen(true)
          if (value) onSelect(null) // edited after selecting: no longer a valid place
        }}
        onBlur={() => setTimeout(() => setOpen(false), 100)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false)
        }}
      />
      {open && suggestions.length > 0 && (
        <ul
          role="listbox"
          className="absolute z-20 mt-1 max-h-64 w-full overflow-auto rounded-xl border border-border bg-white py-1 shadow-lg"
        >
          {suggestions.map((suggestion) => (
            <li
              key={suggestion.placePrediction!.placeId}
              role="option"
              aria-selected={false}
              className="cursor-pointer px-4 py-2 text-sm hover:bg-slate-100"
              onMouseDown={(event) => {
                event.preventDefault()
                choose(suggestion)
              }}
            >
              {suggestion.placePrediction!.text.toString()}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
