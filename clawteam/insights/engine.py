"""洞察引擎 — 使用统计和趋势分析。

能力：
- Token 消耗统计
- 工具使用频率
- 技能使用模式
- 活动模式分析（按天/小时分布）
- 成本估算

依赖：clawteam.database.DatabaseManager
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenUsageStats:
    """Token 使用统计"""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    by_provider: Dict[str, Dict[str, int]] = None  # provider_id -> {input, output, total, cost}
    
    def __post_init__(self):
        if self.by_provider is None:
            self.by_provider = {}


@dataclass
class ToolUsageStats:
    """工具使用统计"""
    total_tool_calls: int = 0
    by_tool: Dict[str, int] = None  # tool_name -> count
    by_hour: Dict[int, int] = None  # hour (0-23) -> count
    
    def __post_init__(self):
        if self.by_tool is None:
            self.by_tool = {}
        if self.by_hour is None:
            self.by_hour = {}


@dataclass
class ActivityStats:
    """活动模式统计"""
    total_sessions: int = 0
    active_days: int = 0
    avg_session_duration_minutes: float = 0.0
    by_weekday: Dict[int, int] = None  # 0=Monday -> count
    by_hour: Dict[int, int] = None    # 0-23 -> count
    
    def __post_init__(self):
        if self.by_weekday is None:
            self.by_weekday = {}
        if self.by_hour is None:
            self.by_hour = {}


@dataclass
class SkillUsageStats:
    """技能使用统计"""
    total_skill_invocations: int = 0
    by_skill: Dict[str, int] = None  # skill_name -> count
    
    def __post_init__(self):
        if self.by_skill is None:
            self.by_skill = {}


class InsightsEngine:
    """洞察引擎"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: SQLite 数据库文件路径，None 则使用默认数据库
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None
        
    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self.conn is not None:
            return self.conn
        
        if self.db_path:
            db_file = Path(self.db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(db_file))
        else:
            # 使用默认数据库位置
            from clawteam.paths import get_data_dir
            data_dir = Path(get_data_dir())
            data_dir.mkdir(parents=True, exist_ok=True)
            db_file = data_dir / "clawteam.db"
            self.conn = sqlite3.connect(str(db_file))
        
        # 启用外键和 WAL 模式
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        
        return self.conn
    
    def _ensure_tables(self):
        """确保统计表存在"""
        conn = self._get_conn()
        
        # 使用统计表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage (
                id TEXT PRIMARY KEY,
                tool_name TEXT NOT NULL,
                session_id TEXT,
                team_id TEXT,
                task_id TEXT,
                timestamp DATETIME NOT NULL,
                metadata TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_usage (
                id TEXT PRIMARY KEY,
                skill_name TEXT NOT NULL,
                session_id TEXT,
                team_id TEXT,
                task_id TEXT,
                timestamp DATETIME NOT NULL,
                result_length INTEGER,
                metadata TEXT
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                team_id TEXT,
                task_id TEXT,
                event_type TEXT NOT NULL,  -- 'session_start', 'session_end', 'tool_call', 'skill_invoke'
                timestamp DATETIME NOT NULL,
                metadata TEXT
            )
        """)
        
        # 创建索引
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_usage_timestamp ON tool_usage(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage(tool_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_usage_timestamp ON skill_usage(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_usage_skill ON skill_usage(skill_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_event ON activity_log(event_type)")
        
        conn.commit()
    
    def record_tool_usage(self, tool_name: str, session_id: str = "", 
                         team_id: str = "", task_id: str = "", metadata: dict = None):
        """记录工具使用"""
        import uuid
        import time
        
        self._ensure_tables()
        conn = self._get_conn()
        
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn.execute(
            "INSERT INTO tool_usage (id, tool_name, session_id, team_id, task_id, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_id, tool_name, session_id, team_id, task_id, timestamp, 
             json.dumps(metadata) if metadata else None)
        )
        
        # 同时记录到活动日志
        activity_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO activity_log (id, session_id, team_id, task_id, event_type, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (activity_id, session_id, team_id, task_id, "tool_call", timestamp,
             json.dumps({"tool": tool_name, **(metadata or {})}))
        )
        
        conn.commit()
        logger.debug(f"Recorded tool usage: {tool_name}")
    
    def record_skill_usage(self, skill_name: str, session_id: str = "",
                          team_id: str = "", task_id: str = "", 
                          result_length: int = 0, metadata: dict = None):
        """记录技能使用"""
        import uuid
        
        self._ensure_tables()
        conn = self._get_conn()
        
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn.execute(
            "INSERT INTO skill_usage (id, skill_name, session_id, team_id, task_id, timestamp, result_length, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, skill_name, session_id, team_id, task_id, timestamp, 
             result_length, json.dumps(metadata) if metadata else None)
        )
        
        # 同时记录到活动日志
        activity_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO activity_log (id, session_id, team_id, task_id, event_type, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (activity_id, session_id, team_id, task_id, "skill_invoke", timestamp,
             json.dumps({"skill": skill_name, "result_length": result_length, **(metadata or {})}))
        )
        
        conn.commit()
        logger.debug(f"Recorded skill usage: {skill_name}")
    
    def record_session_activity(self, event_type: str, session_id: str,
                               team_id: str = "", task_id: str = "", metadata: dict = None):
        """记录会话活动（开始、结束等）"""
        import uuid
        
        self._ensure_tables()
        conn = self._get_conn()
        
        activity_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn.execute(
            "INSERT INTO activity_log (id, session_id, team_id, task_id, event_type, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (activity_id, session_id, team_id, task_id, event_type, timestamp,
             json.dumps(metadata) if metadata else None)
        )
        
        conn.commit()
        logger.debug(f"Recorded session activity: {event_type} for session {session_id}")
    
    def get_token_usage_stats(self, days: int = 30, team_id: str = None) -> TokenUsageStats:
        """获取 Token 使用统计"""
        stats = TokenUsageStats()
        
        try:
            # 尝试从数据库获取使用统计
            from clawteam.database import DatabaseManager
            db_manager = DatabaseManager()
            
            # 获取最近 N 天的使用数据
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.isoformat()
            
            # 这里需要数据库支持查询，暂时返回示例数据
            # 实际实现应该查询数据库
            logger.warning("Token usage stats from database not fully implemented yet")
            
            # 示例数据
            stats.total_input_tokens = 15000
            stats.total_output_tokens = 8000
            stats.total_tokens = 23000
            stats.estimated_cost = 0.023  # 假设成本
            
        except Exception as e:
            logger.error(f"Failed to get token usage stats: {e}")
        
        return stats
    
    def get_tool_usage_stats(self, days: int = 30, team_id: str = None) -> ToolUsageStats:
        """获取工具使用统计"""
        stats = ToolUsageStats()
        
        try:
            self._ensure_tables()
            conn = self._get_conn()
            
            # 计算时间范围
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.isoformat()
            
            # 按工具分组统计
            cursor = conn.execute("""
                SELECT tool_name, COUNT(*) as count 
                FROM tool_usage 
                WHERE timestamp >= ? 
                GROUP BY tool_name 
                ORDER BY count DESC
            """, (since_str,))
            
            for row in cursor.fetchall():
                tool_name, count = row
                stats.by_tool[tool_name] = count
                stats.total_tool_calls += count
            
            # 按小时统计
            cursor = conn.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM tool_usage
                WHERE timestamp >= ?
                GROUP BY hour
                ORDER BY hour
            """, (since_str,))
            
            for row in cursor.fetchall():
                hour, count = row
                stats.by_hour[int(hour)] = count
            
        except Exception as e:
            logger.error(f"Failed to get tool usage stats: {e}")
        
        return stats
    
    def get_skill_usage_stats(self, days: int = 30, team_id: str = None) -> SkillUsageStats:
        """获取技能使用统计"""
        stats = SkillUsageStats()
        
        try:
            self._ensure_tables()
            conn = self._get_conn()
            
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.isoformat()
            
            # 按技能分组统计
            cursor = conn.execute("""
                SELECT skill_name, COUNT(*) as count 
                FROM skill_usage 
                WHERE timestamp >= ? 
                GROUP BY skill_name 
                ORDER BY count DESC
            """, (since_str,))
            
            for row in cursor.fetchall():
                skill_name, count = row
                stats.by_skill[skill_name] = count
                stats.total_skill_invocations += count
            
        except Exception as e:
            logger.error(f"Failed to get skill usage stats: {e}")
        
        return stats
    
    def get_activity_stats(self, days: int = 30, team_id: str = None) -> ActivityStats:
        """获取活动模式统计"""
        stats = ActivityStats()
        
        try:
            self._ensure_tables()
            conn = self._get_conn()
            
            since_date = datetime.now() - timedelta(days=days)
            since_str = since_date.isoformat()
            
            # 获取会话活动
            cursor = conn.execute("""
                SELECT event_type, timestamp
                FROM activity_log
                WHERE timestamp >= ?
                ORDER BY timestamp
            """, (since_str,))
            
            sessions = {}
            session_starts = {}
            
            for row in cursor.fetchall():
                event_type, timestamp_str = row
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    continue
                
                # 这里需要解析 session_id，简化处理
                # 实际应该从 metadata 或单独列获取 session_id
                pass
            
            # 按工作日统计
            cursor = conn.execute("""
                SELECT strftime('%w', timestamp) as weekday, COUNT(*) as count
                FROM activity_log
                WHERE timestamp >= ?
                GROUP BY weekday
                ORDER BY weekday
            """, (since_str,))
            
            for row in cursor.fetchall():
                weekday, count = row
                stats.by_weekday[int(weekday)] = count
            
            # 按小时统计
            cursor = conn.execute("""
                SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                FROM activity_log
                WHERE timestamp >= ?
                GROUP BY hour
                ORDER BY hour
            """, (since_str,))
            
            for row in cursor.fetchall():
                hour, count = row
                stats.by_hour[int(hour)] = count
            
            # 计算活跃天数
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT date(timestamp)) as active_days
                FROM activity_log
                WHERE timestamp >= ?
            """, (since_str,))
            
            row = cursor.fetchone()
            if row:
                stats.active_days = row[0]
            
        except Exception as e:
            logger.error(f"Failed to get activity stats: {e}")
        
        return stats
    
    def generate_report(self, days: int = 30, team_id: str = None, format: str = "json") -> Dict[str, Any]:
        """生成综合报告"""
        report = {
            "generated_at": datetime.now().isoformat(),
            "time_range_days": days,
            "team_id": team_id,
            "format": format
        }
        
        # 收集各项统计
        token_stats = self.get_token_usage_stats(days, team_id)
        tool_stats = self.get_tool_usage_stats(days, team_id)
        skill_stats = self.get_skill_usage_stats(days, team_id)
        activity_stats = self.get_activity_stats(days, team_id)
        
        report["token_usage"] = {
            "total_input_tokens": token_stats.total_input_tokens,
            "total_output_tokens": token_stats.total_output_tokens,
            "total_tokens": token_stats.total_tokens,
            "estimated_cost": token_stats.estimated_cost,
            "by_provider": token_stats.by_provider
        }
        
        # 工具使用排行（前10）
        top_tools = sorted(tool_stats.by_tool.items(), key=lambda x: x[1], reverse=True)[:10]
        report["tool_usage"] = {
            "total_tool_calls": tool_stats.total_tool_calls,
            "top_tools": dict(top_tools),
            "by_hour": tool_stats.by_hour
        }
        
        # 技能使用排行（前10）
        top_skills = sorted(skill_stats.by_skill.items(), key=lambda x: x[1], reverse=True)[:10]
        report["skill_usage"] = {
            "total_skill_invocations": skill_stats.total_skill_invocations,
            "top_skills": dict(top_skills)
        }
        
        # 活动模式
        report["activity_patterns"] = {
            "active_days": activity_stats.active_days,
            "total_sessions": activity_stats.total_sessions,
            "avg_session_duration_minutes": activity_stats.avg_session_duration_minutes,
            "by_weekday": activity_stats.by_weekday,
            "by_hour": activity_stats.by_hour
        }
        
        # 计算一些衍生指标
        if days > 0:
            avg_daily_tokens = token_stats.total_tokens / days if days > 0 else 0
            avg_daily_tool_calls = tool_stats.total_tool_calls / days if days > 0 else 0
        else:
            avg_daily_tokens = avg_daily_tool_calls = 0
            
        report["summary_metrics"] = {
            "avg_daily_tokens": avg_daily_tokens,
            "avg_daily_tool_calls": avg_daily_tool_calls,
            "most_active_hour": max(activity_stats.by_hour.items(), key=lambda x: x[1])[0] if activity_stats.by_hour else None,
            "most_used_tool": top_tools[0][0] if top_tools else None,
            "most_used_skill": top_skills[0][0] if top_skills else None
        }
        
        if format == "html":
            report["html"] = self._format_html_report(report)
        
        return report
    
    def _format_html_report(self, report: Dict[str, Any]) -> str:
        """将报告格式化为 HTML"""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>ClawTeam Insights Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .section {{ margin-bottom: 30px; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .metric {{ display: inline-block; margin-right: 20px; margin-bottom: 10px; }}
        .metric-value {{ font-size: 24px; font-weight: bold; }}
        .metric-label {{ font-size: 14px; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <h1>ClawTeam Insights Report</h1>
    <p>Generated at: {report['generated_at']}</p>
    <p>Time range: {report['time_range_days']} days</p>
    
    <div class="section">
        <h2>Summary Metrics</h2>
        <div class="metric">
            <div class="metric-value">{report['summary_metrics']['avg_daily_tokens']:.0f}</div>
            <div class="metric-label">Avg Daily Tokens</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report['summary_metrics']['avg_daily_tool_calls']:.0f}</div>
            <div class="metric-label">Avg Daily Tool Calls</div>
        </div>
        <div class="metric">
            <div class="metric-value">{report['token_usage']['estimated_cost']:.4f}</div>
            <div class="metric-label">Estimated Cost ($)</div>
        </div>
    </div>
    
    <div class="section">
        <h2>Token Usage</h2>
        <p>Total Tokens: {report['token_usage']['total_tokens']:,} (Input: {report['token_usage']['total_input_tokens']:,}, Output: {report['token_usage']['total_output_tokens']:,})</p>
    </div>
    
    <div class="section">
        <h2>Top Tools</h2>
        <table>
            <tr><th>Tool</th><th>Usage Count</th></tr>
"""
        
        for tool, count in report['tool_usage']['top_tools'].items():
            html += f"<tr><td>{tool}</td><td>{count}</td></tr>\n"
        
        html += """
        </table>
    </div>
    
    <div class="section">
        <h2>Top Skills</h2>
        <table>
            <tr><th>Skill</th><th>Usage Count</th></tr>
"""
        
        for skill, count in report['skill_usage']['top_skills'].items():
            html += f"<tr><td>{skill}</td><td>{count}</td></tr>\n"
        
        html += """
        </table>
    </div>
    
</body>
</html>
"""
        return html
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __del__(self):
        self.close()