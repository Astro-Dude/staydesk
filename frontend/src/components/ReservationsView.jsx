import { useMemo, useState } from 'react';
import Icon from './Icon.jsx';
import StatusBadge from './StatusBadge.jsx';
import { ROOM_TYPE_LABELS, formatINR, formatShortDate, formatStay, plural, todayISO } from '../format.js';

const TABS = [
  { id: 'ALL', label: 'All' },
  { id: 'BOOKED', label: 'Booked' },
  { id: 'CHECKED_IN', label: 'Checked in' },
  { id: 'CHECKED_OUT', label: 'Checked out' },
  { id: 'CANCELLED', label: 'Cancelled' },
];

function RowActions({ reservation, busy, actions }) {
  const today = todayISO();

  if (reservation.status === 'BOOKED') {
    const arrivalOpen = reservation.check_in <= today && today < reservation.check_out;
    return (
      <>
        <button
          type="button"
          className="btn btn-primary btn-sm"
          disabled={busy || !arrivalOpen}
          title={arrivalOpen ? undefined : `Check-in opens on ${formatShortDate(reservation.check_in)}`}
          onClick={() => actions.checkIn(reservation)}
        >
          Check in
        </button>
        <button
          type="button"
          className="btn btn-ghost btn-sm"
          disabled={busy}
          onClick={() => actions.cancel(reservation)}
        >
          Cancel
        </button>
      </>
    );
  }

  if (reservation.status === 'CHECKED_IN') {
    return (
      <button
        type="button"
        className="btn btn-secondary btn-sm"
        disabled={busy}
        onClick={() => actions.checkOut(reservation)}
      >
        Check out
      </button>
    );
  }

  return (
    <button
      type="button"
      className="btn-icon danger"
      aria-label={`Delete reservation for ${reservation.guest_name}`}
      title="Delete reservation"
      disabled={busy}
      onClick={() => actions.deleteReservation(reservation)}
    >
      <Icon name="trash" size={16} />
    </button>
  );
}

export default function ReservationsView({ reservations, actions, busyKey, onNewReservation }) {
  const [tab, setTab] = useState('ALL');
  const [search, setSearch] = useState('');

  const counts = useMemo(() => {
    const result = { ALL: reservations.length };
    reservations.forEach((reservation) => {
      result[reservation.status] = (result[reservation.status] ?? 0) + 1;
    });
    return result;
  }, [reservations]);

  const term = search.trim().toLowerCase();
  const visible = reservations.filter((reservation) => {
    if (tab !== 'ALL' && reservation.status !== tab) return false;
    if (!term) return true;
    return [reservation.guest_name, reservation.guest_email, reservation.room_number]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(term));
  });

  return (
    <section className="panel" aria-labelledby="reservations-title">
      <div className="panel-head panel-head-wrap">
        <div>
          <h2 id="reservations-title">Reservations</h2>
          <p className="muted">Every booking, from confirmation to check-out.</p>
        </div>
        <label className="search">
          <Icon name="search" size={16} />
          <span className="sr-only">Search reservations</span>
          <input
            type="search"
            placeholder="Search guest or room"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
      </div>

      <div className="tabs" role="group" aria-label="Filter by status">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab${tab === item.id ? ' selected' : ''}`}
            aria-pressed={tab === item.id}
            onClick={() => setTab(item.id)}
          >
            {item.label}
            <span className="chip-count">{counts[item.id] ?? 0}</span>
          </button>
        ))}
      </div>

      {visible.length ? (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Guest</th>
                <th scope="col">Room</th>
                <th scope="col">Stay</th>
                <th scope="col" className="num">Guests</th>
                <th scope="col" className="num">Amount</th>
                <th scope="col">Status</th>
                <th scope="col" className="actions-col">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {visible.map((reservation) => (
                <tr key={reservation.id}>
                  <td>
                    <div className="cell-stack">
                      <strong>{reservation.guest_name}</strong>
                      <small>{reservation.guest_email}</small>
                    </div>
                  </td>
                  <td>
                    <div className="cell-stack">
                      <strong>Room {reservation.room_number}</strong>
                      <small>{ROOM_TYPE_LABELS[reservation.room_type] ?? reservation.room_type}</small>
                    </div>
                  </td>
                  <td>
                    <div className="cell-stack">
                      <strong>{formatStay(reservation)}</strong>
                      <small>{plural(reservation.nights, 'night')}</small>
                    </div>
                  </td>
                  <td className="num">{reservation.guests}</td>
                  <td className="num amount">{formatINR(reservation.total_amount)}</td>
                  <td>
                    <StatusBadge value={reservation.status} />
                  </td>
                  <td className="actions-col">
                    <div className="row-actions">
                      <RowActions
                        reservation={reservation}
                        busy={busyKey === `reservation-${reservation.id}`}
                        actions={actions}
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state">
          <Icon name="calendar" size={28} />
          <p>
            {reservations.length
              ? 'No reservations match this filter.'
              : 'No reservations yet — book the first guest to get started.'}
          </p>
          {!reservations.length && (
            <button type="button" className="btn btn-primary" onClick={onNewReservation}>
              <Icon name="plus" size={16} /> New reservation
            </button>
          )}
        </div>
      )}
    </section>
  );
}
