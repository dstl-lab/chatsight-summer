"""Observed PR100 production boundary, deliberately not the Git merge time."""
from .historical import timestamp

# First schema-v1 production receipt verified by the October 16 read-only audit.
# A receipt establishes observed availability, not simultaneous client upgrades.
DEPLOYED = timestamp("2026-10-13T17:30:59.701280Z")
EXPORT_FORMAT = "pr100.production-export.v3"
MAX_UPLOAD = 2 * 1024**3
MAX_EXPANDED = 12 * 1024**3
MAX_ROWS = 10_000_000
MAX_LINE = 8 * 1024**2
