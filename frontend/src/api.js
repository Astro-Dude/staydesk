// Thin fetch wrapper around the StayDesk REST API.
// The browser always calls relative /api paths; Vite (dev), Nginx (Docker) or the
// Kubernetes Ingress route them to the FastAPI backend.
const BASE = '/api';

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// FastAPI returns either {"detail": "message"} or, for validation errors,
// {"detail": [{"loc": [...], "msg": "..."}]}. Turn both into one readable sentence.
function describeDetail(detail) {
  if (!detail) return '';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => String(item?.msg ?? item).replace(/^Value error, /, ''))
      .join('; ');
  }
  return String(detail);
}

async function request(path, { method = 'GET', body } = {}) {
  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers: body === undefined ? { Accept: 'application/json' } : { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError('Cannot reach the StayDesk API', 0);
  }

  if (response.status === 204) return null;

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status >= 500 && !data) {
      throw new ApiError(`StayDesk API is unavailable (HTTP ${response.status})`, response.status);
    }
    throw new ApiError(describeDetail(data?.detail) || `Request failed (HTTP ${response.status})`, response.status);
  }
  return data;
}

function query(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.set(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : '';
}

export const api = {
  meta: () => request('/meta'),

  dashboard: {
    stats: () => request('/dashboard/stats'),
    today: () => request('/dashboard/today'),
  },

  rooms: {
    list: (filters = {}) => request(`/rooms${query(filters)}`),
    availability: ({ check_in, check_out, guests }) =>
      request(`/rooms/availability${query({ check_in, check_out, guests })}`),
    create: (room) => request('/rooms', { method: 'POST', body: room }),
    update: (id, changes) => request(`/rooms/${id}`, { method: 'PUT', body: changes }),
    remove: (id) => request(`/rooms/${id}`, { method: 'DELETE' }),
  },

  reservations: {
    list: (filters = {}) => request(`/reservations${query(filters)}`),
    create: (reservation) => request('/reservations', { method: 'POST', body: reservation }),
    update: (id, changes) => request(`/reservations/${id}`, { method: 'PUT', body: changes }),
    remove: (id) => request(`/reservations/${id}`, { method: 'DELETE' }),
    checkIn: (id) => request(`/reservations/${id}/check-in`, { method: 'POST' }),
    checkOut: (id) => request(`/reservations/${id}/check-out`, { method: 'POST' }),
    cancel: (id) => request(`/reservations/${id}/cancel`, { method: 'POST' }),
  },
};
