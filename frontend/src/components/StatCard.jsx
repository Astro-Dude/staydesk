import Icon from './Icon.jsx';

export default function StatCard({ icon, label, value, hint, tone = 'teal', progress }) {
  return (
    <article className={`stat-card tone-${tone}`}>
      <div className="stat-head">
        <span className="stat-label">{label}</span>
        <span className="stat-icon" aria-hidden="true">
          <Icon name={icon} size={16} />
        </span>
      </div>
      <strong className="stat-value">{value}</strong>
      {progress !== undefined && (
        <div
          className="progress"
          role="progressbar"
          aria-label={`${label} ${Math.round(progress)}%`}
          aria-valuenow={Math.round(progress)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <span style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
        </div>
      )}
      <span className="stat-hint">{hint}</span>
    </article>
  );
}
