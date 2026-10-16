import { useState } from 'react';
import Modal from './Modal.jsx';
import { ROOM_TYPE_LABELS } from '../format.js';

// Sensible defaults applied when the room type changes.
const TYPE_DEFAULTS = {
  SINGLE: { capacity: '1', nightly_rate: '2500' },
  DOUBLE: { capacity: '2', nightly_rate: '4000' },
  DELUXE: { capacity: '3', nightly_rate: '6500' },
  SUITE: { capacity: '4', nightly_rate: '12000' },
};

export default function RoomModal({ onClose, onSubmit }) {
  const [form, setForm] = useState({
    number: '',
    room_type: 'DOUBLE',
    floor: '1',
    housekeeping: 'CLEAN',
    ...TYPE_DEFAULTS.DOUBLE,
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const setField = (field) => (event) => setForm((current) => ({ ...current, [field]: event.target.value }));

  const changeType = (event) => {
    const roomType = event.target.value;
    setForm((current) => ({ ...current, room_type: roomType, ...TYPE_DEFAULTS[roomType] }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    try {
      await onSubmit({
        number: form.number.trim(),
        room_type: form.room_type,
        floor: Number(form.floor),
        capacity: Number(form.capacity),
        nightly_rate: Number(form.nightly_rate),
        housekeeping: form.housekeeping,
      });
    } catch (err) {
      setError(err.message);
      setSaving(false);
    }
  };

  return (
    <Modal eyebrow="NEW ROOM" title="Add a room" onClose={onClose}>
      <form className="form" onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            Room number
            <input
              name="number"
              required
              maxLength={10}
              autoFocus
              placeholder="e.g. 305"
              value={form.number}
              onChange={setField('number')}
            />
          </label>
          <label>
            Type
            <select name="room_type" value={form.room_type} onChange={changeType}>
              {Object.entries(ROOM_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="form-row form-row-3">
          <label>
            Floor
            <input name="floor" type="number" min={0} max={200} required value={form.floor} onChange={setField('floor')} />
          </label>
          <label>
            Sleeps
            <input
              name="capacity"
              type="number"
              min={1}
              max={8}
              required
              value={form.capacity}
              onChange={setField('capacity')}
            />
          </label>
          <label>
            Rate / night (₹)
            <input
              name="nightly_rate"
              type="number"
              min={1}
              step={50}
              required
              value={form.nightly_rate}
              onChange={setField('nightly_rate')}
            />
          </label>
        </div>
        <label>
          Housekeeping status
          <select name="housekeeping" value={form.housekeeping} onChange={setField('housekeeping')}>
            <option value="CLEAN">Clean — ready for guests</option>
            <option value="DIRTY">Needs cleaning</option>
            <option value="OUT_OF_SERVICE">Out of service</option>
          </select>
        </label>

        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}

        <div className="form-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Add room'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
