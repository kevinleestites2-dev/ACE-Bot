"""
memory.py — ACE Bot Memory Handler
═══════════════════════════════════
v2.0.0: Letta stub REPLACED with MUSE self-evolving memory.

AceMemory is the live memory layer:
  - Captures every interaction to disk
  - Reflects on outcomes to extract lessons
  - Evolves Joe's preference weights over time
  - Injects learned context before every reply

Letta is kept as an optional fallback if the env var is set.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# MUSE — self-evolving memory (primary)
from ace_bot.muse_memory import AceMemory

# Optional Letta fallback
LETTA_URL = os.getenv("LETTA_URL")
LETTA_KEY = os.getenv("LETTA_API_KEY")


class MemoryHandler:
    """
    Drop-in replacement for the old Letta stub.
    Same interface (get_memory / save_memory) — backed by MUSE.

    Additional methods:
      get_context(user_message)  → full MUSE context string for system prompt
      record_outcome(...)        → explicit success/failure signal
      signal_correction(...)     → Joe corrected ACE
      memory_summary()           → formatted status string
    """

    def __init__(self):
        self.muse = AceMemory(
            user_id  = "joe",
            base_dir = os.getenv("MUSE_MEMORY_DIR", "ace_state/muse_memory"),
        )
        self._last_domain = "tasks"

    # ── Core interface (backwards-compatible) ─────────────────────

    def get_memory(self, user_id: str, user_message: str = "") -> str:
        """
        Returns MUSE memory context string for injection into system prompt.
        Replaces the old Letta stub.
        """
        context = self.muse.before_reply(user_message)
        if context:
            return context
        # First-time fallback before any memory is built
        return (
            "Joe is an elite executive — Harvard/MIT caliber. "
            "Respond with precision. Be proactive. Anticipate the next step."
        )

    def save_memory(
        self,
        user_id: str,
        message: str,
        response: str,
        success: bool = True,
        domain: str = None,
    ):
        """
        Captures interaction to MUSE. Triggers reflect + consolidate.
        """
        self.muse.after_reply(
            user_message = message,
            response     = response,
            domain       = domain,
            success      = success,
        )

    # ── Extended interface ─────────────────────────────────────────

    def get_context(self, user_message: str) -> str:
        """Full MUSE context string — use this in system prompts."""
        return self.muse.before_reply(user_message)

    def record_outcome(self, message: str, response: str, success: bool, domain: str = None):
        """Explicit outcome signal — use when you know if a reply was good or bad."""
        self.muse.after_reply(
            user_message = message,
            response     = response,
            domain       = domain,
            success      = success,
        )

    def signal_positive(self):
        """Joe said something like 'perfect', 'exactly', 'great'."""
        self.muse.signal_positive()

    def signal_correction(self, correction: str):
        """Joe corrected ACE — learn from it."""
        self.muse.signal_correction(correction)

    def memory_summary(self) -> str:
        """Returns formatted memory status — use in /status command."""
        return self.muse.summary()

    def status_dict(self) -> dict:
        return self.muse.status()
