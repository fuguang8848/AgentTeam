"""
HeadlessTerminalBuffer - 虚拟终端缓冲区

参考 SpectrAI/src/main/agent/HeadlessTerminalBuffer.ts 实现
使用纯 Python 实现终端模拟器（不依赖 @xterm/headless）

核心功能：
- 正确处理 ANSI 转义序列（光标移动、行清除、覆写、滚动）
- getText() 返回与屏幕实际显示一致的内容
- onScreenUpdate 回调：write 完成后通知外部
- getLastLines(n) 获取最后 N 行
- totalAppended 累计字节数

@author ClawTeam
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


# 默认配置
DEFAULT_COLS = 120
DEFAULT_ROWS = 80
DEFAULT_SCROLLBACK = 5000


@dataclass
class ScreenUpdateInfo:
    """屏幕更新回调参数"""
    last_lines: List[str]  # 屏幕最后 N 行文本
    total_appended: int    # 累计写入的原始字节数


class ANSICommand(Enum):
    """ANSI 转义序列命令类型"""
    CURSOR_UP = 'A'
    CURSOR_DOWN = 'B'
    CURSOR_FORWARD = 'C'
    CURSOR_BACK = 'D'
    CURSOR_POSITION = 'H'
    ERASE_DISPLAY = 'J'
    ERASE_LINE = 'K'
    SET_SCROLL_REGION = 'r'
    RESET = 'c'
    SAVE_CURSOR = 's'
    RESTORE_CURSOR = 'u'
    # SGR (Select Graphic Rendition) - 颜色/样式
    SGR = 'm'


class HeadlessTerminalBuffer:
    """
    虚拟终端缓冲区
    
    使用纯 Python 实现终端模拟器，正确处理 ANSI 转义序列。
    使 getText() 返回的内容与屏幕上实际显示一致。
    
    使用示例：
        buffer = HeadlessTerminalBuffer(cols=120, rows=80)
        
        # 设置更新回调
        buffer.set_on_screen_update(lambda info: print(info.last_lines))
        
        # 写入数据（含 ANSI 转义序列）
        buffer.write("Hello\\x1b[2J\\x1b[HWorld")
        
        # 获取屏幕内容
        text = buffer.get_text()
        lines = buffer.get_last_lines(10)
    """
    
    def __init__(
        self,
        cols: int = DEFAULT_COLS,
        rows: int = DEFAULT_ROWS,
        scrollback: int = DEFAULT_SCROLLBACK,
        on_screen_update: Optional[Callable[[ScreenUpdateInfo], None]] = None,
        callback_tail_lines: int = 30
    ):
        """
        初始化虚拟终端
        
        Args:
            cols: 列宽
            rows: 可视行数
            scrollback: 回滚缓冲区行数
            on_screen_update: 屏幕更新回调
            callback_tail_lines: 回调中返回最后多少行
        """
        self._cols = cols
        self._rows = rows
        self._scrollback = scrollback
        self._on_screen_update = on_screen_update
        self._callback_tail_lines = callback_tail_lines
        
        # 终端缓冲区：二维数组，每个元素是一个字符
        # 主缓冲区（可视区域 + 回滚缓冲区）
        self._buffer: List[List[str]] = []
        self._init_buffer()
        
        # 光标位置
        self._cursor_row = 0
        self._cursor_col = 0
        
        # 保存的光标位置
        self._saved_cursor_row = 0
        self._saved_cursor_col = 0
        
        # 滚动区域
        self._scroll_top = 0
        self._scroll_bottom = rows - 1
        
        # 累计写入字节数
        self._total_appended = 0
        
        # 是否已销毁
        self._disposed = False
        
        # 当前样式状态（简化处理，主要用于跟踪）
        self._current_style: Dict[str, Any] = {}
    
    def _init_buffer(self) -> None:
        """初始化缓冲区"""
        total_rows = self._rows + self._scrollback
        self._buffer = [[' ' for _ in range(self._cols)] for _ in range(total_rows)]
    
    def set_on_screen_update(self, callback: Optional[Callable[[ScreenUpdateInfo], None]]) -> None:
        """设置屏幕更新回调"""
        self._on_screen_update = callback
    
    def write(self, data: str) -> None:
        """
        追加 PTY 原始输出（含 ANSI 转义序列）
        
        Args:
            data: 原始输出数据
        """
        if self._disposed:
            return
        
        self._total_appended += len(data)
        self._process_output(data)
        
        # 触发回调
        if self._on_screen_update:
            self._on_screen_update(ScreenUpdateInfo(
                last_lines=self.get_last_lines(self._callback_tail_lines),
                total_appended=self._total_appended
            ))
    
    def append(self, data: str) -> None:
        """append 方法（与 write 相同）"""
        self.write(data)
    
    def _process_output(self, data: str) -> None:
        """处理输出数据，解析 ANSI 转义序列"""
        i = 0
        while i < len(data):
            char = data[i]
            
            # 检查 ANSI 转义序列
            if char == '\x1b':
                # 尝试解析完整的转义序列
                seq_end, command, params = self._parse_ansi_sequence(data, i)
                if seq_end > i:
                    self._execute_ansi_command(command, params)
                    i = seq_end
                    continue
            
            # 普通字符处理
            if char == '\n':
                self._cursor_down()
            elif char == '\r':
                self._cursor_col = 0
            elif char == '\t':
                # 制表符：移动到下一个 8 字符边界
                next_tab = (self._cursor_col + 8) & ~7
                self._cursor_col = min(next_tab, self._cols - 1)
            elif char == '\b':
                # 退格
                if self._cursor_col > 0:
                    self._cursor_col -= 1
            elif char >= ' ' and char <= '~' or ord(char) > 127:
                # 可打印字符
                self._put_char(char)
            
            i += 1
    
    def _parse_ansi_sequence(self, data: str, start: int) -> tuple:
        """
        解析 ANSI 转义序列
        
        Returns:
            (end_index, command, params)
        """
        if start + 1 >= len(data):
            return (start + 1, None, [])
        
        next_char = data[start + 1]
        
        # CSI 序列：\x1b[...
        if next_char == '[':
            # 查找命令字符
            i = start + 2
            params_str = ""
            while i < len(data):
                c = data[i]
                if c.isalpha() or c in 'Hfmsrc':
                    command = c
                    params = self._parse_params(params_str)
                    return (i + 1, command, params)
                elif c.isdigit() or c in ';?':
                    params_str += c
                else:
                    # 未知序列，跳过
                    return (i + 1, None, [])
                i += 1
            return (i, None, [])
        
        # 其他转义序列
        if next_char == 'c':
            # 重置终端
            return (start + 2, ANSICommand.RESET.value, [])
        elif next_char == '7':
            # 保存光标
            return (start + 2, 's', [])
        elif next_char == '8':
            # 恢复光标
            return (start + 2, 'u', [])
        elif next_char == 'M':
            # 向上滚动一行
            self._scroll_up()
            return (start + 2, None, [])
        elif next_char == 'D':
            # 向下滚动一行
            self._scroll_down()
            return (start + 2, None, [])
        
        return (start + 2, None, [])
    
    def _parse_params(self, params_str: str) -> List[int]:
        """解析 CSI 参数"""
        if not params_str:
            return []
        
        params = []
        for p in params_str.split(';'):
            try:
                params.append(int(p) if p else 0)
            except ValueError:
                params.append(0)
        return params
    
    def _execute_ansi_command(self, command: Optional[str], params: List[int]) -> None:
        """执行 ANSI 命令"""
        if command is None:
            return
        
        if command == 'A':
            # 光标上移
            n = params[0] if params else 1
            self._cursor_row = max(0, self._cursor_row - n)
        
        elif command == 'B':
            # 光标下移
            n = params[0] if params else 1
            self._cursor_row = min(self._rows - 1, self._cursor_row + n)
        
        elif command == 'C':
            # 光标前移
            n = params[0] if params else 1
            self._cursor_col = min(self._cols - 1, self._cursor_col + n)
        
        elif command == 'D':
            # 光标后移
            n = params[0] if params else 1
            self._cursor_col = max(0, self._cursor_col - n)
        
        elif command in ('H', 'f'):
            # 光标定位
            row = (params[0] if len(params) > 0 else 1) - 1
            col = (params[1] if len(params) > 1 else 1) - 1
            self._cursor_row = max(0, min(self._rows - 1, row))
            self._cursor_col = max(0, min(self._cols - 1, col))
        
        elif command == 'J':
            # 清屏
            mode = params[0] if params else 0
            if mode == 0:
                # 从光标到屏幕末尾
                self._clear_from_cursor_to_end()
            elif mode == 1:
                # 从屏幕开头到光标
                self._clear_from_start_to_cursor()
            elif mode == 2 or mode == 3:
                # 整个屏幕
                self._clear_screen()
        
        elif command == 'K':
            # 清除行
            mode = params[0] if params else 0
            if mode == 0:
                # 从光标到行末
                self._clear_line_from_cursor()
            elif mode == 1:
                # 从行首到光标
                self._clear_line_to_cursor()
            elif mode == 2:
                # 整行
                self._clear_entire_line()
        
        elif command == 'r':
            # 设置滚动区域
            top = (params[0] if len(params) > 0 else 1) - 1
            bottom = (params[1] if len(params) > 1 else self._rows) - 1
            self._scroll_top = max(0, top)
            self._scroll_bottom = min(self._rows - 1, bottom)
        
        elif command == 's':
            # 保存光标位置
            self._saved_cursor_row = self._cursor_row
            self._saved_cursor_col = self._cursor_col
        
        elif command == 'u':
            # 恢复光标位置
            self._cursor_row = self._saved_cursor_row
            self._cursor_col = self._saved_cursor_col
        
        elif command == 'm':
            # SGR - 选择图形渲染（颜色/样式）
            # 简化处理，只跟踪状态
            self._handle_sgr(params)
        
        elif command == 'c':
            # 重置终端
            self._reset()
    
    def _handle_sgr(self, params: List[int]) -> None:
        """处理 SGR 参数（颜色/样式）"""
        for p in params:
            if p == 0:
                # 重置所有属性
                self._current_style = {}
            elif p == 1:
                self._current_style['bold'] = True
            elif p == 4:
                self._current_style['underline'] = True
            elif p == 7:
                self._current_style['reverse'] = True
            elif p >= 30 and p <= 37:
                self._current_style['fg_color'] = p - 30
            elif p >= 40 and p <= 47:
                self._current_style['bg_color'] = p - 40
    
    def _put_char(self, char: str) -> None:
        """在当前光标位置放置字符"""
        if self._cursor_row >= len(self._buffer):
            return
        
        row_idx = self._get_buffer_row(self._cursor_row)
        if row_idx < 0 or row_idx >= len(self._buffer):
            return
        
        self._buffer[row_idx][self._cursor_col] = char
        self._cursor_col += 1
        
        # 光标超出列宽时换行
        if self._cursor_col >= self._cols:
            self._cursor_col = 0
            self._cursor_down()
    
    def _cursor_down(self) -> None:
        """光标下移一行"""
        if self._cursor_row < self._scroll_bottom:
            self._cursor_row += 1
        else:
            # 在滚动区域底部，触发滚动
            self._scroll_up()
    
    def _scroll_up(self) -> None:
        """向上滚动一行"""
        # 将滚动区域顶部的行移到回滚缓冲区
        # 所有行向上移动
        top_buffer_row = self._get_buffer_row(self._scroll_top)
        bottom_buffer_row = self._get_buffer_row(self._scroll_bottom)
        
        if top_buffer_row >= 0 and bottom_buffer_row < len(self._buffer):
            # 清除顶部行（移入回滚缓冲区）
            self._buffer[top_buffer_row] = [' ' for _ in range(self._cols)]
            
            # 行向上移动
            for i in range(top_buffer_row, bottom_buffer_row):
                self._buffer[i] = self._buffer[i + 1]
            
            # 清除底部行
            self._buffer[bottom_buffer_row] = [' ' for _ in range(self._cols)]
    
    def _scroll_down(self) -> None:
        """向下滚动一行"""
        top_buffer_row = self._get_buffer_row(self._scroll_top)
        bottom_buffer_row = self._get_buffer_row(self._scroll_bottom)
        
        if top_buffer_row >= 0 and bottom_buffer_row < len(self._buffer):
            # 行向下移动
            for i in range(bottom_buffer_row, top_buffer_row, -1):
                self._buffer[i] = self._buffer[i - 1]
            
            # 清除顶部行
            self._buffer[top_buffer_row] = [' ' for _ in range(self._cols)]
    
    def _get_buffer_row(self, screen_row: int) -> int:
        """将屏幕行号转换为缓冲区行号"""
        # 简化实现：直接使用屏幕行号
        return screen_row
    
    def _clear_from_cursor_to_end(self) -> None:
        """从光标到屏幕末尾清除"""
        # 清除当前行从光标到行末
        self._clear_line_from_cursor()
        
        # 清除后续所有行
        for row in range(self._cursor_row + 1, self._rows):
            row_idx = self._get_buffer_row(row)
            if row_idx < len(self._buffer):
                self._buffer[row_idx] = [' ' for _ in range(self._cols)]
    
    def _clear_from_start_to_cursor(self) -> None:
        """从屏幕开头到光标清除"""
        # 清除之前所有行
        for row in range(0, self._cursor_row):
            row_idx = self._get_buffer_row(row)
            if row_idx < len(self._buffer):
                self._buffer[row_idx] = [' ' for _ in range(self._cols)]
        
        # 清除当前行从行首到光标
        self._clear_line_to_cursor()
    
    def _clear_screen(self) -> None:
        """清除整个屏幕"""
        for row in range(self._rows):
            row_idx = self._get_buffer_row(row)
            if row_idx < len(self._buffer):
                self._buffer[row_idx] = [' ' for _ in range(self._cols)]
    
    def _clear_line_from_cursor(self) -> None:
        """从光标到行末清除"""
        row_idx = self._get_buffer_row(self._cursor_row)
        if row_idx < len(self._buffer):
            for col in range(self._cursor_col, self._cols):
                self._buffer[row_idx][col] = ' '
    
    def _clear_line_to_cursor(self) -> None:
        """从行首到光标清除"""
        row_idx = self._get_buffer_row(self._cursor_row)
        if row_idx < len(self._buffer):
            for col in range(0, self._cursor_col + 1):
                self._buffer[row_idx][col] = ' '
    
    def _clear_entire_line(self) -> None:
        """清除整行"""
        row_idx = self._get_buffer_row(self._cursor_row)
        if row_idx < len(self._buffer):
            self._buffer[row_idx] = [' ' for _ in range(self._cols)]
    
    def _reset(self) -> None:
        """重置终端"""
        self._init_buffer()
        self._cursor_row = 0
        self._cursor_col = 0
        self._saved_cursor_row = 0
        self._saved_cursor_col = 0
        self._scroll_top = 0
        self._scroll_bottom = self._rows - 1
        self._current_style = {}
    
    def get_text(self) -> str:
        """
        获取终端屏幕的实际显示内容（纯文本）
        
        Returns:
            屏幕内容字符串
        """
        if self._disposed:
            return ''
        
        lines = []
        for row in range(self._rows):
            row_idx = self._get_buffer_row(row)
            if row_idx < len(self._buffer):
                line = ''.join(self._buffer[row_idx]).rstrip()
                lines.append(line)
        
        # 去除末尾空行
        while lines and lines[-1] == '':
            lines.pop()
        
        return '\n'.join(lines)
    
    def get_last_chars(self, n: int) -> str:
        """获取最后 n 个字符"""
        text = self.get_text()
        return text[-n:] if n > 0 else ''
    
    def get_last_lines(self, n: int) -> List[str]:
        """
        获取最后 N 行文本
        
        Args:
            n: 行数
            
        Returns:
            最后 N 行文本列表
        """
        if self._disposed:
            return []
        
        lines = []
        for row in range(self._rows):
            row_idx = self._get_buffer_row(row)
            if row_idx < len(self._buffer):
                line = ''.join(self._buffer[row_idx]).rstrip()
                lines.append(line)
        
        # 去除末尾空行
        while lines and lines[-1] == '':
            lines.pop()
        
        return lines[-n:] if n > 0 else lines
    
    def clear(self) -> None:
        """清空终端内容"""
        if self._disposed:
            return
        
        self._reset()
        self._total_appended = 0
    
    @property
    def length(self) -> int:
        """当前终端文本内容长度"""
        if self._disposed:
            return 0
        text = self.get_text()
        return max(1, len(text)) if self._total_appended > 0 else 0
    
    @property
    def total_appended(self) -> int:
        """累计追加的总字节数"""
        return self._total_appended
    
    @property
    def cursor_position(self) -> tuple:
        """当前光标位置 (row, col)"""
        return (self._cursor_row, self._cursor_col)
    
    def dispose(self) -> None:
        """销毁终端实例，释放资源"""
        if self._disposed:
            return
        
        self._disposed = True
        self._on_screen_update = None
        self._buffer = []
    
    def resize(self, cols: int, rows: int) -> None:
        """
        调整终端尺寸
        
        Args:
            cols: 新列宽
            rows: 新行数
        """
        if self._disposed:
            return
        
        old_cols = self._cols
        self._cols = cols
        self._rows = rows
        self._scroll_bottom = rows - 1
        
        # 调整缓冲区
        for i, row in enumerate(self._buffer):
            if len(row) < cols:
                row.extend([' ' for _ in range(cols - len(row))])
            elif len(row) > cols:
                self._buffer[i] = row[:cols]
        
        # 确保光标在有效范围内
        self._cursor_col = min(self._cursor_col, cols - 1)
        self._cursor_row = min(self._cursor_row, rows - 1)
    
    def get_buffer_info(self) -> Dict[str, Any]:
        """获取缓冲区信息"""
        return {
            'cols': self._cols,
            'rows': self._rows,
            'scrollback': self._scrollback,
            'cursor_row': self._cursor_row,
            'cursor_col': self._cursor_col,
            'total_appended': self._total_appended,
            'disposed': self._disposed
        }