import Icon from './Icon.jsx';

export function LoadingState() {
  return (
    <div className="loading" aria-busy="true" aria-live="polite">
      <span className="sr-only">Loading front desk data…</span>
      <div className="kpi-grid">
        {Array.from({ length: 5 }, (_, index) => (
          <div key={index} className="stat-card skeleton" />
        ))}
      </div>
      <div className="dashboard-grid">
        <div className="panel skeleton skeleton-tall" />
        <div className="panel skeleton skeleton-tall" />
      </div>
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <section className="panel error-state" role="alert">
      <span className="error-icon" aria-hidden="true">
        <Icon name="alert" size={26} />
      </span>
      <h2>Can’t reach the StayDesk API</h2>
      <p className="muted">{message}. The dashboard will load as soon as the backend responds.</p>
      <ul className="error-hints">
        <li>
          Running locally? Start the full stack with <code>docker compose up --build</code>.
        </li>
        <li>
          On Kubernetes? Check <code>kubectl get pods -n staydesk</code> and the backend readiness probe.
        </li>
      </ul>
      <button type="button" className="btn btn-primary" onClick={onRetry}>
        <Icon name="refresh" size={16} /> Retry
      </button>
    </section>
  );
}

export function ConnectionBanner({ message, onRetry }) {
  return (
    <div className="banner" role="alert">
      <Icon name="alert" size={16} />
      <span>
        Lost connection to the API ({message}). Showing the last data we loaded.
      </span>
      <button type="button" className="btn btn-secondary btn-sm" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
