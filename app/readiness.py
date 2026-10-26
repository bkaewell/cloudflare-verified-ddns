# ─── Standard library imports ───
from enum import Enum, auto


class ReadinessState(Enum):
    """
    Readiness classifications used to gate network-dependent side effects.

    • INIT        — startup, no assumptions
    • PROBING     — network looks healthy, stability not proven
    • READY       — safe to act
    • NOT_READY   — known failure; observe only

    Invariants:
    • Promotions are monotonic (INIT/NOT_READY → PROBING → READY)
    • Any verified failure forces NOT_READY
    """
    INIT = auto()
    PROBING = auto()
    READY = auto()
    NOT_READY = auto()

    def __str__(self) -> str:
        return self.name

READINESS_EMOJI = {
    ReadinessState.INIT:      "⚪",
    ReadinessState.PROBING:   "🟡",
    ReadinessState.READY:     "💚",
    ReadinessState.NOT_READY: "🔴",
}

class ReadinessController:
    """
    Monotonic readiness gate for network-driven side effects.

    • Single source of truth for “is it safe to act?”
    • Conservative by design: readiness must be earned
    • Fail-fast demotion on any verified WAN failure
    """

    def __init__(self):
        self.state: ReadinessState = ReadinessState.INIT

    def _demote(self) -> None:
        """
        Immediately revoke readiness after a verified failure.
        """
        self.state = ReadinessState.NOT_READY

    def reprobe(self) -> None:
        """
        Re-enter the stability-probing window without marking the network down.

        Used when the WAN path is healthy but a new public IP has appeared and
        must earn READY again before DNS mutation.
        """
        self.state = ReadinessState.PROBING

    def advance(
            self, 
            wan_path_ok: bool, 
            allow_promotion: bool = True,
        ) -> None:
        """
        Advance the readiness FSM by one evaluation cycle.

        • Any WAN failure → NOT_READY
        • Promotions are sequential (INIT/NOT_READY → PROBING → READY)
        • PROBING is observational only
        • Promotion to READY is externally gated
        """
        if not wan_path_ok:
            self._demote()
            return

        match self.state:
            case ReadinessState.INIT | ReadinessState.NOT_READY:
                self.state = ReadinessState.PROBING

            case ReadinessState.PROBING if allow_promotion:
                self.state = ReadinessState.READY

            case _:
                pass  # READY stays READY
