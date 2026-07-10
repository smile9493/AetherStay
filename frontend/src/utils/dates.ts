/** Date-only helpers (YYYY-MM-DD), always in local calendar. */

export function todayStart(): Date {
  const d = new Date()
  d.setHours(0, 0, 0, 0)
  return d
}

export function parseDateOnly(s: string): Date {
  const [y, m, day] = s.split('-').map(Number)
  return new Date(y, m - 1, day)
}

export function formatDateOnly(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function addDays(dateStr: string, days: number): string {
  const d = parseDateOnly(dateStr)
  d.setDate(d.getDate() + days)
  return formatDateOnly(d)
}

export function isValidDateRange(checkIn: string, checkOut: string): boolean {
  return parseDateOnly(checkOut) > parseDateOnly(checkIn)
}

export function isPastDate(d: Date): boolean {
  const target = new Date(d)
  target.setHours(0, 0, 0, 0)
  return target < todayStart()
}

/** True when calendar day of `d` is on or before the date-only string. */
export function isOnOrBeforeDateStr(d: Date, dateStr: string): boolean {
  const target = new Date(d)
  target.setHours(0, 0, 0, 0)
  const cmp = parseDateOnly(dateStr)
  cmp.setHours(0, 0, 0, 0)
  return target <= cmp
}
