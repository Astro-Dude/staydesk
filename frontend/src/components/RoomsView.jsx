import { useMemo, useState } from 'react';
import Icon from './Icon.jsx';
import StatusBadge from './StatusBadge.jsx';
import { ROOM_TYPE_LABELS, formatINR, roomState } from '../format.js';

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'available', label: 'Available' },
  { id: 'occupied', label: 'Occupied' },
  { id: 'dirty', label: 'Needs cleaning' },
  { id: 'out_of_service', label: 'Out of service' },
];

function RoomCard({ room, busy, actions }) {
  const state = roomState(room);
  const update = (changes, message) => actions.updateRoom(room, changes, message);

  return (
    <article className={`room-card state-${state}`}>
      <header className="room-card-head">
        <div>
          <span className="room-number">{room.number}</span>
          <span className="room-type">{ROOM_TYPE_LABELS[room.room_type] ?? room.room_type}</span>
        </div>
        <StatusBadge kind="room" value={state} />
      </header>

      <dl className="room-facts">
        <div>
          <dt>Floor</dt>
          <dd>{room.floor}</dd>
        </div>
        <div>
          <dt>Sleeps</dt>
          <dd>{room.capacity}</dd>
        </div>
        <div>
          <dt>Rate</dt>
          <dd>
            {formatINR(room.nightly_rate)}
            <small>per night</small>
          </dd>
        </div>
      </dl>

      <footer className="room-actions">
        {room.housekeeping === 'DIRTY' && (
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={busy}
            onClick={() => update({ housekeeping: 'CLEAN' }, `Room ${room.number} marked clean`)}
          >
            <Icon name="sparkle" size={14} /> Mark clean
          </button>
        )}
        {room.housekeeping === 'CLEAN' && (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={busy}
            onClick={() => update({ housekeeping: 'DIRTY' }, `Room ${room.number} sent to housekeeping`)}
          >
            <Icon name="droplet" size={14} /> Mark dirty
          </button>
        )}
        {room.housekeeping === 'OUT_OF_SERVICE' ? (
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={busy}
            onClick={() => update({ housekeeping: 'CLEAN' }, `Room ${room.number} is back in service`)}
          >
            <Icon name="check" size={14} /> Return to service
          </button>
        ) : (
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            disabled={busy || room.occupied}
            title={room.occupied ? 'Check the guest out before taking this room out of service' : undefined}
            onClick={() => update({ housekeeping: 'OUT_OF_SERVICE' }, `Room ${room.number} taken out of service`)}
          >
            <Icon name="wrench" size={14} /> Out of service
          </button>
        )}
        <button
          type="button"
          className="btn-icon danger"
          aria-label={`Delete room ${room.number}`}
          title="Delete room"
          disabled={busy}
          onClick={() => actions.deleteRoom(room)}
        >
          <Icon name="trash" size={16} />
        </button>
      </footer>
    </article>
  );
}

export default function RoomsView({ rooms, actions, busyKey, onAddRoom }) {
  const [filter, setFilter] = useState('all');

  const counts = useMemo(() => {
    const result = { all: rooms.length };
    rooms.forEach((room) => {
      const state = roomState(room);
      result[state] = (result[state] ?? 0) + 1;
    });
    return result;
  }, [rooms]);

  const visible = filter === 'all' ? rooms : rooms.filter((room) => roomState(room) === filter);

  return (
    <section className="panel" aria-labelledby="rooms-title">
      <div className="panel-head">
        <div>
          <h2 id="rooms-title">All rooms</h2>
          <p className="muted">Housekeeping and availability across the property.</p>
        </div>
        <div className="chips" role="group" aria-label="Filter rooms">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`chip${filter === item.id ? ' selected' : ''}`}
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
            >
              {item.label}
              <span className="chip-count">{counts[item.id] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      {visible.length ? (
        <div className="room-grid">
          {visible.map((room) => (
            <RoomCard key={room.id} room={room} busy={busyKey === `room-${room.id}`} actions={actions} />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <Icon name="bed" size={28} />
          <p>{rooms.length ? 'No rooms match this filter.' : 'No rooms yet — add your first room to start taking bookings.'}</p>
          {!rooms.length && (
            <button type="button" className="btn btn-primary" onClick={onAddRoom}>
              <Icon name="plus" size={16} /> Add room
            </button>
          )}
        </div>
      )}
    </section>
  );
}
