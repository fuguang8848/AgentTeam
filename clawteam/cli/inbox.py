"""Inbox rendering module for ClawTeam CLI.

Provides rich console rendering for inbox messages with image support.
Uses iTerm2 inline images when available, with URL fallback for other terminals.

P30-P33: Multimodal inbox support.
"""

from __future__ import annotations

import base64
import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from clawteam.team.models import TeamMessage


# ANSI escape code for iTerm2 inline image
_ITERM2_INLINE = "\033]1337;File="
_ITERM2完毕 = "\a"


def _is_iterm2() -> bool:
    """Check if we're running in iTerm2."""
    return os.environ.get("TERM_PROGRAM") == "iTerm2"


def render_image_inline(
    data: bytes,
    mime_type: str = "image/png",
    width: int | None = None,
    height: int | None = None,
    preserve_aspect_ratio: bool = True,
) -> str:
    """Render an image using iTerm2 inline image protocol.

    Args:
        data: Raw image bytes.
        mime_type: MIME type of the image (e.g., "image/png").
        width: Display width in cells (optional).
        height: Display height in cells (optional).
        preserve_aspect_ratio: Whether to preserve aspect ratio.

    Returns:
        ANSI escape string for iTerm2, or empty string if not in iTerm2.
    """
    if not _is_iterm2():
        return ""

    # Base64-encode the image data
    b64 = base64.b64encode(data).decode("ascii")

    # Build the iTerm2 protocol string
    # Format: ESC]1337;File=name=<name>;size=<size>;width=<w>;height=<h>;preserveAspectRatio=<0|1>:<base64-data>BETA
    # We use inline data mode (no name=)
    parts = [f"size={len(data)}"]

    if width is not None:
        parts.append(f"width={width}")
    if height is not None:
        parts.append(f"height={height}")
    if preserve_aspect_ratio:
        parts.append("preserveAspectRatio=1")

    # Add MIME type
    parts.append(f"type={mime_type}")

    params = ";".join(parts)
    return f"{_ITERM2_INLINE}{params}:{b64}{_ITERM2完毕}"


def render_image_url_fallback(image_url: str, alt_text: str = "[image]") -> str:
    """Render image as a URL fallback for non-iTerm2 terminals.

    Args:
        image_url: URL of the image.
        alt_text: Alternative text to show when URL can't be displayed.

    Returns:
        Formatted string with the image URL.
    """
    # Truncate long URLs for display
    display_url = image_url
    if len(display_url) > 80:
        display_url = display_url[:77] + "..."

    # Try to extract a filename from the URL
    filename = image_url.split("/")[-1].split("?")[0]
    if filename and len(filename) < 60:
        return f"🖼️  [{filename}]({display_url})"
    return f"🖼️  {display_url}"


def render_message_image(msg: "TeamMessage") -> str:
    """Render image content from a TeamMessage.

    Supports three modes (in priority order):
    1. iTerm2 inline image (when image_data is available and terminal supports it)
    2. URL link fallback (when image_url is available)
    3. Nothing (when no image data is present)

    Args:
        msg: The TeamMessage to render images from.

    Returns:
        Formatted string with rendered image(s), or empty string.
    """
    output_parts = []

    # Handle inline image data (base64)
    if msg.image_data:
        try:
            # Decode base64 image data
            image_bytes = base64.b64decode(msg.image_data)
            inline = render_image_inline(
                data=image_bytes,
                mime_type=msg.image_mime_type or "image/png",
                width=msg.image_width,
                height=msg.image_height,
            )
            if inline:
                output_parts.append(inline)
            elif msg.image_url:
                # Fall back to URL if iTerm2 not available
                output_parts.append(render_image_url_fallback(msg.image_url))
        except Exception:
            # Decode error — fall back to URL if available
            if msg.image_url:
                output_parts.append(render_image_url_fallback(msg.image_url))

    # Handle image URL directly
    elif msg.image_url:
        output_parts.append(render_image_url_fallback(msg.image_url))

    # Handle attachments that are images (check mime_type)
    if msg.attachments:
        for att in msg.attachments:
            if att.mime_type.startswith("image/"):
                if att.url:
                    output_parts.append(render_image_url_fallback(att.url, alt_text=f"[{att.name}]"))
                else:
                    # No inline data for attachments (only URL support)
                    output_parts.append(f"🖼️  [{att.name}] ({att.size} bytes)")

    return "\n".join(output_parts)


def console_print_image(
    console,
    msg: "TeamMessage",
    border_style: str = "dim",
) -> None:
    """Print a TeamMessage's image content to the console using Rich.

    If no image is present, does nothing.

    Args:
        console: Rich Console instance.
        msg: The TeamMessage containing image data.
        border_style: Rich border style for the image panel.
    """
    from rich.panel import Panel
    from rich.text import Text

    image_output = render_message_image(msg)
    if not image_output:
        return

    # Create a panel with the image
    panel = Panel(
        Text.from_markup(image_output),
        title="📎 Attachment",
        border_style=border_style,
        expand=False,
    )
    console.print(panel)


# =============================================================================
# Exposed for use by clawteam.cli.commands
# =============================================================================


def patch_inbox_human_output():
    """Monkey-patch the inbox _human output functions to support images.

    This is a non-invasive way to add image support to the existing
    inbox commands in commands.py without rewriting them.

    Call this after the commands module is loaded to enhance the
    inbox rendering with image support.
    """
    import clawteam.cli.commands as cmds

    # The _human functions in inbox commands call console.print with formatted messages.
    # We expose render_message_image so commands.py can use it.
    cmds._render_inbox_image = render_message_image  # type: ignore[attr-defined]
    cmds._console_print_image = console_print_image  # type: ignore[attr-defined]
