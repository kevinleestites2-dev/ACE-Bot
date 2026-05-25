"""
muse_memory.py — MUSE Memory for ACE Bot
══════════════════════════════════════════
Self-evolving memory layer for ACE — Joe's executive assistant.

Based on the MUSE (Hierarchical Memory Module) architecture:
  Phase 1 — CAPTURE  : Every interaction stored as a trajectory entry
  Phase 2 — REFLECT  : Patterns distilled into lessons (success/failure)
  Phase 3 — CONSOLIDATE: Long-term skill memory, preferences, habits

Three memory tiers:
  1. ExperienceStore  — raw interaction log (what happened)
  2. MemSkill         — distilled lessons per domain (what worked)
  3. MemRL            — preference/habit weights (what Joe likes)

ACE-specific domains:
  - schedule     : calendar, meetings, timing preferences
  - comms        : how Joe communicates, tone, contacts
  - research     : what Joe asks about, knowledge depth expected
  - tasks        : action items, follow-ups, priorities
  - personal     : Joe's life context (family, crew, KJLK, Oklahoma bid)

Usage:
    from ace_bot.muse_memory import AceMemory

    mem = AceMemory(user_id="joe")
    context = mem.before_reply(user_message, domain)
    # ... generate response ...
    mem.after_reply(user_message, response, domain, success=True)
"""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


# ══════════════════════════════════════════════════════════════════
# EXPERIENCE STORE — raw interaction log
# ══════════════════════════════════════════════════════════════════

class ExperienceStore:
    """
    Append-only log of every interaction.
    Persisted to disk. Survives restarts.
    """

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> Dict:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"entries": [], "total": 0}

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def append(self, entry: Dict):
        with self._lock:
            entry["ts"] = datetime.utcnow().isoformat()
            self._data["entries"].append(entry)
            self._data["total"] += 1
            # Cap at 500 raw entries — keep recent history
            if len(self._data["entries"]) > 500:
                self._data["entries"] = self._data["entries"][-500:]
            self._save()

    def recent(self, n: int = 20, domain: Optional[str] = None) -> List[Dict]:
        entries = self._data["entries"]
        if domain:
            entries = [e for e in entries if e.get("domain") == domain]
        return entries[-n:]

    def retrieve(self, domain: str, pattern: str = "", top_k: int = 5) -> List[Dict]:
        entries = [e for e in self._data["entries"] if e.get("domain") == domain]
        if pattern:
            entries = [e for e in entries if pattern.lower() in json.dumps(e).lower()]
        return entries[-top_k:]

    @property
    def total(self) -> int:
        return self._data.get("total", 0)


# ══════════════════════════════════════════════════════════════════
# MEM SKILL — distilled lessons per domain
# ══════════════════════════════════════════════════════════════════

class MemSkill:
    """
    Distilled lessons from raw experience.
    
    After every N interactions, patterns are extracted and written
    as structured lessons: what worked, what failed, what Joe prefers.
    """

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> Dict:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"lessons": {}, "success_counts": {}, "failure_counts": {}}

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def record_outcome(self, domain: str, success: bool, lesson: str):
        with self._lock:
            if domain not in self._data["lessons"]:
                self._data["lessons"][domain] = []
                self._data["success_counts"][domain] = 0
                self._data["failure_counts"][domain] = 0

            if success:
                self._data["success_counts"][domain] += 1
            else:
                self._data["failure_counts"][domain] += 1

            self._data["lessons"][domain].append({
                "lesson":  lesson,
                "success": success,
                "ts":      datetime.utcnow().isoformat(),
            })
            # Keep last 50 lessons per domain
            self._data["lessons"][domain] = self._data["lessons"][domain][-50:]
            self._save()

    def get_lessons(self, domain: str, n: int = 5) -> List[Dict]:
        return self._data["lessons"].get(domain, [])[-n:]

    def success_rate(self, domain: str) -> float:
        s = self._data["success_counts"].get(domain, 0)
        f = self._data["failure_counts"].get(domain, 0)
        total = s + f
        return round(s / total, 2) if total else 0.0

    def domains_with_memory(self) -> List[str]:
        return list(self._data["lessons"].keys())


# ══════════════════════════════════════════════════════════════════
# MEM RL — preference & habit weights
# ══════════════════════════════════════════════════════════════════

class MemRL:
    """
    Joe's learned preferences and habits.
    
    Weights evolve based on feedback signals:
    - Positive: Joe approved, acted on suggestion, said thanks
    - Negative: Joe corrected, ignored, said wrong
    
    These weights bias future responses toward what Joe actually wants.
    """

    DEFAULTS = {
        "brevity":        0.5,   # 0=verbose, 1=brief
        "formality":      0.7,   # 0=casual, 1=formal (Joe is exec-level)
        "proactivity":    0.8,   # 0=reactive, 1=proactive
        "technical_depth": 0.9,  # 0=simple, 1=deep (Joe is MIT/Harvard tier)
        "tone_warmth":    0.6,   # 0=cold/professional, 1=warm/personal
    }

    def __init__(self, path: str):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> Dict:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"weights": dict(self.DEFAULTS), "adjustments": []}

    def _save(self):
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def adjust(self, preference: str, direction: float, reason: str = ""):
        """Nudge a preference weight. direction: +0.05 or -0.05"""
        with self._lock:
            current = self._data["weights"].get(preference, 0.5)
            updated = max(0.0, min(1.0, current + direction))
            self._data["weights"][preference] = updated
            self._data["adjustments"].append({
                "preference": preference,
                "from":       current,
                "to":         updated,
                "reason":     reason,
                "ts":         datetime.utcnow().isoformat(),
            })
            self._data["adjustments"] = self._data["adjustments"][-100:]
            self._save()

    def weights(self) -> Dict[str, float]:
        return dict(self._data["weights"])

    def style_hint(self) -> str:
        """Returns a style instruction string based on current weights."""
        w = self._data["weights"]
        hints = []

        if w.get("brevity", 0.5) > 0.6:
            hints.append("Be concise — Joe prefers short, direct answers.")
        else:
            hints.append("Joe appreciates thorough explanations.")

        if w.get("formality", 0.5) > 0.6:
            hints.append("Maintain a professional, executive tone.")
        else:
            hints.append("Keep the tone conversational.")

        if w.get("proactivity", 0.5) > 0.6:
            hints.append("Anticipate next steps. Don't wait to be asked.")

        if w.get("technical_depth", 0.5) > 0.7:
            hints.append("Joe is highly technical — don't oversimplify.")

        return " ".join(hints)


# ══════════════════════════════════════════════════════════════════
# ACE MEMORY — the unified interface
# ══════════════════════════════════════════════════════════════════

class AceMemory:
    """
    Self-evolving memory for ACE Bot.
    
    Three phases per interaction:
      before_reply()  → injects memory context into system prompt
      after_reply()   → captures outcome, reflects, consolidates
      
    Three storage tiers:
      ExperienceStore → raw log of every interaction
      MemSkill        → distilled lessons per domain
      MemRL           → Joe's preference weights
    
    Domain auto-detection:
      Pass domain=None and AceMemory will infer from message content.
    """

    DOMAINS = ["schedule", "comms", "research", "tasks", "personal"]

    def __init__(self, user_id: str = "joe", base_dir: str = "ace_state/muse_memory"):
        self.user_id   = user_id
        self.base_dir  = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.store = ExperienceStore(str(self.base_dir / "experiences.json"))
        self.skill = MemSkill(str(self.base_dir / "skills.json"))
        self.rl    = MemRL(str(self.base_dir / "preferences.json"))

        # Reflection counter — every 5 interactions, do a full reflection pass
        self._interaction_count = self.store.total

    def detect_domain(self, message: str) -> str:
        """Infer domain from message content."""
        msg = message.lower()
        if any(w in msg for w in ["meeting", "calendar", "schedule", "appointment", "time", "today", "tomorrow"]):
            return "schedule"
        if any(w in msg for w in ["email", "call", "text", "message", "contact", "healy", "joe"]):
            return "comms"
        if any(w in msg for w in ["research", "find", "look up", "what is", "how does", "explain"]):
            return "research"
        if any(w in msg for w in ["task", "todo", "remind", "follow up", "action", "do this"]):
            return "tasks"
        if any(w in msg for w in ["kjlk", "oklahoma", "bid", "farm", "pantheon", "apartment", "crew"]):
            return "personal"
        return "tasks"  # default

    def before_reply(self, user_message: str, domain: Optional[str] = None) -> str:
        """
        Build memory context string to inject into ACE's system prompt.
        
        Returns a compact string summarizing:
          - Recent interactions in this domain
          - Relevant lessons from MemSkill
          - Joe's current style preferences (MemRL)
        """
        if not domain:
            domain = self.detect_domain(user_message)

        context_parts = []

        # Style preferences
        style = self.rl.style_hint()
        if style:
            context_parts.append(f"[ACE Style] {style}")

        # Recent interactions in domain
        recent = self.store.recent(n=5, domain=domain)
        if recent:
            context_parts.append(f"[Recent {domain} context]")
            for entry in recent[-3:]:
                msg_snippet = entry.get("message", "")[:80]
                resp_snippet = entry.get("response", "")[:80]
                context_parts.append(f"  User: {msg_snippet}")
                context_parts.append(f"  ACE:  {resp_snippet}")

        # Lessons from MemSkill
        lessons = self.skill.get_lessons(domain, n=3)
        success_lessons = [l for l in lessons if l.get("success")]
        if success_lessons:
            context_parts.append(f"[What worked in {domain}]")
            for l in success_lessons[-2:]:
                context_parts.append(f"  ✅ {l['lesson'][:100]}")

        fail_lessons = [l for l in lessons if not l.get("success")]
        if fail_lessons:
            context_parts.append(f"[What to avoid in {domain}]")
            for l in fail_lessons[-1:]:
                context_parts.append(f"  ❌ {l['lesson'][:100]}")

        return "\n".join(context_parts) if context_parts else ""

    def after_reply(
        self,
        user_message: str,
        response: str,
        domain: Optional[str] = None,
        success: bool = True,
        feedback: Optional[str] = None,
    ):
        """
        Capture interaction outcome. Reflect. Consolidate.
        
        Called after every ACE response.
        success=True  → Joe got a good answer, acted on it
        success=False → Joe corrected ACE or ignored response
        feedback      → optional raw feedback signal
        """
        if not domain:
            domain = self.detect_domain(user_message)

        # PHASE 1 — CAPTURE
        entry = {
            "domain":   domain,
            "message":  user_message[:300],
            "response": response[:300],
            "success":  success,
            "feedback": feedback or "",
            "user_id":  self.user_id,
        }
        self.store.append(entry)
        self._interaction_count += 1

        # PHASE 2 — REFLECT (every 5 interactions or on failure)
        if self._interaction_count % 5 == 0 or not success:
            self._reflect(domain, user_message, response, success)

        # PHASE 3 — CONSOLIDATE preferences (RL update)
        self._consolidate_rl(domain, success, user_message, response)

    def _reflect(self, domain: str, message: str, response: str, success: bool):
        """Distill a lesson from the recent interaction."""
        if success:
            lesson = (
                f"When asked about '{message[:60]}', "
                f"responding with '{response[:60]}' was effective."
            )
        else:
            lesson = (
                f"When asked about '{message[:60]}', "
                f"the response '{response[:60]}' did not satisfy Joe — needs improvement."
            )
        self.skill.record_outcome(domain, success, lesson)

    def _consolidate_rl(self, domain: str, success: bool, message: str, response: str):
        """Nudge preference weights based on interaction outcome."""
        direction = 0.03 if success else -0.03

        # Brief messages → nudge brevity preference
        if len(response) < 200 and success:
            self.rl.adjust("brevity", 0.02, f"Short response worked in {domain}")
        elif len(response) > 800 and not success:
            self.rl.adjust("brevity", 0.03, f"Long response failed in {domain} — Joe wanted shorter")

        # Technical content → nudge depth preference
        tech_words = ["api", "deploy", "code", "script", "system", "protocol", "architecture"]
        if any(w in message.lower() for w in tech_words) and success:
            self.rl.adjust("technical_depth", 0.02, f"Technical depth worked in {domain}")

    def signal_positive(self, domain: Optional[str] = None):
        """Call when Joe explicitly approves (e.g., 'perfect', 'exactly right')."""
        d = domain or "tasks"
        self.rl.adjust("proactivity", 0.03, f"Positive signal in {d}")

    def signal_correction(self, correction: str, domain: Optional[str] = None):
        """Call when Joe corrects ACE."""
        d = domain or "tasks"
        self.skill.record_outcome(d, False, f"Joe corrected: {correction[:120]}")
        self.rl.adjust("brevity", -0.02, f"Correction received in {d}")

    def status(self) -> Dict:
        return {
            "total_interactions": self.store.total,
            "skill_domains":      self.skill.domains_with_memory(),
            "preferences":        self.rl.weights(),
            "success_rates":      {
                d: self.skill.success_rate(d)
                for d in self.skill.domains_with_memory()
            },
        }

    def summary(self) -> str:
        """Human-readable memory summary for /status command."""
        s = self.status()
        lines = [
            f"🧠 ACE Memory — {s['total_interactions']} interactions logged",
            f"📚 Domains learned: {', '.join(s['skill_domains']) or 'none yet'}",
        ]
        if s["success_rates"]:
            lines.append("✅ Success rates:")
            for d, rate in s["success_rates"].items():
                lines.append(f"   {d}: {int(rate*100)}%")
        prefs = s["preferences"]
        lines.append(
            f"🎯 Style: "
            f"{'Brief' if prefs.get('brevity',0.5)>0.6 else 'Detailed'} | "
            f"{'Formal' if prefs.get('formality',0.5)>0.6 else 'Casual'} | "
            f"{'Proactive' if prefs.get('proactivity',0.5)>0.6 else 'Reactive'}"
        )
        return "\n".join(lines)
