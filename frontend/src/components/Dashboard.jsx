import Icon from './Icon.jsx';
import StatCard from './StatCard.jsx';
import {
  ROOM_STATE_LABELS,
  ROOM_TYPE_LABELS,
  formatINR,
  formatShortDate,
  initials,
  parseISODate,
  plural,
  roomState,
  todayISO,
} from '../format.js';

const ROOM_STATES = ['available', 'occupied', 'dirty', 'out_of_service'];

function GuestRow({ reservation, meta, children }) {
  return (
    <li className="guest-row">
      <span className="avatar" aria-hidden="true">{initials(reservation.guest_name)}</span>
      <div className="guest-row-body">
        <strong>{reservation.guest_name}</strong>
        <small>
          Room {reservation.room_number} · {ROOM_TYPE_LABELS[reservation.room_type] ?? reservation.room_type} ·{' '}
          {plural(reservation.nights, 'night')}
        </small>
        {meta}
      </div>
      <div className="guest-row-actions">{children}</div>
    </li>
  );
}

function FrontDeskPanel({ today, roomsById, actions, busyKey }) {
  const todayIso = todayISO();

  return (
    <section className="panel frontdesk" aria-labelledby="frontdesk-title">
      <div className="panel-head">
        <div>
          <h2 id="frontdesk-title">Today at the front desk</h2>
          <p className="muted">Guests arriving and leaving today.</p>
        </div>
      </div>

      <div className="frontdesk-columns">
        <div className="frontdesk-column">
          <h3>
            <Icon name="login" size={16} /> Arrivals <span className="count">{today.arrivals.length}</span>
          </h3>
          {today.arrivals.length ? (
            <ul className="guest-list">
              {today.arrivals.map((reservation) => {
                const room = roomsById.get(reservation.room_id);
                const needsCleaning = room?.housekeeping === 'DIRTY';
                const busy = busyKey === `reservation-${reservation.id}` || busyKey === `room-${reservation.room_id}`;
                return (
                  <GuestRow
                    key={reservation.id}
                    reservation={reservation}
                    meta={needsCleaning && <span className="row-note warn">Room needs cleaning first</span>}
                  >
                    {needsCleaning ? (
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        disabled={busy}
                        onClick={() => actions.updateRoom(room, { housekeeping: 'CLEAN' }, `Room ${room.number} marked clean`)}
                      >
                        <Icon name="sparkle" size={14} /> Mark clean
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={busy}
                        onClick={() => actions.checkIn(reservation)}
                      >
                        Check in
                      </button>
                    )}
                  </GuestRow>
                );
              })}
            </ul>
          ) : (
            <p className="empty-inline">No more arrivals expected today.</p>
          )}
        </div>

        <div className="frontdesk-column">
          <h3>
            <Icon name="logout" size={16} /> Departures <span className="count">{today.departures.length}</span>
          </h3>
          {today.departures.length ? (
            <ul className="guest-list">
              {today.departures.map((reservation) => {
                const overdue = reservation.check_out < todayIso;
                return (
                  <GuestRow
                    key={reservation.id}
                    reservation={reservation}
                    meta={
                      <span className={`row-note ${overdue ? 'danger' : ''}`}>
                        {overdue ? `Overdue since ${formatShortDate(reservation.check_out)}` : 'Due to check out today'}
                      </span>
                    }
                  >
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      disabled={busyKey === `reservation-${reservation.id}`}
                      onClick={() => actions.checkOut(reservation)}
                    >
                      Check out
                    </button>
                  </GuestRow>
                );
              })}
            </ul>
          ) : (
            <p className="empty-inline">No departures due today.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function RoomStatusPanel({ rooms }) {
  const counts = rooms.reduce((acc, room) => {
    const state = roomState(room);
    acc[state] = (acc[state] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <section className="panel" aria-labelledby="room-status-title">
      <div className="panel-head">
        <div>
          <h2 id="room-status-title">Room status</h2>
          <p className="muted">Live view of every room.</p>
        </div>
        <a className="link" href="#/rooms">
          Manage <Icon name="arrowRight" size={14} />
        </a>
      </div>
      <ul className="legend">
        {ROOM_STATES.map((state) => (
          <li key={state}>
            <span className={`legend-swatch state-${state}`} aria-hidden="true" />
            {ROOM_STATE_LABELS[state]} <b>{counts[state] ?? 0}</b>
          </li>
        ))}
      </ul>
      {rooms.length ? (
        <ul className="room-tiles">
          {rooms.map((room) => {
            const state = roomState(room);
            return (
              <li
                key={room.id}
                className={`room-tile state-${state}`}
                title={`Room ${room.number} · ${ROOM_TYPE_LABELS[room.room_type]} · ${ROOM_STATE_LABELS[state]}`}
              >
                <span>{room.number}</span>
                <span className="sr-only">{ROOM_STATE_LABELS[state]}</span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty-inline">No rooms set up yet.</p>
      )}
    </section>
  );
}

function UpcomingPanel({ reservations }) {
  return (
    <section className="panel" aria-labelledby="upcoming-title">
      <div className="panel-head">
        <div>
          <h2 id="upcoming-title">Upcoming reservations</h2>
          <p className="muted">Next confirmed stays.</p>
        </div>
        <a className="link" href="#/reservations">
          View all <Icon name="arrowRight" size={14} />
        </a>
      </div>
      {reservations.length ? (
        <ul className="upcoming-list">
          {reservations.map((reservation) => {
            const date = parseISODate(reservation.check_in);
            return (
              <li key={reservation.id}>
                <span className="date-chip" aria-hidden="true">
                  <b>{date.getDate()}</b>
                  {date.toLocaleString('en-IN', { month: 'short' })}
                </span>
                <div className="upcoming-body">
                  <strong>{reservation.guest_name}</strong>
                  <small>
                    Room {reservation.room_number} · {formatShortDate(reservation.check_in)} ·{' '}
                    {plural(reservation.nights, 'night')}
                  </small>
                </div>
                <span className="amount">{formatINR(reservation.total_amount)}</span>
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="empty-inline">No upcoming reservations. Create one with “New reservation”.</p>
      )}
    </section>
  );
}

export default function Dashboard({ stats, today, rooms, reservations, actions, busyKey }) {
  const todayIso = todayISO();
  const sellableRooms = Math.max(0, stats.total_rooms - stats.out_of_service_rooms);
  const roomsById = new Map(rooms.map((room) => [room.id, room]));
  const upcoming = reservations
    .filter((reservation) => reservation.status === 'BOOKED' && reservation.check_in > todayIso)
    .sort((a, b) => a.check_in.localeCompare(b.check_in))
    .slice(0, 5);

  return (
    <>
      <section className="kpi-grid" aria-label="Key metrics">
        <StatCard
          icon="percent"
          label="Occupancy"
          value={`${Math.round(stats.occupancy_rate)}%`}
          progress={stats.occupancy_rate}
          hint={`${stats.occupied_rooms} of ${plural(sellableRooms, 'sellable room')}`}
          tone="teal"
        />
        <StatCard icon="login" label="Arrivals today" value={stats.arrivals_today} hint="expected check-ins" tone="blue" />
        <StatCard
          icon="logout"
          label="Departures today"
          value={stats.departures_today}
          hint="due to check out"
          tone="amber"
        />
        <StatCard
          icon="users"
          label="In-house guests"
          value={stats.in_house_guests}
          hint={`across ${plural(stats.occupied_rooms, 'room')}`}
          tone="green"
        />
        <StatCard
          icon="rupee"
          label="Booked revenue"
          value={formatINR(stats.revenue_this_month)}
          hint={`this month · ${plural(stats.upcoming_reservations, 'upcoming stay')}`}
          tone="brass"
        />
      </section>

      <div className="dashboard-grid">
        <FrontDeskPanel today={today} roomsById={roomsById} actions={actions} busyKey={busyKey} />
        <div className="dashboard-side">
          <RoomStatusPanel rooms={rooms} />
          <UpcomingPanel reservations={upcoming} />
        </div>
      </div>
    </>
  );
}
