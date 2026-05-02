"""
Phase 1: .learnings 自动闭环引擎

实现 Hermes 协议一、二、五：
1. 任务完成后自动评估三问（新问题/用户纠正/更好方法）
2. 心跳驱动的自动反思逻辑
3. 每轮对话后记忆自动同步到 memory/ 目录

兼容 OpenClaw L1-L4 记忆架构，不侵入核心代码。
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 默认路径
# ---------------------------------------------------------------------------
_DEFAULT_WORKSPACE = Path.home() / ".openclaw" / "workspace"
_DEFAULT_LEARNINGS = _DEFAULT_WORKSPACE / ".learnings"
_DEFAULT_MEMORY = _DEFAULT_WORKSPACE / "memory"


class ThreeQuestionResult:
    """三问评估结果"""

    def __init__(self):
        self.has_new_problem: bool = False
        self.has_user_correction: bool = False
        self.has_better_method: bool = False
        self.new_problem_summary: str = ""
        self.correction_summary: str = ""
        self.better_method_summary: str = ""


class HermesSyncEngine:
    """Hermes 自动同步引擎 — Phase 1 核心"""

    def __init__(
        self,
        workspace: Optional[Path] = None,
        learnings_dir: Optional[Path] = None,
        memory_dir: Optional[Path] = None,
    ):
        self.workspace = workspace or _DEFAULT_WORKSPACE
        self.learnings_dir = learnings_dir or (self.workspace / ".learnings")
        self.memory_dir = memory_dir or (self.workspace / "memory")
        self.learnings_dir.mkdir(parents=True, exist_ok=True)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

        # 心跳计数器（用于周期性反思）
        self._heartbeat_count = 0

    # =====================================================================
    # 协议一：每轮对话后自动同步（sync_turn）
    # =====================================================================

    def sync_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        session_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """每轮对话后评估是否有值得记录的内容

        判断标准：
        - 新事实：人名、项目、日期、决策、地址
        - 偏好变化：表达了新的喜欢/不喜欢
        - 项目状态变更
        - 教训：犯了错、被纠正、发现了更好的方法

        如果满足 → 追加到 memory/YYYY-MM-DD.md
        如果是偏好/长期记忆 → 同步更新 USER.md

        Returns:
            如果记录了内容则返回记录信息，否则返回 None
        """
        content = f"{user_msg}\n{assistant_msg}"
        today = datetime.now().strftime("%Y-%m-%d")

        # 评估是否需要记录
        record_info = self._evaluate_turn(content, user_msg, assistant_msg)

        if not record_info:
            return None

        # 追加到今日 memory 文件
        memory_file = self.memory_dir / f"{today}.md"
        self._append_to_daily_memory(memory_file, record_info, session_id)

        # 如果是偏好变化，同步到 USER.md
        if record_info.get("type") == "preference_change":
            self._sync_preference_to_user_md(record_info)

        logger.info(f"[Hermes sync_turn] Recorded: {record_info.get('type')}")
        return record_info

    def _evaluate_turn(
        self,
        full_content: str,
        user_msg: str,
        assistant_msg: str,
    ) -> Optional[Dict[str, Any]]:
        """评估单轮对话是否需要记录"""
        # 1. 检测新事实
        facts = self._extract_facts(user_msg, assistant_msg)
        if facts:
            return {
                "type": "new_fact",
                "content": facts,
                "timestamp": datetime.now().isoformat(),
            }

        # 2. 检测偏好变化
        pref = self._detect_preference_change(user_msg)
        if pref:
            return {
                "type": "preference_change",
                "preference": pref,
                "timestamp": datetime.now().isoformat(),
            }

        # 3. 检测项目状态变更
        project = self._detect_project_change(user_msg, assistant_msg)
        if project:
            return {
                "type": "project_update",
                "content": project,
                "timestamp": datetime.now().isoformat(),
            }

        # 4. 检测教训
        lesson = self._detect_lesson(user_msg, assistant_msg)
        if lesson:
            return {
                "type": "lesson",
                "content": lesson,
                "timestamp": datetime.now().isoformat(),
            }

        return None

    def _extract_facts(self, user_msg: str, assistant_msg: str) -> Optional[str]:
        """提取新事实（人名、项目、日期、决策等）"""
        content = user_msg
        # 关键词模式
        fact_patterns = [
            r"(?:我叫|名字是|name[是是是])\s*(.+?)[。.!]",
            r"(?:项目名|project[是是])\s*(.+?)[。.!]",
            r"(?:截止日期|deadline|截止[是是])\s*(.+?)[。.!]",
            r"(?:决定|decided|选择了)\s*(.+?)[。.!]",
            r"(?:地址|address[是是])\s*(.+?)[。.!]",
        ]
        for pat in fact_patterns:
            match = re.search(pat, content, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _detect_preference_change(self, user_msg: str) -> Optional[Dict[str, Any]]:
        """检测用户偏好变化"""
        content = user_msg.lower()

        like_patterns = [
            (r"(?:喜欢|love|prefer|偏好).*?(.+?)[。.!]", "like"),
            (r"(?:不喜欢|hate|dislike|讨厌).*?(.+?)[。.!]", "dislike"),
        ]

        for pat, ptype in like_patterns:
            match = re.search(pat, content, re.IGNORECASE)
            if match:
                return {
                    "type": ptype,
                    "item": match.group(1).strip(),
                    "source": user_msg[:200],
                }

        return None

    def _detect_project_change(self, user_msg: str, assistant_msg: str) -> Optional[str]:
        """检测项目状态变更"""
        content = user_msg + " " + assistant_msg
        project_keywords = ["进度", "完成", "done", "finished", "更新了", "changed"]
        for kw in project_keywords:
            if kw in content.lower():
                return content[:300]
        return None

    def _detect_lesson(self, user_msg: str, assistant_msg: str) -> Optional[Dict[str, Any]]:
        """检测教训（犯错、纠正、更好的方法）"""
        content = (user_msg + " " + assistant_msg).lower()

        correction_patterns = [
            r"(?:不对|错了|wrong|incorrect|应该是).*?(.+?)[。.!]",
            r"(?:更好|better|improved|优化).*?(.+?)[。.!]",
            r"(?:下次|next time|以后).*?(.+?)[。.!]",
        ]

        for pat in correction_patterns:
            match = re.search(pat, content, re.IGNORECASE)
            if match:
                return {
                    "type": "correction",
                    "detail": match.group(1).strip(),
                    "source": (user_msg + " " + assistant_msg)[:300],
                }

        return None

    def _append_to_daily_memory(
        self,
        memory_file: Path,
        record_info: Dict[str, Any],
        session_id: str = "",
    ) -> None:
        """追加记录到当日 memory 文件"""
        timestamp = datetime.now().strftime("%H:%M")
        rec_type = record_info.get("type", "unknown")

        line = f"- [{timestamp}] **{rec_type}**: "

        if rec_type == "new_fact":
            line += f"{record_info.get('content', '')}"
        elif rec_type == "preference_change":
            pref = record_info.get("preference", {})
            line += f"偏好变化: {pref.get('type', '')} → {pref.get('item', '')}"
        elif rec_type == "project_update":
            line += f"{record_info.get('content', '')[:200]}"
        elif rec_type == "lesson":
            lesson = record_info.get("content", {})
            line += f"教训: {lesson.get('detail', '')}"

        if session_id:
            line += f" _(session: {session_id[:8]})_"

        line += "\n"

        # 如果文件不存在，添加标题
        if not memory_file.exists():
            with open(memory_file, "w", encoding="utf-8") as f:
                f.write(f"# {datetime.now().strftime('%Y-%m-%d')}\n\n")

        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(line)

    def _sync_preference_to_user_md(self, record_info: Dict[str, Any]) -> None:
        """将偏好变化同步到 USER.md（简化实现）"""
        user_md = self.workspace / "USER.md"
        if not user_md.exists():
            return

        try:
            content = user_md.read_text(encoding="utf-8")
            pref = record_info.get("preference", {})
            ptype = pref.get("type", "")
            item = pref.get("item", "")

            # 简单追加到 Notes 部分
            if "喜欢的事物" in content and ptype == "like":
                # 在喜欢的事物部分追加
                insert_pos = content.find("## 上下文")
                if insert_pos == -1:
                    insert_pos = len(content)

                new_section = f"\n- {item}（自动检测，{datetime.now().strftime('%Y-%m-%d')}）\n"
                content = content[:insert_pos] + new_section + content[insert_pos:]
                user_md.write_text(content, encoding="utf-8")

        except Exception as e:
            logger.warning(f"Failed to sync preference to USER.md: {e}")

    # =====================================================================
    # 协议二：任务完成后自动评估三问
    # =====================================================================

    def evaluate_task_completion(
        self,
        task_result: Dict[str, Any],
        conversation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """任务完成后自动评估三问

        1. 遇到新问题了吗？→ ERRORS.md
        2. 用户纠正我了吗？→ LEARNINGS.md
        3. 发现更好的方法了吗？→ LEARNINGS.md

        Returns:
            记录的经验条目列表
        """
        entries = []

        # 三问评估
        result = self._three_question_eval(task_result, conversation)

        if result.has_new_problem:
            entry = self._write_error_entry(result.new_problem_summary, task_result)
            if entry:
                entries.append(entry)

        if result.has_user_correction:
            entry = self._write_learning_entry(result.correction_summary, task_result, "correction")
            if entry:
                entries.append(entry)

        if result.has_better_method:
            entry = self._write_learning_entry(
                result.better_method_summary, task_result, "best_practice"
            )
            if entry:
                entries.append(entry)

        # 检查是否需要晋升
        if entries:
            promoted = self._check_and_promote()
            if promoted:
                logger.info(f"[Hermes evaluate] Promoted {len(promoted)} entries")

        return entries

    def _three_question_eval(
        self,
        task_result: Dict[str, Any],
        conversation: Optional[str] = None,
    ) -> ThreeQuestionResult:
        """执行三问评估"""
        result = ThreeQuestionResult()

        status = task_result.get("status", "unknown")
        error = task_result.get("error", "")
        feedback = task_result.get("user_feedback", "")
        output = task_result.get("output", "")

        # 合并评估文本
        eval_text = f"{error} {feedback} {output} {conversation or ''}".lower()

        # 问题1: 遇到新问题了吗？
        error_indicators = [
            "error",
            "failed",
            "exception",
            "崩溃",
            "报错",
            "出错",
            "新问题",
            "unexpected",
            "bug",
            "无法",
            "不能",
        ]
        for indicator in error_indicators:
            if indicator in eval_text:
                result.has_new_problem = True
                result.new_problem_summary = self._extract_summary(eval_text, indicator)
                break

        # 问题2: 用户纠正我了吗？
        correction_indicators = [
            "不对",
            "错了",
            "wrong",
            "incorrect",
            "应该是",
            "纠正",
            "correction",
            "不是",
            "no, ",
            "no.",
        ]
        for indicator in correction_indicators:
            if indicator in eval_text:
                result.has_user_correction = True
                result.correction_summary = self._extract_summary(eval_text, indicator)
                break

        # 问题3: 发现更好的方法了吗？
        improvement_indicators = [
            "更好",
            "better",
            "improved",
            "优化",
            "更高效",
            "改进",
            "optimize",
            "more efficient",
            "下次",
        ]
        for indicator in improvement_indicators:
            if indicator in eval_text:
                result.has_better_method = True
                result.better_method_summary = self._extract_summary(eval_text, indicator)
                break

        return result

    def _extract_summary(self, text: str, keyword: str) -> str:
        """从文本中提取摘要"""
        idx = text.find(keyword)
        if idx == -1:
            return text[:200]
        start = max(0, idx - 20)
        end = min(len(text), idx + 180)
        return text[start:end].strip()

    def _write_error_entry(
        self, summary: str, task_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """写入 ERRORS.md"""
        errors_file = self.learnings_dir / "ERRORS.md"
        entry = {
            "type": "error",
            "summary": summary,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "task_id": task_result.get("task_id", ""),
        }

        try:
            if not errors_file.exists():
                errors_file.write_text("# ERRORS.md — 错误记录\n\n", encoding="utf-8")

            with open(errors_file, "a", encoding="utf-8") as f:
                f.write(f"- [{entry['timestamp']}] {entry['summary']} (task: {entry['task_id']})\n")
            return entry
        except Exception as e:
            logger.error(f"Failed to write error entry: {e}")
            return None

    def _write_learning_entry(
        self,
        summary: str,
        task_result: Dict[str, Any],
        entry_type: str = "learning",
    ) -> Optional[Dict[str, Any]]:
        """写入 LEARNINGS.md"""
        learnings_file = self.learnings_dir / "LEARNINGS.md"
        entry = {
            "type": entry_type,
            "summary": summary,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "task_id": task_result.get("task_id", ""),
        }

        try:
            if not learnings_file.exists():
                learnings_file.write_text("# LEARNINGS.md — 学习记录\n\n", encoding="utf-8")

            with open(learnings_file, "a", encoding="utf-8") as f:
                prefix = "💡" if entry_type == "best_practice" else "🔧"
                f.write(
                    f"- [{entry['timestamp']}] {prefix} [{entry_type}] {entry['summary']}"
                    f" (task: {entry['task_id']})\n"
                )
            return entry
        except Exception as e:
            logger.error(f"Failed to write learning entry: {e}")
            return None

    def _check_and_promote(self) -> List[Dict[str, Any]]:
        """检查 .learnings 中的重复模式，≥3 次则晋升"""
        promoted = []
        errors_file = self.learnings_dir / "ERRORS.md"
        learnings_file = self.learnings_dir / "LEARNINGS.md"

        for source_file, target_doc in [
            (errors_file, "ERRORS.md"),
            (learnings_file, "LEARNINGS.md"),
        ]:
            if not source_file.exists():
                continue

            try:
                content = source_file.read_text(encoding="utf-8")
                lines = [l.strip() for l in content.split("\n") if l.strip().startswith("- [")]

                # 提取摘要并统计
                summaries: Dict[str, List[str]] = {}
                for line in lines:
                    # 提取摘要部分（时间戳之后）
                    match = re.search(r"\]\s*(.*?)\s*\(task:", line)
                    if match:
                        summary = match.group(1).strip()
                        # 去除 emoji 和类型标签
                        summary = re.sub(r"^[💡🔧]\s*\[\w+\]\s*", "", summary)
                        # 标准化（前50字符）
                        key = summary[:50].lower()
                        if key not in summaries:
                            summaries[key] = []
                        summaries[key].append(line)

                # 检查重复
                for key, occ_lines in summaries.items():
                    if len(occ_lines) >= 3:
                        promoted.append(
                            {
                                "pattern": key,
                                "count": len(occ_lines),
                                "source": target_doc,
                            }
                        )

            except Exception as e:
                logger.warning(f"Failed to check promotions in {source_file}: {e}")

        return promoted

    # =====================================================================
    # 协议五：心跳驱动的自动反思
    # =====================================================================

    def on_heartbeat(self) -> Optional[Dict[str, Any]]:
        """心跳触发：每 2 次心跳回顾最近任务，检查晋升

        Returns:
            反思结果摘要，如果没有需要处理的返回 None
        """
        self._heartbeat_count += 1

        # 每 2 次心跳执行一次反思
        if self._heartbeat_count % 2 != 0:
            return None

        reflection = {
            "timestamp": datetime.now().isoformat(),
            "heartbeat_count": self._heartbeat_count,
            "actions_taken": [],
        }

        # 1. 回顾最近 2 天的 memory 文件
        recent_memories = self._review_recent_memories(days=2)
        if recent_memories:
            reflection["actions_taken"].append(
                f"Reviewed {len(recent_memories)} recent memory files"
            )

        # 2. 检查 .learnings 晋升
        promoted = self._check_and_promote()
        if promoted:
            reflection["actions_taken"].append(
                f"Found {len(promoted)} patterns eligible for promotion"
            )

        # 3. 清理过期条目（简单实现）
        cleaned = self._cleanup_old_entries()
        if cleaned:
            reflection["actions_taken"].append(f"Cleaned {cleaned} old entries")

        if reflection["actions_taken"]:
            logger.info(f"[Hermes heartbeat] Reflection: {reflection}")
            return reflection

        return None

    def _review_recent_memories(self, days: int = 2) -> List[Path]:
        """回顾最近的 memory 文件"""
        recent = []
        today = datetime.now()

        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            memory_file = self.memory_dir / f"{date}.md"
            if memory_file.exists():
                recent.append(memory_file)

        return recent

    def _cleanup_old_entries(self) -> int:
        """清理超过 30 天的 .learnings 条目（简单实现）"""
        count = 0
        cutoff = datetime.now() - timedelta(days=30)

        for md_file in [
            self.learnings_dir / "ERRORS.md",
            self.learnings_dir / "LEARNINGS.md",
        ]:
            if not md_file.exists():
                continue

            try:
                content = md_file.read_text(encoding="utf-8")
                lines = content.split("\n")
                new_lines = []

                for line in lines:
                    # 检查时间戳
                    match = re.search(r"\[(\d{4}-\d{2}-\d{2})", line)
                    if match:
                        entry_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        if entry_date >= cutoff:
                            new_lines.append(line)
                        else:
                            count += 1
                    else:
                        new_lines.append(line)

                if len(new_lines) != len(lines):
                    md_file.write_text("\n".join(new_lines), encoding="utf-8")

            except Exception as e:
                logger.warning(f"Failed to cleanup {md_file}: {e}")

        return count

    # =====================================================================
    # 工具方法
    # =====================================================================

    def get_learnings_summary(self, days: int = 7) -> Dict[str, Any]:
        """获取 .learnings 摘要"""
        summary = {
            "errors": 0,
            "learnings": 0,
            "promotions": 0,
            "period_days": days,
        }

        errors_file = self.learnings_dir / "ERRORS.md"
        learnings_file = self.learnings_dir / "LEARNINGS.md"

        cutoff = datetime.now() - timedelta(days=days)

        for fpath, key in [(errors_file, "errors"), (learnings_file, "learnings")]:
            if not fpath.exists():
                continue

            try:
                content = fpath.read_text(encoding="utf-8")
                for line in content.split("\n"):
                    match = re.search(r"\[(\d{4}-\d{2}-\d{2})", line)
                    if match:
                        entry_date = datetime.strptime(match.group(1), "%Y-%m-%d")
                        if entry_date >= cutoff:
                            summary[key] += 1
            except Exception:
                pass

        return summary
