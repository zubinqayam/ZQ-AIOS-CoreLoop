# ---------------------------------------------------------------------------
# ZQ-AIOS-CoreLoop / core package
# ---------------------------------------------------------------------------
# Public API surface — governed by RUNTIME_CONTRACT_v1.md
# Imports are intentionally explicit; wildcard imports are PROHIBITED.
# ---------------------------------------------------------------------------

# -- Phase 1: Priority Runtime Skeletons ------------------------------------
from .event_appender import EventAppender          # WAL / append-only log
from .replay_engine import ReplayEngine            # Deterministic replay engine
from .keyhole_gateway import KeyholeGateway        # Enterprise trust boundary

# -- Existing Core Components -----------------------------------------------
# (Legacy imports preserved; do not remove without CONTRACT review)
try:
    from .agent import Agent
except ImportError:
    pass

try:
    from .event_bus import EventBus
except ImportError:
    pass

__all__ = [
    # Phase 1 skeletons
    "EventAppender",
    "ReplayEngine",
    "KeyholeGateway",
    # Existing
    "Agent",
    "EventBus",
]
