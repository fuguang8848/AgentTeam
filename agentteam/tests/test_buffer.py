"""Tests for terminal buffer."""

import pytest
from agentteam.spawn.terminal_buffer import HeadlessTerminalBuffer, ScreenUpdateInfo


@pytest.fixture
def buffer():
    """Create a fresh terminal buffer."""
    return HeadlessTerminalBuffer(cols=80, rows=24)


@pytest.fixture
def buffer_with_callback():
    """Create a buffer with screen update callback."""
    updates = []
    
    def callback(info: ScreenUpdateInfo):
        updates.append(info)
    
    buffer = HeadlessTerminalBuffer(
        cols=80, 
        rows=24,
        on_screen_update=callback,
        callback_tail_lines=10
    )
    return buffer, updates


def test_initialization(buffer):
    """Test buffer initialization."""
    assert buffer._cols == 80
    assert buffer._rows == 24
    assert buffer._scrollback == 5000
    assert not buffer._disposed
    assert buffer._total_appended == 0


def test_write_simple_text(buffer):
    """Test writing simple text."""
    buffer.write("Hello, world!")
    
    assert buffer._total_appended == 13
    text = buffer.get_text()
    assert "Hello, world!" in text


def test_append_method(buffer):
    """Test append method (same as write)."""
    buffer.append("Test append")
    
    assert buffer._total_appended == 11
    text = buffer.get_text()
    assert "Test append" in text


def test_write_with_callback(buffer_with_callback):
    """Test write with callback."""
    buffer, updates = buffer_with_callback
    
    buffer.write("Hello")
    
    assert len(updates) == 1
    info = updates[0]
    assert isinstance(info, ScreenUpdateInfo)
    assert info.total_appended == 5
    assert len(info.last_lines) <= 10


def test_write_multiple_with_callback(buffer_with_callback):
    """Test multiple writes with callback."""
    buffer, updates = buffer_with_callback
    
    buffer.write("First line\n")
    buffer.write("Second line\n")
    
    assert len(updates) == 2
    assert updates[0].total_appended == 11
    assert updates[1].total_appended == 23


def test_get_text(buffer):
    """Test get_text method."""
    buffer.write("Line 1\nLine 2\nLine 3")
    
    text = buffer.get_text()
    assert "Line 1" in text
    assert "Line 2" in text
    assert "Line 3" in text


def test_get_last_lines(buffer):
    """Test get_last_lines method."""
    buffer.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
    
    last_2 = buffer.get_last_lines(2)
    assert len(last_2) == 2
    assert "Line 4" in last_2[0] or "Line 4" in last_2[1]
    assert "Line 5" in last_2[0] or "Line 5" in last_2[1]


def test_get_last_lines_more_than_available(buffer):
    """Test get_last_lines with more lines than available."""
    buffer.write("Line 1\nLine 2")
    
    last_10 = buffer.get_last_lines(10)
    assert len(last_10) <= 2  # Should return only available lines


def test_get_last_lines_empty(buffer):
    """Test get_last_lines on empty buffer."""
    lines = buffer.get_last_lines(10)
    assert len(lines) == 0


def test_cursor_position(buffer):
    """Test cursor_position property."""
    buffer.write("Hello")
    
    row, col = buffer.cursor_position
    assert isinstance(row, int)
    assert isinstance(col, int)
    assert row >= 0
    assert col >= 0


def test_total_appended_property(buffer):
    """Test total_appended property."""
    assert buffer.total_appended == 0
    
    buffer.write("Test")
    assert buffer.total_appended == 4
    
    buffer.write("More")
    assert buffer.total_appended == 8


def test_set_on_screen_update(buffer):
    """Test set_on_screen_update method."""
    updates = []
    
    def callback(info: ScreenUpdateInfo):
        updates.append(info)
    
    buffer.set_on_screen_update(callback)
    
    buffer.write("Test")
    assert len(updates) == 1
    assert updates[0].total_appended == 4


def test_dispose(buffer):
    """Test dispose method."""
    buffer.write("Some data")
    
    assert not buffer._disposed
    buffer.dispose()
    
    assert buffer._disposed
    assert buffer._on_screen_update is None
    
    # Write after dispose should do nothing
    buffer.write("Ignored")
    assert buffer._total_appended == 9  # Still original 9 bytes


def test_resize(buffer):
    """Test resize method."""
    assert buffer._cols == 80
    assert buffer._rows == 24
    
    buffer.resize(cols=100, rows=30)
    
    assert buffer._cols == 100
    assert buffer._rows == 30
    assert buffer._scroll_bottom == 29  # rows - 1


def test_resize_after_dispose(buffer):
    """Test resize after dispose."""
    buffer.dispose()
    
    # Should not raise error
    buffer.resize(cols=100, rows=30)
    assert buffer._cols == 80  # Should not change


def test_get_buffer_info(buffer):
    """Test get_buffer_info method."""
    buffer.write("Hello")
    
    info = buffer.get_buffer_info()
    
    assert info['cols'] == 80
    assert info['rows'] == 24
    assert info['scrollback'] == 5000
    assert info['cursor_row'] >= 0
    assert info['cursor_col'] >= 0
    assert info['total_appended'] == 5
    assert info['disposed'] is False


def test_ansi_escape_sequences():
    """Test handling of ANSI escape sequences."""
    buffer = HeadlessTerminalBuffer(cols=80, rows=24)
    
    # Test cursor movement sequences (simplified)
    buffer.write("Start\x1b[HMiddle\x1b[2JEnd")
    
    # Should not crash
    text = buffer.get_text()
    assert isinstance(text, str)


def test_write_empty_string(buffer):
    """Test writing empty string."""
    buffer.write("")
    
    assert buffer._total_appended == 0
    text = buffer.get_text()
    assert text == ""


def test_multiple_lines_scroll(buffer):
    """Test writing more lines than buffer rows."""
    buffer = HeadlessTerminalBuffer(cols=80, rows=5)  # Small buffer
    
    # Write more lines than buffer can hold
    for i in range(10):
        buffer.write(f"Line {i}\n")
    
    text = buffer.get_text()
    lines = text.split('\n')
    
    # Should have some lines (implementation dependent)
    assert len(lines) > 0


def test_screen_update_info_dataclass():
    """Test ScreenUpdateInfo dataclass."""
    info = ScreenUpdateInfo(
        last_lines=["Line 1", "Line 2"],
        total_appended=100
    )
    
    assert info.last_lines == ["Line 1", "Line 2"]
    assert info.total_appended == 100