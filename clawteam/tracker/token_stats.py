"""Token 用量统计器 - 支持按会话/按日累计和持久化

参考 SpectrAI UsageEstimator.ts 实现。
支持字符估算、持久化、趋势分析、Web UI 集成。

@author ClawTeam
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class UsageSummary:
    """用量汇总"""

    total_tokens: int = 0
    total_minutes: int = 0
    today_tokens: int = 0
    today_minutes: int = 0
    active_sessions: int = 0
    session_breakdown: dict[str, int] = field(default_factory=dict)
    provider_breakdown: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "totalTokens": self.total_tokens,
            "totalMinutes": self.total_minutes,
            "todayTokens": self.today_tokens,
            "todayMinutes": self.today_minutes,
            "activeSessions": self.active_sessions,
            "sessionBreakdown": self.session_breakdown,
            "providerBreakdown": self.provider_breakdown,
        }


@dataclass
class DailyUsage:
    """每日用量"""

    date: str  # YYYY-MM-DD
    tokens: int = 0
    minutes: int = 0
    sessions: int = 0
    providers: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "tokens": self.tokens,
            "minutes": self.minutes,
            "sessions": self.sessions,
            "providers": self.providers,
        }


@dataclass
class SessionUsage:
    """会话用量"""

    session_id: str
    tokens: int = 0
    minutes: int = 0
    start_time: float = 0
    last_update: float = 0
    provider: str = ""
    task_type: str = ""

    def to_dict(self) -> dict:
        return {
            "sessionId": self.session_id,
            "tokens": self.tokens,
            "minutes": self.minutes,
            "startTime": self.start_time,
            "lastUpdate": self.last_update,
            "provider": self.provider,
            "taskType": self.task_type,
        }


@dataclass
class TrendAnalysis:
    """趋势分析结果"""

    daily_data: list[DailyUsage] = field(default_factory=list)
    avg_daily_tokens: float = 0
    avg_daily_minutes: float = 0
    peak_day: str = ""
    peak_tokens: int = 0
    growth_rate: float = 0  # 相比上周的增长率
    prediction_next_day: int = 0  # 预测明天的用量

    def to_dict(self) -> dict:
        return {
            "dailyData": [d.to_dict() for d in self.daily_data],
            "avgDailyTokens": self.avg_daily_tokens,
            "avgDailyMinutes": self.avg_daily_minutes,
            "peakDay": self.peak_day,
            "peakTokens": self.peak_tokens,
            "growthRate": self.growth_rate,
            "predictionNextDay": self.prediction_next_day,
        }


@dataclass
class ProviderUsageStats:
    """Provider 用量统计"""

    provider: str
    total_tokens: int = 0
    total_sessions: int = 0
    avg_tokens_per_session: float = 0
    percentage: float = 0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "totalTokens": self.total_tokens,
            "totalSessions": self.total_sessions,
            "avgTokensPerSession": self.avg_tokens_per_session,
            "percentage": self.percentage,
        }


def _get_data_dir() -> Path:
    """获取数据目录"""
    from clawteam.team.models import get_data_dir

    return get_data_dir()


def _usage_file() -> Path:
    """用量数据文件路径"""
    return _get_data_dir() / "usage" / "token_stats.json"


def _ensure_usage_dir() -> Path:
    """确保用量数据目录存在"""
    usage_dir = _get_data_dir() / "usage"
    usage_dir.mkdir(parents=True, exist_ok=True)
    return usage_dir


class UsageEstimator:
    """Token 用量估算器

    基于字符数估算 Token 消耗，支持持久化到文件。
    参考 SpectrAI UsageEstimator.ts 实现。
    """

    def __init__(self):
        # 每个会话的累计 Token 用量
        self._session_usage: dict[str, SessionUsage] = {}
        # 每日用量历史
        self._daily_history: dict[str, DailyUsage] = {}
        # 数据文件路径
        self._data_file = _usage_file()
        # 定时 flush 定时器
        self._flush_timer: threading.Timer | None = None
        # 锁
        self._lock = threading.Lock()
        # 加载历史数据
        self._load_from_file()
        # 启动定时 flush
        self._start_flush_timer()

    # ------------------------------------------------------------------
    # Token 估算
    # ------------------------------------------------------------------

    def estimate_tokens(self, text: str) -> int:
        """估算文本的 Token 数量

        ASCII 字符: 约 4 字符 = 1 token
        非 ASCII 字符: 约 2 字符 = 1 token
        """
        if not text:
            return 0

        ascii_chars = 0
        non_ascii_chars = 0

        for char in text:
            if ord(char) <= 127:
                ascii_chars += 1
            else:
                non_ascii_chars += 1

        # 向上取整除法，最少1个token
        tokens = ((ascii_chars + 3) // 4) + ((non_ascii_chars + 1) // 2)
        return max(1, tokens)

    # ------------------------------------------------------------------
    # 用量累加
    # ------------------------------------------------------------------

    def accumulate_usage(
        self,
        session_id: str,
        text: str,
        provider: str = "",
        task_type: str = "",
    ) -> int:
        """累加会话的 Token 用量

        Args:
            session_id: 会话 ID
            text: 文本内容
            provider: Provider 名称（可选）
            task_type: 任务类型（可选）

        Returns:
            本次累加的 Token 数
        """
        tokens = self.estimate_tokens(text)

        with self._lock:
            now = time.time()

            if session_id not in self._session_usage:
                # 新会话
                self._session_usage[session_id] = SessionUsage(
                    session_id=session_id,
                    tokens=tokens,
                    start_time=now,
                    last_update=now,
                    provider=provider,
                    task_type=task_type,
                )
            else:
                # 已有会话
                usage = self._session_usage[session_id]
                usage.tokens += tokens
                usage.last_update = now
                if provider:
                    usage.provider = provider
                if task_type:
                    usage.task_type = task_type

        return tokens

    def record_request(
        self,
        session_id: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "",
        task_type: str = "",
    ) -> int:
        """记录请求的 Token 用量（精确计数）

        Args:
            session_id: 会话 ID
            input_tokens: 输入 Token 数
            output_tokens: 输出 Token 数
            provider: Provider 名称
            task_type: 任务类型

        Returns:
            总 Token 数
        """
        total_tokens = input_tokens + output_tokens

        with self._lock:
            now = time.time()

            if session_id not in self._session_usage:
                self._session_usage[session_id] = SessionUsage(
                    session_id=session_id,
                    tokens=total_tokens,
                    start_time=now,
                    last_update=now,
                    provider=provider,
                    task_type=task_type,
                )
            else:
                usage = self._session_usage[session_id]
                usage.tokens += total_tokens
                usage.last_update = now
                if provider:
                    usage.provider = provider
                if task_type:
                    usage.task_type = task_type

        return total_tokens

    def mark_session_ended(self, session_id: str) -> None:
        """标记会话结束 - 计算活跃时间并 flush"""
        with self._lock:
            if session_id not in self._session_usage:
                return

            usage = self._session_usage[session_id]
            # 计算活跃分钟数
            elapsed_seconds = time.time() - usage.start_time
            usage.minutes = int(elapsed_seconds // 60)

            # Flush 到文件
            self._flush_session_to_file(session_id)

            # 清理（但保留数据给 summary 查看）
            del self._session_usage[session_id]

    # ------------------------------------------------------------------
    # 用量查询
    # ------------------------------------------------------------------

    def get_summary(self) -> UsageSummary:
        """获取用量汇总"""
        with self._lock:
            total_tokens = 0
            total_minutes = 0
            session_breakdown = {}
            provider_breakdown = {}
            active_sessions = 0

            for session_id, usage in self._session_usage.items():
                total_tokens += usage.tokens
                # 更新活跃分钟数
                elapsed_seconds = time.time() - usage.start_time
                current_minutes = int(elapsed_seconds // 60)
                total_minutes += current_minutes
                session_breakdown[session_id] = usage.tokens

                # Provider 统计
                if usage.provider:
                    provider_breakdown[usage.provider] = (
                        provider_breakdown.get(usage.provider, 0) + usage.tokens
                    )

                active_sessions += 1

            # 今日数据（从历史加载）
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_history = self._daily_history.get(today)
            history_tokens = today_history.tokens if today_history else 0
            history_minutes = today_history.minutes if today_history else 0

            return UsageSummary(
                total_tokens=total_tokens + history_tokens,
                total_minutes=total_minutes + history_minutes,
                today_tokens=total_tokens + history_tokens,
                today_minutes=total_minutes + history_minutes,
                active_sessions=active_sessions,
                session_breakdown=session_breakdown,
                provider_breakdown=provider_breakdown,
            )

    def get_session_usage(self, session_id: str) -> int:
        """获取指定会话的用量"""
        with self._lock:
            if session_id in self._session_usage:
                return self._session_usage[session_id].tokens
            return 0

    def get_trend(self, days: int = 30) -> TrendAnalysis:
        """获取趋势分析"""
        with self._lock:
            # 获取最近 N 天的数据
            daily_data = []
            today = datetime.now(timezone.utc)

            for i in range(days):
                date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
                if date in self._daily_history:
                    daily_data.append(self._daily_history[date])
                else:
                    daily_data.append(DailyUsage(date=date))

            # 添加今日活跃会话数据
            today_str = today.strftime("%Y-%m-%d")
            today_tokens = sum(u.tokens for u in self._session_usage.values())
            today_minutes = sum(
                int((time.time() - u.start_time) // 60) for u in self._session_usage.values()
            )

            if today_str in self._daily_history:
                self._daily_history[today_str].tokens += today_tokens
                self._daily_history[today_str].minutes += today_minutes
                self._daily_history[today_str].sessions += len(self._session_usage)
            else:
                self._daily_history[today_str] = DailyUsage(
                    date=today_str,
                    tokens=today_tokens,
                    minutes=today_minutes,
                    sessions=len(self._session_usage),
                )

            # 计算统计数据
            total_tokens = sum(d.tokens for d in daily_data)
            total_minutes = sum(d.minutes for d in daily_data)
            avg_daily_tokens = total_tokens / days if days > 0 else 0
            avg_daily_minutes = total_minutes / days if days > 0 else 0

            # 找峰值日
            peak_day = ""
            peak_tokens = 0
            for d in daily_data:
                if d.tokens > peak_tokens:
                    peak_tokens = d.tokens
                    peak_day = d.date

            # 计算增长率（相比上周）
            this_week_tokens = sum(d.tokens for d in daily_data[:7])
            last_week_tokens = sum(d.tokens for d in daily_data[7:14]) if days >= 14 else 0
            growth_rate = 0
            if last_week_tokens > 0:
                growth_rate = (this_week_tokens - last_week_tokens) / last_week_tokens * 100

            # 预测明天用量（简单线性预测）
            prediction_next_day = int(avg_daily_tokens)
            if len(daily_data) >= 3:
                # 使用最近3天的平均值作为预测
                recent_avg = sum(d.tokens for d in daily_data[:3]) / 3
                prediction_next_day = int(recent_avg)

            return TrendAnalysis(
                daily_data=daily_data,
                avg_daily_tokens=avg_daily_tokens,
                avg_daily_minutes=avg_daily_minutes,
                peak_day=peak_day,
                peak_tokens=peak_tokens,
                growth_rate=growth_rate,
                prediction_next_day=prediction_next_day,
            )

    def get_provider_stats(self) -> list[ProviderUsageStats]:
        """获取 Provider 用量统计"""
        with self._lock:
            provider_totals: dict[str, int] = {}
            provider_sessions: dict[str, int] = {}

            # 从活跃会话统计
            for usage in self._session_usage.values():
                if usage.provider:
                    provider_totals[usage.provider] = (
                        provider_totals.get(usage.provider, 0) + usage.tokens
                    )
                    provider_sessions[usage.provider] = provider_sessions.get(usage.provider, 0) + 1

            # 从历史统计
            for daily in self._daily_history.values():
                for provider, tokens in daily.providers.items():
                    provider_totals[provider] = provider_totals.get(provider, 0) + tokens

            # 计算百分比和平均值
            total_all = sum(provider_totals.values())
            stats = []

            for provider, tokens in provider_totals.items():
                sessions = provider_sessions.get(provider, 0)
                avg = tokens / sessions if sessions > 0 else 0
                percentage = tokens / total_all * 100 if total_all > 0 else 0

                stats.append(
                    ProviderUsageStats(
                        provider=provider,
                        total_tokens=tokens,
                        total_sessions=sessions,
                        avg_tokens_per_session=avg,
                        percentage=percentage,
                    )
                )

            # 按用量排序
            stats.sort(key=lambda s: s.total_tokens, reverse=True)
            return stats

    # ------------------------------------------------------------------
    # 持久化
    # ------------------------------------------------------------------

    def _flush_session_to_file(self, session_id: str) -> None:
        """将单个会话的用量写入文件"""
        if session_id not in self._session_usage:
            return

        usage = self._session_usage[session_id]
        if usage.tokens == 0:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 更新每日统计
        if today not in self._daily_history:
            self._daily_history[today] = DailyUsage(date=today)

        self._daily_history[today].tokens += usage.tokens
        self._daily_history[today].minutes += usage.minutes
        self._daily_history[today].sessions += 1

        # Provider 统计
        if usage.provider:
            self._daily_history[today].providers[usage.provider] = (
                self._daily_history[today].providers.get(usage.provider, 0) + usage.tokens
            )

        # 写入文件
        self._save_to_file()

    def _save_to_file(self) -> None:
        """保存所有数据到文件"""
        _ensure_usage_dir()

        data = {
            "dailyHistory": {date: daily.to_dict() for date, daily in self._daily_history.items()},
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with open(self._data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Failed to save usage data: {e}")

    def _load_from_file(self) -> None:
        """从文件加载历史数据"""
        if not self._data_file.exists():
            return

        try:
            with open(self._data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 加载每日历史
            for date, daily_data in data.get("dailyHistory", {}).items():
                self._daily_history[date] = DailyUsage(
                    date=date,
                    tokens=daily_data.get("tokens", 0),
                    minutes=daily_data.get("minutes", 0),
                    sessions=daily_data.get("sessions", 0),
                    providers=daily_data.get("providers", {}),
                )

            logger.info(f"Loaded usage history from {self._data_file}")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to load usage data: {e}")

    def _start_flush_timer(self) -> None:
        """启动定时 flush 定时器"""

        def _flush():
            with self._lock:
                # Flush 所有活跃会话
                for session_id in list(self._session_usage.keys()):
                    usage = self._session_usage[session_id]
                    elapsed_seconds = time.time() - usage.start_time
                    usage.minutes = int(elapsed_seconds // 60)

                # 保存到文件
                self._save_to_file()

            # 重新启动定时器
            self._start_flush_timer()

        self._flush_timer = threading.Timer(60.0, _flush)  # 每60秒 flush
        self._flush_timer.daemon = True
        self._flush_timer.start()

    def cleanup(self) -> None:
        """清理资源"""
        if self._flush_timer:
            self._flush_timer.cancel()
            self._flush_timer = None

        # 最终 flush
        with self._lock:
            self._save_to_file()

    # ------------------------------------------------------------------
    # Web UI 集成
    # ------------------------------------------------------------------

    def get_web_ui_data(self) -> dict:
        """获取 Web UI 展示数据"""
        summary = self.get_summary()
        trend = self.get_trend(30)
        provider_stats = self.get_provider_stats()

        return {
            "summary": summary.to_dict(),
            "trend": trend.to_dict(),
            "providerStats": [s.to_dict() for s in provider_stats],
            "lastUpdated": datetime.now(timezone.utc).isoformat(),
        }

    def reset_all(self) -> None:
        """重置所有用量数据"""
        with self._lock:
            self._session_usage.clear()
            self._daily_history.clear()
            self._save_to_file()


# 全局实例
_global_estimator: UsageEstimator | None = None
_estimator_lock = threading.Lock()


def get_usage_estimator() -> UsageEstimator:
    """获取全局 UsageEstimator 实例"""
    global _global_estimator

    with _estimator_lock:
        if _global_estimator is None:
            _global_estimator = UsageEstimator()
        return _global_estimator


def get_usage_summary() -> UsageSummary:
    """获取用量汇总（便捷函数）"""
    return get_usage_estimator().get_summary()


def get_usage_trend(days: int = 30) -> TrendAnalysis:
    """获取趋势分析（便捷函数）"""
    return get_usage_estimator().get_trend(days)


def get_provider_stats() -> list[ProviderUsageStats]:
    """获取 Provider 统计（便捷函数）"""
    return get_usage_estimator().get_provider_stats()


def accumulate_usage(session_id: str, text: str, provider: str = "") -> int:
    """累加用量（便捷函数）"""
    return get_usage_estimator().accumulate_usage(session_id, text, provider)


def record_request(
    session_id: str, input_tokens: int, output_tokens: int, provider: str = ""
) -> int:
    """记录请求（便捷函数）"""
    return get_usage_estimator().record_request(session_id, input_tokens, output_tokens, provider)


def mark_session_ended(session_id: str) -> None:
    """标记会话结束（便捷函数）"""
    get_usage_estimator().mark_session_ended(session_id)


def estimate_tokens(text: str) -> int:
    """估算文本的 Token 数量（便捷函数）"""
    return get_usage_estimator().estimate_tokens(text)
