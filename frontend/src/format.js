// Formatting helpers shared by the views. Dates from the API are plain
// "YYYY-MM-DD" strings (hotel dates, no time zone), so they are parsed as local dates.

const inr = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

const shortDate = new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' });
const longDate = new Intl.DateTimeFormat('en-IN', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  year: 'numeric',
});

const DAY_MS = 24 * 60 * 60 * 1000;

export const ROOM_TYPE_LABELS = {
  SINGLE: 'Single',
  DOUBLE: 'Double',
  DELUXE: 'Deluxe',
  SUITE: 'Suite',
};

export const RESERVATION_STATUS_LABELS = {
  BOOKED: 'Booked',
  CHECKED_IN: 'Checked in',
  CHECKED_OUT: 'Checked out',
  CANCELLED: 'Cancelled',
};

export const ROOM_STATE_LABELS = {
  available: 'Available',
  occupied: 'Occupied',
  dirty: 'Needs cleaning',
  out_of_service: 'Out of service',
};

export function formatINR(amount) {
  return inr.format(amount ?? 0);
}

export function parseISODate(iso) {
  const [year, month, day] = iso.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function toISODate(date) {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

export function todayISO() {
  return toISODate(new Date());
}

export function addDays(iso, days) {
  const date = parseISODate(iso);
  date.setDate(date.getDate() + days);
  return toISODate(date);
}

export function nightsBetween(checkIn, checkOut) {
  if (!checkIn || !checkOut) return 0;
  return Math.round((parseISODate(checkOut) - parseISODate(checkIn)) / DAY_MS);
}

export function formatShortDate(iso) {
  return shortDate.format(parseISODate(iso));
}

export function formatLongDate(date = new Date()) {
  return longDate.format(date);
}

export function formatStay(reservation) {
  return `${formatShortDate(reservation.check_in)} → ${formatShortDate(reservation.check_out)}`;
}

export function plural(count, word, pluralWord = `${word}s`) {
  return `${count} ${count === 1 ? word : pluralWord}`;
}

export function greeting(now = new Date()) {
  const hour = now.getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export function shortSha(sha) {
  if (!sha) return '—';
  return /^[0-9a-f]{8,}$/i.test(sha) ? sha.slice(0, 7) : sha;
}

export function initials(name = '') {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return '?';
  return (parts[0][0] + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase();
}

// A room's front-desk state combines occupancy with its housekeeping status.
export function roomState(room) {
  if (room.occupied) return 'occupied';
  if (room.housekeeping === 'OUT_OF_SERVICE') return 'out_of_service';
  if (room.housekeeping === 'DIRTY') return 'dirty';
  return 'available';
}
