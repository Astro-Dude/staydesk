"""Business metrics exported on /metrics next to the HTTP metrics from the instrumentator."""

from prometheus_client import Counter

RESERVATION_EVENTS = Counter(
    "staydesk_reservation_events_total",
    "Reservation lifecycle events handled by the API",
    ["event"],
)

# Touch each label once so the series exist (at 0) before the first event — dashboards
# and rate() queries then show a flat line instead of "No data".
for _event in ("created", "checked_in", "checked_out", "cancelled"):
    RESERVATION_EVENTS.labels(event=_event)
