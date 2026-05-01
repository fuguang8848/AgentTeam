"""Output reader manager for multi-provider coordination.

Routes to corresponding reader implementations by Provider ID, exposes unified interface.
When adding a new Provider: new XxxReader() → register_reader()

@author ClawTeam
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass

from clawteam.reader.types import BaseOutputReader, OutputEvent

logger = logging.getLogger(__name__)


@dataclass
class ReaderRegistration:
    """Reader registration information."""
    reader: BaseOutputReader
    provider_id: str


class OutputReaderManager:
    """Structured output reader manager.
    
    provider_id → reader instance
    session_id → provider_id
    """
    
    def __init__(self):
        """Initialize output reader manager."""
        self._readers: Dict[str, BaseOutputReader] = {}
        self._session_provider_map: Dict[str, str] = {}
        self._callbacks: List[callable] = []
    
    def register_reader(self, reader: BaseOutputReader) -> None:
        """Register reader for a provider.
        
        Args:
            reader: Reader instance.
        """
        self._readers[reader.provider_id] = reader
        logger.info("[OutputReaderManager] Registered reader: %s", reader.provider_id)
    
    def register_callback(self, callback: callable) -> None:
        """Register callback for output events.
        
        Args:
            callback: Callback function taking OutputEvent.
        """
        self._callbacks.append(callback)
    
    def start_watching(self, session_id: str, provider_id: str, work_dir: str) -> None:
        """Start watching session.
        
        If provider has no corresponding reader, silently skip (fall back to OutputParser).
        
        Args:
            session_id: Session ID.
            provider_id: Provider ID.
            work_dir: Working directory.
        """
        reader = self._readers.get(provider_id)
        if not reader:
            return
        
        self._session_provider_map[session_id] = provider_id
        reader.start_watching(session_id, work_dir)
        logger.debug("[OutputReaderManager] Started watching session %s for provider %s",
                     session_id, provider_id)
    
    def on_conversation_id_detected(self, session_id: str, conversation_id: str) -> None:
        """Call when CLI internal conversation ID is detected.
        
        Args:
            session_id: Session ID.
            conversation_id: Conversation ID.
        """
        provider_id = self._session_provider_map.get(session_id)
        if not provider_id:
            return
        
        reader = self._readers.get(provider_id)
        if reader:
            reader.bind_conversation_id(session_id, conversation_id)
            logger.debug("[OutputReaderManager] Bound conversation %s for session %s",
                         conversation_id, session_id)
    
    def has_active_reader(self, session_id: str) -> bool:
        """Check if session has active structured reader.
        
        Used by caller to decide whether to skip OutputParser's fuzzy parsing.
        
        Args:
            session_id: Session ID.
            
        Returns:
            True if active reader exists.
        """
        return session_id in self._session_provider_map
    
    def stop_watching(self, session_id: str) -> None:
        """Stop watching session.
        
        Args:
            session_id: Session ID.
        """
        provider_id = self._session_provider_map.get(session_id)
        if not provider_id:
            return
        
        reader = self._readers.get(provider_id)
        if reader:
            reader.stop_watching(session_id)
        
        del self._session_provider_map[session_id]
        logger.debug("[OutputReaderManager] Stopped watching session %s", session_id)
    
    def emit_event(self, event: OutputEvent) -> None:
        """Emit output event to all callbacks.
        
        Args:
            event: Output event.
        """
        for callback in self._callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("Error in output event callback: %s", e)
    
    def cleanup(self) -> None:
        """Clean up all resources."""
        for reader in self._readers.values():
            try:
                reader.cleanup()
            except Exception as e:
                logger.error("Error cleaning up reader %s: %s", reader.provider_id, e)
        
        self._readers.clear()
        self._session_provider_map.clear()
        self._callbacks.clear()
        logger.info("[OutputReaderManager] Cleaned up all resources")