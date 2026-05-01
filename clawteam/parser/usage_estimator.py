"""Token usage estimator for AI provider outputs.

Estimates token consumption based on character count and tracks usage per session.
Inspired by SpectrAI's UsageEstimator.ts.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from clawteam.parser.types import UsageSummary


def _get_today() -> str:
    """Get today's date in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


@dataclass
class SessionUsage:
    """Usage tracking for a single session."""
    
    tokens: int = 0
    start_time: float = 0.0
    minutes: int = 0
    last_update: float = 0.0


class UsageEstimator:
    """Estimates and tracks token usage across sessions."""
    
    # Token estimation ratios
    # ASCII: ~4 chars per token
    # Non-ASCII (CJK): ~2 chars per token
    ASCII_RATIO = 4
    NON_ASCII_RATIO = 2
    
    def __init__(self, persist_dir: Path | None = None):
        self._session_usage: dict[str, SessionUsage] = {}
        self._lock = threading.Lock()
        self._persist_dir = persist_dir
        self._flush_interval = 60.0  # seconds
        self._flush_thread: threading.Thread | None = None
        self._running = False
    
    def start_persistence(self) -> None:
        """Start background thread for periodic persistence."""
        if self._persist_dir is None:
            return
        self._running = True
        self._flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._flush_thread.start()
    
    def stop_persistence(self) -> None:
        """Stop background persistence thread."""
        self._running = False
        if self._flush_thread:
            self._flush_thread.join(timeout=5.0)
        self._flush_to_disk()
    
    def _flush_loop(self) -> None:
        """Background loop for periodic persistence."""
        while self._running:
            time.sleep(self._flush_interval)
            self._flush_to_disk()
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.
        
        Uses character-based estimation:
        - ASCII characters: ~4 chars = 1 token
        - Non-ASCII characters: ~2 chars = 1 token
        """
        ascii_chars = 0
        non_ascii_chars = 0
        
        for char in text:
            if ord(char) <= 127:
                ascii_chars += 1
            else:
                non_ascii_chars += 1
        
        return (ascii_chars // self.ASCII_RATIO) + (non_ascii_chars // self.NON_ASCII_RATIO)
    
    def accumulate_usage(self, session_id: str, text: str) -> int:
        """Accumulate token usage for a session.
        
        Returns the estimated tokens added.
        """
        tokens = self.estimate_tokens(text)
        
        with self._lock:
            if session_id not in self._session_usage:
                self._session_usage[session_id] = SessionUsage(
                    start_time=time.time(),
                    last_update=time.time(),
                )
            
            usage = self._session_usage[session_id]
            usage.tokens += tokens
            usage.last_update = time.time()
        
        return tokens
    
    def mark_session_ended(self, session_id: str) -> UsageSummary:
        """Mark session as ended and calculate final usage."""
        with self._lock:
            usage = self._session_usage.get(session_id)
            if usage is None:
                return UsageSummary()
            
            # Calculate minutes
            elapsed = time.time() - usage.start_time
            usage.minutes = int(elapsed / 60)
            
            # Persist to disk if enabled
            if self._persist_dir:
                self._persist_session(session_id, usage)
            
            # Return summary for this session
            summary = UsageSummary(
                total_tokens=usage.tokens,
                total_minutes=usage.minutes,
                active_sessions=0,
                session_breakdown={session_id: usage.tokens},
            )
        
        return summary
    
    def get_session_usage(self, session_id: str) -> int:
        """Get token usage for a specific session."""
        with self._lock:
            usage = self._session_usage.get(session_id)
            return usage.tokens if usage else 0
    
    def get_summary(self) -> UsageSummary:
        """Get overall usage summary."""
        with self._lock:
            total_tokens = 0
            total_minutes = 0
            active_sessions = 0
            session_breakdown: dict[str, int] = {}
            
            now = time.time()
            
            for session_id, usage in self._session_usage.items():
                total_tokens += usage.tokens
                session_breakdown[session_id] = usage.tokens
                
                # Count active sessions (updated within last 5 minutes)
                if now - usage.last_update < 300:
                    active_sessions += 1
                
                # Calculate minutes
                elapsed = now - usage.start_time
                total_minutes += int(elapsed / 60)
        
        return UsageSummary(
            total_tokens=total_tokens,
            total_minutes=total_minutes,
            today_tokens=total_tokens,  # In-memory only tracks current session
            today_minutes=total_minutes,
            active_sessions=active_sessions,
            session_breakdown=session_breakdown,
        )
    
    def reset_session_usage(self, session_id: str) -> None:
        """Reset usage for a specific session."""
        with self._lock:
            self._session_usage.pop(session_id, None)
    
    def reset_all(self) -> None:
        """Reset all usage tracking."""
        with self._lock:
            self._session_usage.clear()
    
    def _persist_session(self, session_id: str, usage: SessionUsage) -> None:
        """Persist session usage to disk."""
        if self._persist_dir is None:
            return
        
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        
        today = _get_today()
        record = {
            "session_id": session_id,
            "date": today,
            "tokens": usage.tokens,
            "minutes": usage.minutes,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Append to daily log file
        log_file = self._persist_dir / f"usage-{today}.jsonl"
        with log_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False))
            f.write("\n")
    
    def _flush_to_disk(self) -> None:
        """Flush all session usage to disk."""
        if self._persist_dir is None:
            return
        
        with self._lock:
            for session_id, usage in self._session_usage.items():
                if usage.tokens > 0:
                    self._persist_session(session_id, usage)
    
    def get_usage_history(self, days: int = 7) -> list[dict[str, Any]]:
        """Get usage history from persisted logs."""
        if self._persist_dir is None:
            return []
        
        history = []
        
        for i in range(days):
            date = datetime.now(timezone.utc) - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            log_file = self._persist_dir / f"usage-{date_str}.jsonl"
            
            if log_file.exists():
                with log_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                record = json.loads(line)
                                history.append(record)
                            except json.JSONDecodeError:
                                pass
        
        return history
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_persistence()


# Import timedelta for get_usage_history
from datetime import timedelta
from dataclasses import field