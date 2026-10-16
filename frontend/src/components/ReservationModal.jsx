import { useEffect, useState } from 'react';
import Modal from './Modal.jsx';
import { api } from '../api.js';
import { ROOM_TYPE_LABELS, addDays, formatINR, nightsBetween, plural, todayISO } from '../format.js';

function initialForm() {
  const today = todayISO();
  return {
    guest_name: '',
    guest_email: '',
    guest_phone: '',
    check_in: today,
    check_out: addDays(today, 1),
    guests: '2',
    room_id: '',
    notes: '',
  };
}

export default function ReservationModal({ onClose, onSubmit }) {
  const [form, setForm] = useState(initialForm);
  const [rooms, setRooms] = useState([]);
  const [roomsStatus, setRoomsStatus] = useState('idle'); // idle | loading | ready | error
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const nights = nightsBetween(form.check_in, form.check_out);
  const guests = Number(form.guests);
  const datesValid = Boolean(form.check_in && form.check_out) && nights > 0;
  const guestsValid = Number.isInteger(guests) && guests >= 1;

  // Re-query availability whenever the stay dates or party size change.
  useEffect(() => {
    if (!datesValid || !guestsValid) {
      setRooms([]);
      setRoomsStatus('idle');
      return undefined;
    }

    let cancelled = false;
    setRoomsStatus('loading');
    const timer = setTimeout(() => {
      api.rooms
        .availability({ check_in: form.check_in, check_out: form.check_out, guests })
        .then((available) => {
          if (cancelled) return;
          setRooms(available);
          setRoomsStatus('ready');
          setForm((current) =>
            available.some((room) => String(room.id) === current.room_id)
              ? current
              : { ...current, room_id: available[0] ? String(available[0].id) : '' },
          );
        })
        .catch((err) => {
          if (cancelled) return;
          setRooms([]);
          setRoomsStatus('error');
          setError(err.message);
        });
    }, 200);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [form.check_in, form.check_out, guests, datesValid, guestsValid]);

  const setField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const selectedRoom = rooms.find((room) => String(room.id) === form.room_id);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!datesValid) {
      setError('Check-out must be after check-in.');
      return;
    }
    if (!selectedRoom) {
      setError('Choose an available room for these dates.');
      return;
    }

    const phone = form.guest_phone.trim();
    const notes = form.notes.trim();
    setSaving(true);
    setError('');
    try {
      await onSubmit({
        room_id: selectedRoom.id,
        guest_name: form.guest_name.trim(),
        guest_email: form.guest_email.trim(),
        ...(phone ? { guest_phone: phone } : {}),
        guests,
        check_in: form.check_in,
        check_out: form.check_out,
        ...(notes ? { notes } : {}),
      });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <Modal eyebrow="NEW RESERVATION" title="Book a stay" onClose={onClose}>
      <form className="form" onSubmit={handleSubmit}>
        <fieldset className="form-section">
          <legend>Guest</legend>
          <label>
            Full name
            <input
              name="guest_name"
              required
              maxLength={120}
              autoFocus
              autoComplete="name"
              placeholder="e.g. Ananya Rao"
              value={form.guest_name}
              onChange={setField('guest_name')}
            />
          </label>
          <div className="form-row">
            <label>
              Email
              <input
                name="guest_email"
                type="email"
                required
                autoComplete="email"
                placeholder="guest@example.com"
                value={form.guest_email}
                onChange={setField('guest_email')}
              />
            </label>
            <label>
              <span className="label-text">
                Phone <span className="optional">optional</span>
              </span>
              <input
                name="guest_phone"
                type="tel"
                autoComplete="tel"
                placeholder="+91 98765 43210"
                value={form.guest_phone}
                onChange={setField('guest_phone')}
              />
            </label>
          </div>
        </fieldset>

        <fieldset className="form-section">
          <legend>Stay</legend>
          <div className="form-row form-row-3">
            <label>
              Check-in
              <input name="check_in" type="date" required value={form.check_in} onChange={setField('check_in')} />
            </label>
            <label>
              Check-out
              <input
                name="check_out"
                type="date"
                required
                min={form.check_in ? addDays(form.check_in, 1) : undefined}
                value={form.check_out}
                onChange={setField('check_out')}
              />
            </label>
            <label>
              Guests
              <input
                name="guests"
                type="number"
                min={1}
                max={8}
                required
                value={form.guests}
                onChange={setField('guests')}
              />
            </label>
          </div>
          {!datesValid && form.check_in && form.check_out && (
            <p className="field-error">Check-out must be at least one night after check-in.</p>
          )}

          <label>
            Room
            <select
              name="room_id"
              required
              value={form.room_id}
              onChange={setField('room_id')}
              disabled={roomsStatus !== 'ready' || !rooms.length}
            >
              {roomsStatus === 'loading' && <option value="">Checking availability…</option>}
              {roomsStatus === 'idle' && <option value="">Pick valid dates first</option>}
              {roomsStatus === 'error' && <option value="">Could not load availability</option>}
              {roomsStatus === 'ready' && !rooms.length && <option value="">No rooms free for these dates</option>}
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  Room {room.number} · {ROOM_TYPE_LABELS[room.room_type]} · sleeps {room.capacity} ·{' '}
                  {formatINR(room.nightly_rate)}/night
                </option>
              ))}
            </select>
          </label>
          {roomsStatus === 'ready' && !rooms.length && (
            <p className="field-hint warn">No rooms free for these dates — try other dates or fewer guests.</p>
          )}

          <label>
            <span className="label-text">
              Notes <span className="optional">optional</span>
            </span>
            <textarea
              name="notes"
              rows={2}
              maxLength={500}
              placeholder="Late arrival, airport pickup, dietary needs…"
              value={form.notes}
              onChange={setField('notes')}
            />
          </label>
        </fieldset>

        <div className="price-preview" aria-live="polite">
          {selectedRoom && datesValid ? (
            <>
              <span>
                {plural(nights, 'night')} × {formatINR(selectedRoom.nightly_rate)}
              </span>
              <strong>{formatINR(nights * selectedRoom.nightly_rate)}</strong>
            </>
          ) : (
            <span className="muted">Choose dates and a room to see the total.</span>
          )}
        </div>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving || !selectedRoom || !datesValid}>
            {saving ? 'Booking…' : 'Confirm reservation'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
