import { RESERVATION_STATUS_LABELS, ROOM_STATE_LABELS } from '../format.js';

// kind="reservation" expects BOOKED/CHECKED_IN/...; kind="room" expects a roomState() value.
export default function StatusBadge({ kind = 'reservation', value }) {
  const labels = kind === 'room' ? ROOM_STATE_LABELS : RESERVATION_STATUS_LABELS;
  return (
    <span className={`badge badge-${kind} is-${value.toLowerCase()}`}>
      <span className="badge-dot" aria-hidden="true" />
      {labels[value] ?? value}
    </span>
  );
}
