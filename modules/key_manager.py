"""
modules/key_manager.py
-----------------------
Manages a pool of Groq + Gemini API keys with round-robin rotation.

On a rate-limit / quota error the caller invokes rotate() to advance
to the next key automatically. Keys with missing values (empty env vars)
are silently excluded from the pool at startup.

Usage:
    from modules.key_manager import APIKeyManager
    km = APIKeyManager()
    key_info = km.current()   # {"provider": "groq", "key": "gsk_..."}
    km.rotate()               # advance to next key on rate-limit error
"""

import os


class APIKeyManager:
    """
    Round-robin API key pool supporting Groq and Gemini providers.

    Key pool order: GROQ_KEY_1 → GROQ_KEY_2 → GEMINI_KEY_1 → GEMINI_KEY_2
    Keys absent from the environment are skipped automatically.
    """

    def __init__(self):
        candidates = [
            {"provider": "groq",   "key": os.getenv("GROQ_API_KEY_1")},
            {"provider": "groq",   "key": os.getenv("GROQ_API_KEY_2")},
            {"provider": "gemini", "key": os.getenv("GEMINI_API_KEY_1")},
            {"provider": "gemini", "key": os.getenv("GEMINI_API_KEY_2")},
        ]
        # Remove entries where the key env var is unset or empty
        self.keys = [k for k in candidates if k["key"]]
        self.index = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def current(self) -> dict:
        """
        Return the current key info dict.

        Returns:
            {"provider": "groq"|"gemini", "key": "<api_key_string>"}

        Raises:
            ValueError: if no keys are configured in the environment.
        """
        if not self.keys:
            raise ValueError(
                "No API keys configured. Set at least one of: "
                "GROQ_API_KEY_1, GROQ_API_KEY_2, GEMINI_API_KEY_1, GEMINI_API_KEY_2."
            )
        return self.keys[self.index]

    def rotate(self) -> dict:
        """
        Advance to the next key in the pool (wraps around).

        Returns:
            The new current key info dict after rotation.
        """
        self.index = (self.index + 1) % len(self.keys)
        return self.current()

    # ------------------------------------------------------------------
    # Diagnostic helpers
    # ------------------------------------------------------------------

    def pool_size(self) -> int:
        """Return the number of valid keys in the pool."""
        return len(self.keys)

    def provider_summary(self) -> dict:
        """
        Return a count of keys per provider.

        Returns:
            e.g. {"groq": 2, "gemini": 1}
        """
        summary: dict = {}
        for k in self.keys:
            summary[k["provider"]] = summary.get(k["provider"], 0) + 1
        return summary
