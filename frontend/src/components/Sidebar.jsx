import Icon from './Icon.jsx';
import { shortSha } from '../format.js';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'rooms', label: 'Rooms', icon: 'bed' },
  { id: 'reservations', label: 'Reservations', icon: 'calendar' },
];

// Baked in at build time by the Docker build (VITE_GIT_SHA build-arg = commit SHA).
const UI_VERSION = import.meta.env.VITE_GIT_SHA || 'dev';

export default function Sidebar({ view, meta }) {
  const apiVersion = meta?.git_sha || meta?.version;

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true">
          <Icon name="key" size={20} />
        </span>
        <div className="brand-text">
          <strong>StayDesk</strong>
          <small>Front office</small>
        </div>
      </div>

      <nav className="nav" aria-label="Main">
        {NAV_ITEMS.map((item) => (
          <a
            key={item.id}
            href={`#/${item.id}`}
            className={`nav-link${view === item.id ? ' active' : ''}`}
            aria-current={view === item.id ? 'page' : undefined}
          >
            <Icon name={item.icon} />
            <span>{item.label}</span>
          </a>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="property-card">
          <span className="property-avatar" aria-hidden="true">SV</span>
          <div>
            <strong>Front desk · Shift A</strong>
            <small>Shaurya Verma</small>
          </div>
        </div>
        <p className="version" title={`UI build ${UI_VERSION}${apiVersion ? ` · API build ${apiVersion}` : ''}`}>
          <span>UI {shortSha(UI_VERSION)}</span>
          <span aria-hidden="true">·</span>
          <span>API {shortSha(apiVersion)}</span>
        </p>
      </div>
    </aside>
  );
}
