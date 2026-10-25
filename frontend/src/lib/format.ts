export function formatDuration(minutes: number) {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours}h ${remainder}m`
}

export function formatMoney(value: number) {
  return `$${value.toFixed(2)}`
}
