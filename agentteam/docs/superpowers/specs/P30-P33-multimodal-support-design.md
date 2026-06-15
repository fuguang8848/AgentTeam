# AgentTeam Multimodal Support - P30-P33 Architecture Design

## Overview

This document defines the architecture for AgentTeam Multimodal Support (Phases 30-33), enabling rich media and real-time streaming capabilities in inter-agent communication.

## Motivation

Currently, AgentTeam supports only plain text messages (`TeamMessage.content`). Modern AI agents can generate and consume multiple modalities (images, audio, video, files). This enhancement enables:

1. **Image Support** - Agents can share generated images, screenshots, charts
2. **File Attachments** - Agents can share documents, code files, data
3. **Rich Media** - Audio/video playback in board
4. **Streaming** - Real-time progress and activity streaming

---

## Phase 30: Image Support

### Models

```python
# New fields in TeamMessage
image_url: str | None = None          # Remote image URL
image_data: str | None = None         # Base64 encoded image (small images only)
image_mime_type: str | None = "image/png"
image_width: int | None = None
image_height: int | None = None

# New fields in Notification
image_url: str | None = None
```

### Implementation

1. **`agentteam/team/models.py`**: Add image fields to `TeamMessage` and `Notification`
2. **`agentteam/notification/types.py`**: Add `image_url` to `Notification`
3. **`agentteam/cli/inbox.py`**: Render images in CLI using iTerm2 inline images or fallback to URL display
4. **`agentteam/board/web/`**: Display images in web board notification cards

### CLI Rendering

```bash
# Text fallback (non-iTerm2 terminals)
📷 [image: screenshot.png] https://example.com/image.png

# iTerm2 compatible (direct inline)
\033]1337;File=name=screenshot.png;size=12345;inline=1:base64data...\a
```

---

## Phase 31: File Attachment Support

### Models

```python
class FileAttachment(BaseModel):
    """A file attachment in a message."""
    name: str                              # Original filename
    size: int                              # Size in bytes
    mime_type: str = "application/octet-stream"
    url: str | None = None                 # Remote URL (if stored externally)
    path: str | None = None                # Local path (if in data dir)
    hash_sha256: str | None = None        # For integrity verification
    thumbnail_url: str | None = None      # Thumbnail for preview

class TeamMessage(BaseModel):
    # ... existing fields ...
    attachments: list[FileAttachment] = []  # Files attached to message
```

### Implementation

1. **`agentteam/team/models.py`**: Add `FileAttachment` class and `attachments` to `TeamMessage`
2. **`agentteam/team/mailbox.py`**: Handle attachment storage (copy to data dir or reference URL)
3. **`agentteam/cli/inbox.py`**: Display attachment list with icons by MIME type
4. **`agentteam/board/web/`**: File list component with download buttons

### File Type Icons

| MIME Type | Icon | CLI |
|-----------|------|-----|
| image/* | 🖼️ | 📷 |
| audio/* | 🎵 | 🎙️ |
| video/* | 🎬 | 📹 |
| application/pdf | 📄 | 📄 |
| text/* | 📝 | 📝 |
| application/zip | 📦 | 📦 |
| */* | 📎 | 📎 |

---

## Phase 32: Rich Notification & Metadata

### Enhanced Notification

```python
class Notification:
    # ... existing fields ...
    image_url: str | None = None
    attachments: list[FileAttachment] = []
    metadata: dict[str, Any] = {}         # Arbitrary structured data
    action_url: str | None = None          # CTA button URL
    progress: float | None = None          # 0.0-1.0 progress indicator
```

### Notification Types

```python
class NotificationType(str, Enum):
    # ... existing ...
    PROGRESS = "progress"                  # Progress update
    MEDIA = "media"                        # Audio/video notification
    FILE = "file"                          # File shared notification
    IMAGE = "image"                        # Image shared notification
```

### Implementation

1. **`agentteam/notification/types.py`**: Extend `Notification` and `NotificationType`
2. **`agentteam/notification/manager.py`**: Handle rich notification rendering
3. **`agentteam/board/web/`**: Rich notification cards with progress bars, images

---

## Phase 33: Real-time Streaming & Activity Feed

### Streaming Message Type

```python
class MessageType(str, Enum):
    # ... existing ...
    stream_start = "stream_start"          # Start of streaming output
    stream_chunk = "stream_chunk"          # Chunk of streaming output
    stream_end = "stream_end"              # End of streaming output
    activity = "activity"                  # Agent activity update

class TeamMessage(BaseModel):
    # ... existing fields ...
    stream_id: str | None = None           # ID for streaming sequence
    chunk_index: int | None = None         # Index in stream
    total_chunks: int | None = None        # Total chunks expected
    is_final: bool = False                 # Final chunk flag
    progress: float | None = None          # 0.0-1.0 progress
```

### Activity Feed

```python
class AgentActivity(BaseModel):
    """Real-time agent activity update."""
    agent_id: str
    agent_name: str
    activity_type: str                      # "thinking", "coding", "waiting", etc.
    message: str | None                     # Activity description
    progress: float | None = None           # Optional progress
    timestamp: str = Field(default_factory=_now_iso)
```

### Implementation

1. **`agentteam/team/models.py`**: Add streaming message types and `AgentActivity`
2. **`agentteam/team/mailbox.py`**: Support streaming message sequences
3. **`agentteam/board/web/`**: Real-time activity feed with SSE/WebSocket
4. **`agentteam/cli/board.py`**: Live activity display in CLI

### Web Board Streaming

```
┌─ Activity Feed ──────────────────────────────────────┐
│ 🟢 arch-p27  thinking  "Analyzing task requirements" │
│ 🟡 arch-p28  coding    "Implementing feature X" 45% │
│ 🔴 arch-p29  waiting   "Blocked by task #123"       │
└──────────────────────────────────────────────────────┘
```

---

## Backward Compatibility

All changes are **backward compatible**:
- Existing text-only messages continue to work unchanged
- New fields have default values or are Optional
- Old clients can ignore unknown fields

---

## File Structure

```
agentteam/
├── team/
│   └── models.py              # Add FileAttachment, image fields, streaming types
├── notification/
│   ├── types.py              # Add image_url, attachments, progress to Notification
│   └── manager.py            # Rich notification handling
├── board/
│   └── web/
│       ├── components/        # Rich notification cards
│       └── streaming.py       # SSE/WebSocket streaming
└── cli/
    └── inbox.py               # Image and attachment rendering
```

---

## Testing Strategy

| Phase | Tests | Coverage |
|-------|-------|----------|
| P30 | `test_multimodal_image.py` | 15+ tests |
| P31 | `test_multimodal_files.py` | 15+ tests |
| P32 | `test_multimodal_notification.py` | 12+ tests |
| P33 | `test_multimodal_streaming.py` | 18+ tests |

---

## Dependencies

- No new required dependencies
- Optional: `python-magic` for MIME type detection
- Web board already supports SSE (no new deps)

---

## Migration Guide

```python
# Old message (still works)
TeamMessage(from_agent="alice", content="Hello")

# New image message
TeamMessage(from_agent="alice", content="Here's the chart", image_url="https://...")

# New file attachment
TeamMessage(
    from_agent="alice",
    content="Code file attached",
    attachments=[FileAttachment(name="main.py", size=1234, mime_type="text/plain")]
)

# Streaming message
TeamMessage(
    from_agent="alice",
    type=MessageType.stream_chunk,
    stream_id="abc123",
    chunk_index=5,
    content="part of streaming output"
)
```

---

_Last updated: 2026-05-03_
_Architect: arch-p30-33_
