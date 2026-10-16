import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from './api.js';
import { formatLongDate, greeting, plural } from './format.js';
import Icon from './components/Icon.jsx';
import Sidebar from './components/Sidebar.jsx';
import Dashboard from './components/Dashboard.jsx';
import RoomsView from './components/RoomsView.jsx';
import ReservationsView from './components/ReservationsView.jsx';
import ReservationModal from './components/ReservationModal.jsx';
import RoomModal from './components/RoomModal.jsx';
import Toasts from './components/Toasts.jsx';
import { ConnectionBanner, ErrorState, LoadingState } from './components/States.jsx';

const VIEWS = {
  dashboard: 'Dashboard',
  rooms: 'Rooms',
  reservations: 'Reservations',
};

const REFRESH_INTERVAL_MS = 30_000;
const TOAST_TIMEOUT_MS = 4_500;

function viewFromHash() {
  const name = window.location.hash.replace(/^#\/?/, '');
  return Object.hasOwn(VIEWS, name) ? name : 'dashboard';
}

function subtitleFor(view, data) {
  const { stats, rooms, reservations } = data;
  if (view === 'rooms') {
    const floors = new Set(rooms.map((room) => room.floor)).size;
    const ready = rooms.filter((room) => !room.occupied && room.housekeeping === 'CLEAN').length;
    return `${plural(rooms.length, 'room')} across ${plural(floors, 'floor')} · ${ready} ready for guests`;
  }
  if (view === 'reservations') {
    const upcoming = reservations.filter((reservation) => reservation.status === 'BOOKED').length;
    return `${plural(reservations.length, 'reservation')} on file · ${upcoming} awaiting arrival`;
  }
  if (!stats) return formatLongDate();
  return `${formatLongDate()} · ${plural(stats.arrivals_today, 'arrival')} and ${plural(
    stats.departures_today,
    'departure',
  )} today`;
}

export default function App() {
  const [view, setView] = useState(viewFromHash);
  const [data, setData] = useState({
    stats: null,
    today: { arrivals: [], departures: [] },
    rooms: [],
    reservations: [],
  });
  const [meta, setMeta] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | ready | error
  const [loadError, setLoadError] = useState('');
  const [modal, setModal] = useState(null); // 'reservation' | 'room' | null
  const [busyKey, setBusyKey] = useState(null);
  const [toasts, setToasts] = useState([]);
  const toastId = useRef(0);

  useEffect(() => {
    const onHashChange = () => setView(viewFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const notify = useCallback(
    (message, tone = 'success') => {
      toastId.current += 1;
      const id = toastId.current;
      setToasts((current) => [...current.slice(-3), { id, message, tone }]);
      setTimeout(() => dismissToast(id), TOAST_TIMEOUT_MS);
    },
    [dismissToast],
  );

  const loadAll = useCallback(async () => {
    try {
      const [stats, today, rooms, reservations] = await Promise.all([
        api.dashboard.stats(),
        api.dashboard.today(),
        api.rooms.list(),
        api.reservations.list(),
      ]);
      setData({ stats, today, rooms, reservations });
      setLoadError('');
      setStatus('ready');
    } catch (error) {
      setLoadError(error.message);
      setStatus((current) => (current === 'ready' ? 'ready' : 'error'));
    }
  }, []);

  const loadMeta = useCallback(() => {
    api
      .meta()
      .then(setMeta)
      .catch(() => setMeta(null));
  }, []);

  useEffect(() => {
    loadAll();
    loadMeta();
    const timer = setInterval(() => {
      loadAll();
      loadMeta();
    }, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [loadAll, loadMeta]);

  const retry = useCallback(() => {
    setStatus((current) => (current === 'error' ? 'loading' : current));
    loadAll();
    loadMeta();
  }, [loadAll, loadMeta]);

  // Every mutation: mark the row busy, call the API, toast the outcome, then refetch.
  const runAction = useCallback(
    async (key, request, successMessage) => {
      setBusyKey(key);
      try {
        await request();
        notify(successMessage);
      } catch (error) {
        notify(error.message, 'error');
      } finally {
        setBusyKey(null);
        await loadAll();
      }
    },
    [loadAll, notify],
  );

  const actions = useMemo(
    () => ({
      checkIn: (reservation) =>
        runAction(
          `reservation-${reservation.id}`,
          () => api.reservations.checkIn(reservation.id),
          `${reservation.guest_name} checked in to room ${reservation.room_number}`,
        ),
      checkOut: (reservation) =>
        runAction(
          `reservation-${reservation.id}`,
          () => api.reservations.checkOut(reservation.id),
          `${reservation.guest_name} checked out · room ${reservation.room_number} sent to housekeeping`,
        ),
      cancel: (reservation) => {
        if (!window.confirm(`Cancel ${reservation.guest_name}'s reservation for room ${reservation.room_number}?`)) return;
        runAction(
          `reservation-${reservation.id}`,
          () => api.reservations.cancel(reservation.id),
          `Reservation for ${reservation.guest_name} cancelled`,
        );
      },
      deleteReservation: (reservation) => {
        if (!window.confirm(`Delete reservation #${reservation.id} for ${reservation.guest_name}? This cannot be undone.`)) {
          return;
        }
        runAction(
          `reservation-${reservation.id}`,
          () => api.reservations.remove(reservation.id),
          `Reservation #${reservation.id} deleted`,
        );
      },
      updateRoom: (room, changes, message) =>
        runAction(`room-${room.id}`, () => api.rooms.update(room.id, changes), message),
      deleteRoom: (room) => {
        if (!window.confirm(`Delete room ${room.number}? This cannot be undone.`)) return;
        runAction(`room-${room.id}`, () => api.rooms.remove(room.id), `Room ${room.number} deleted`);
      },
    }),
    [runAction],
  );

  const closeModal = useCallback(() => setModal(null), []);

  const createReservation = useCallback(
    async (payload) => {
      const reservation = await api.reservations.create(payload);
      setModal(null);
      notify(`Reservation confirmed for ${reservation.guest_name} · room ${reservation.room_number}`);
      await loadAll();
    },
    [loadAll, notify],
  );

  const createRoom = useCallback(
    async (payload) => {
      const room = await api.rooms.create(payload);
      setModal(null);
      notify(`Room ${room.number} added`);
      await loadAll();
    },
    [loadAll, notify],
  );

  const ready = status === 'ready';
  const title = view === 'dashboard' ? `${greeting()}, Shaurya` : VIEWS[view];

  return (
    <div className="app">
      <Sidebar view={view} meta={meta} />

      <main className="main">
        <header className="page-header">
          <div className="page-heading">
            <p className="eyebrow">FRONT OFFICE / {VIEWS[view].toUpperCase()}</p>
            <h1>{title}</h1>
            <p className="muted">{subtitleFor(view, data)}</p>
          </div>
          <div className="header-actions">
            {view === 'rooms' && (
              <button type="button" className="btn btn-secondary" disabled={!ready} onClick={() => setModal('room')}>
                <Icon name="plus" size={16} /> Add room
              </button>
            )}
            <button type="button" className="btn btn-primary" disabled={!ready} onClick={() => setModal('reservation')}>
              <Icon name="plus" size={16} /> New reservation
            </button>
          </div>
        </header>

        {ready && loadError && <ConnectionBanner message={loadError} onRetry={retry} />}
        {status === 'loading' && <LoadingState />}
        {status === 'error' && <ErrorState message={loadError} onRetry={retry} />}

        {ready && view === 'dashboard' && data.stats && (
          <Dashboard
            stats={data.stats}
            today={data.today}
            rooms={data.rooms}
            reservations={data.reservations}
            actions={actions}
            busyKey={busyKey}
          />
        )}
        {ready && view === 'rooms' && (
          <RoomsView rooms={data.rooms} actions={actions} busyKey={busyKey} onAddRoom={() => setModal('room')} />
        )}
        {ready && view === 'reservations' && (
          <ReservationsView
            reservations={data.reservations}
            actions={actions}
            busyKey={busyKey}
            onNewReservation={() => setModal('reservation')}
          />
        )}
      </main>

      {modal === 'reservation' && <ReservationModal onClose={closeModal} onSubmit={createReservation} />}
      {modal === 'room' && <RoomModal onClose={closeModal} onSubmit={createRoom} />}
      <Toasts toasts={toasts} onDismiss={dismissToast} />
    </div>
  );
}
