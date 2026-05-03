"""
ClawTeam 自主技能创建引擎 - P13 实现

核心功能：
1. 检测对话中的技能创建意图
2. 从 learnings 提取知识
3. 生成 SKILL.md
4. 注册到 SpectrAI
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class DetectedPattern(BaseModel):
    """检测到的模式"""

    pattern_id: str = Field(default_factory=lambda: f"pattern_{uuid.uuid4().hex[:8]}")
    name: str
    description: str
    trigger_count: int
    tools_used: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    estimated_savings: int = 0  # 预计节省步数
    confidence: float = 0.0
    first_detected: datetime = Field(default_factory=datetime.now)
    last_detected: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})


class SkillSpec(BaseModel):
    """技能规范"""

    name: str
    description: str
    version: str = "1.0.0"
    author: str = "ClawTeam Auto Creator"
    created_at: datetime = Field(default_factory=datetime.now)
    category: str = "automation"
    instructions: str
    inputs: List[Dict[str, Any]] = Field(default_factory=list)
    outputs: List[Dict[str, Any]] = Field(default_factory=list)
    references: Dict[str, str] = Field(default_factory=dict)
    templates: Dict[str, str] = Field(default_factory=dict)
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(json_encoders={datetime: lambda dt: dt.isoformat()})


class SkillUsageTracker:
    """技能使用追踪器"""

    def __init__(self, usage_dir: Optional[str] = None):
        self.usage_dir = Path(usage_dir or "~/.openclaw/workspace/skills/usage").expanduser()
        self.usage_dir.mkdir(parents=True, exist_ok=True)
        self._usage_data: Dict[str, List[Dict[str, Any]]] = {}
        self._load_usage_data()

    def _load_usage_data(self) -> None:
        """加载使用数据"""
        try:
            usage_files = list(self.usage_dir.glob("skill_usage_*.json"))
            for file_path in usage_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        skill_name = data.get("skill_name")
                        if skill_name:
                            if skill_name not in self._usage_data:
                                self._usage_data[skill_name] = []
                            self._usage_data[skill_name].append(data)
                except Exception as e:
                    logger.warning(f"Failed to load usage data from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading usage data: {e}")

    def _save_usage_record(self, record: Dict[str, Any]) -> None:
        """保存使用记录"""
        try:
            skill_name = record.get("skill_name", "unknown")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_path = self.usage_dir / f"skill_usage_{skill_name}_{timestamp}.json"

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save usage record: {e}")

    def record_skill_usage(
        self,
        skill_name: str,
        session_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        success: bool,
        duration_ms: int,
    ) -> None:
        """记录技能使用

        Args:
            skill_name: 技能名称
            session_id: 会话ID
            inputs: 输入参数
            outputs: 输出结果
            success: 是否成功
            duration_ms: 持续时间（毫秒）
        """
        record = {
            "skill_name": skill_name,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "inputs": inputs,
            "outputs": outputs,
            "success": success,
            "duration_ms": duration_ms,
        }

        # 添加到内存数据
        if skill_name not in self._usage_data:
            self._usage_data[skill_name] = []
        self._usage_data[skill_name].append(record)

        # 保存到文件
        self._save_usage_record(record)

        logger.debug(f"Recorded skill usage: {skill_name} (success: {success}, duration: {duration_ms}ms)")

    def get_skill_stats(self, skill_name: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """获取技能统计

        Args:
            skill_name: 技能名称，None 表示所有技能
            days: 过去多少天的数据

        Returns:
            统计信息字典
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        if skill_name:
            skill_names = [skill_name]
        else:
            skill_names = list(self._usage_data.keys())

        stats = {}
        for skill in skill_names:
            if skill not in self._usage_data:
                continue

            records = self._usage_data[skill]
            recent_records = [
                r for r in records if datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")) >= cutoff_date
            ]

            if not recent_records:
                continue

            success_count = sum(1 for r in recent_records if r["success"])
            total_count = len(recent_records)
            success_rate = success_count / total_count if total_count > 0 else 0

            avg_duration = sum(r["duration_ms"] for r in recent_records) / total_count if total_count > 0 else 0

            # 分析常用输入模式
            input_patterns = {}
            for r in recent_records:
                inputs_str = str(sorted(r["inputs"].items()))
                input_patterns[inputs_str] = input_patterns.get(inputs_str, 0) + 1

            stats[skill] = {
                "total_uses": total_count,
                "success_rate": success_rate,
                "avg_duration_ms": avg_duration,
                "success_count": success_count,
                "failure_count": total_count - success_count,
                "input_patterns": sorted(input_patterns.items(), key=lambda x: x[1], reverse=True)[:5],
                "first_use": min(r["timestamp"] for r in recent_records),
                "last_use": max(r["timestamp"] for r in recent_records),
            }

        return stats


class SkillAutoCreator:
    """自主技能创建引擎"""

    def __init__(self, skills_dir: Optional[str] = None):
        """初始化引擎

        Args:
            skills_dir: 技能存储目录，默认 ~/.openclaw/workspace/skills
        """
        self.skills_dir = Path(skills_dir or "~/.openclaw/workspace/skills").expanduser()
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.usage_tracker = SkillUsageTracker()
        self._patterns: Dict[str, DetectedPattern] = {}
        self._load_patterns()

    def _load_patterns(self) -> None:
        """加载已检测到的模式"""
        try:
            pattern_files = list(self.skills_dir.glob("patterns/pattern_*.json"))
            pattern_dir = self.skills_dir / "patterns"
            pattern_dir.mkdir(exist_ok=True)

            for file_path in pattern_files:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # 转换 ISO 格式时间字符串回 datetime
                        for key in ["first_detected", "last_detected"]:
                            if key in data and isinstance(data[key], str):
                                data[key] = datetime.fromisoformat(data[key].replace("Z", "+00:00"))
                        pattern = DetectedPattern(**data)
                        self._patterns[pattern.pattern_id] = pattern
                except Exception as e:
                    logger.warning(f"Failed to load pattern from {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")

    def _save_pattern(self, pattern: DetectedPattern) -> None:
        """保存模式到文件"""
        try:
            pattern_dir = self.skills_dir / "patterns"
            pattern_dir.mkdir(exist_ok=True)
            file_path = pattern_dir / f"pattern_{pattern.pattern_id}.json"

            with open(file_path, "w", encoding="utf-8") as f:
                data = pattern.model_dump()
                for key in ["first_detected", "last_detected"]:
                    if key in data and isinstance(data[key], datetime):
                        data[key] = data[key].isoformat()
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save pattern {pattern.pattern_id}: {e}")

    def detect_patterns_from_usage(
        self, min_occurrences: int = 5, min_confidence: float = 0.7
    ) -> List[DetectedPattern]:
        """从使用数据中检测模式

        Args:
            min_occurrences: 最小出现次数
            min_confidence: 最小置信度

        Returns:
            检测到的模式列表
        """
        # 获取所有技能的使用统计
        stats = self.usage_tracker.get_skill_stats(days=90)

        detected_patterns = []

        for skill_name, skill_stats in stats.items():
            total_uses = skill_stats.get("total_uses", 0)
            if total_uses < min_occurrences:
                continue

            input_patterns = skill_stats.get("input_patterns", [])

            # 检查是否有频繁使用的输入模式
            for inputs_str, count in input_patterns:
                if count >= min_occurrences:
                    # 分析输入模式以提取步骤
                    pattern = self._analyze_input_pattern(skill_name, inputs_str, count, skill_stats)
                    if pattern and pattern.confidence >= min_confidence:
                        detected_patterns.append(pattern)

        # 保存新检测到的模式
        for pattern in detected_patterns:
            if pattern.pattern_id not in self._patterns:
                self._patterns[pattern.pattern_id] = pattern
                self._save_pattern(pattern)

        return detected_patterns

    def _analyze_input_pattern(
        self, skill_name: str, inputs_str: str, count: int, skill_stats: Dict[str, Any]
    ) -> Optional[DetectedPattern]:
        """分析输入模式以创建模式对象"""
        try:
            # 解析输入字符串（简化实现）
            import ast

            inputs = {}
            try:
                # 尝试解析为字典
                inputs_dict = ast.literal_eval(inputs_str)
                if isinstance(inputs_dict, list):
                    for item in inputs_dict:
                        if isinstance(item, tuple) and len(item) == 2:
                            inputs[item[0]] = item[1]
            except:
                pass

            # 基于技能名称和输入推断模式
            pattern_name = f"{skill_name}_pattern_{count}_uses"
            description = f"检测到 {skill_name} 被使用了 {count} 次，具有相似的输入模式"

            # 提取使用的工具（从技能名称推断）
            tools_used = [skill_name]

            # 生成步骤描述
            steps = [
                f"调用 {skill_name} 技能",
                f"提供输入参数: {len(inputs)} 个参数",
                "处理并返回结果",
            ]

            # 计算预计节省步数（基于使用频率）
            estimated_savings = count * 3  # 假设每次节省3步

            # 计算置信度
            success_rate = skill_stats.get("success_rate", 0.0)
            confidence = min(0.9, success_rate * 0.8 + (count / 20.0))

            pattern = DetectedPattern(
                pattern_id=f"pattern_{uuid.uuid4().hex[:8]}",
                name=pattern_name,
                description=description,
                trigger_count=count,
                tools_used=tools_used,
                steps=steps,
                estimated_savings=estimated_savings,
                confidence=confidence,
                metadata={
                    "skill_name": skill_name,
                    "input_pattern": inputs_str,
                    "success_rate": success_rate,
                    "avg_duration_ms": skill_stats.get("avg_duration_ms", 0),
                },
            )

            return pattern

        except Exception as e:
            logger.warning(f"Failed to analyze input pattern: {e}")
            return None

    def detect_skill_creation_intent(self, conversation: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
        """检测对话中的技能创建意图

        Args:
            conversation: 对话历史，每个元素包含 "role" 和 "content"

        Returns:
            技能创建意图信息，如无意图则返回 None
        """
        # 合并对话内容
        full_text = "\n".join([msg["content"] for msg in conversation if "content" in msg]).lower()

        # 检测技能创建关键词
        skill_keywords = [
            "create a skill",
            "make a skill",
            "new skill",
            "automate this",
            "skill for",
            "save this as",
            "reusable",
            "template for",
            "每次都要",
            "重复操作",
            "自动化",
            "技能创建",
            "创建技能",
            "创建一个技能",
            "做成一个技能",
            "技能来",
            "自动创建",
        ]

        intent_detected = False
        for keyword in skill_keywords:
            if keyword in full_text:
                intent_detected = True
                break

        if not intent_detected:
            return None

        # 提取技能相关信息
        skill_info = {
            "intent_detected": True,
            "conversation_summary": full_text[:500] + "..." if len(full_text) > 500 else full_text,
            "detected_at": datetime.now().isoformat(),
            "confidence": 0.7,  # 基础置信度
        }

        # 尝试从对话中提取技能名称和描述
        # 查找包含 "skill" 或 "技能" 的句子
        lines = full_text.split("\n")
        for line in lines:
            if any(word in line for word in ["skill", "技能"]):
                # 尝试提取名称
                name_match = re.search(r"(?:skill|技能)[:\s]+(.+?)(?:\.|$)", line)
                if name_match:
                    skill_info["potential_name"] = name_match.group(1).strip()
                    skill_info["confidence"] += 0.1

        return skill_info

    def create_skill_from_pattern(self, pattern: DetectedPattern, confirm: bool = True) -> Optional[SkillSpec]:
        """基于模式创建技能

        Args:
            pattern: 检测到的模式
            confirm: 是否需要确认

        Returns:
            创建的技能规范
        """
        try:
            # 基于模式生成技能名称
            skill_name = pattern.name.replace("_pattern", "").replace("_", "-")

            # 生成技能描述
            description = f"自动化技能：{pattern.description}"

            # 生成指令
            instructions = f"""# {skill_name}

## 用途
{pattern.description}

## 使用方法
"""
            for i, step in enumerate(pattern.steps, 1):
                instructions += f"{i}. {step}\n"

            instructions += f"\n## 预计节省\n预计每次使用可节省 {pattern.estimated_savings} 步操作。"

            # 定义输入参数
            inputs = []
            if pattern.metadata.get("input_pattern"):
                # 从元数据中提取输入参数
                inputs.append(
                    {
                        "name": "input_data",
                        "type": "string",
                        "description": "输入数据",
                        "required": True,
                    }
                )
            else:
                # 默认输入参数
                inputs.append({"name": "task", "type": "string", "description": "任务描述", "required": True})

            # 定义输出
            outputs = [{"name": "result", "type": "string", "description": "执行结果"}]

            # 添加示例
            examples = [{"input": {"task": "执行自动化任务"}, "output": {"result": "任务执行成功"}}]

            spec = SkillSpec(
                name=skill_name,
                description=description,
                instructions=instructions,
                inputs=inputs,
                outputs=outputs,
                examples=examples,
                metadata={
                    "created_from_pattern": pattern.pattern_id,
                    "tools_used": pattern.tools_used,
                    "estimated_savings": pattern.estimated_savings,
                    "confidence": pattern.confidence,
                },
            )

            logger.info(f"Created skill spec from pattern: {skill_name}")
            return spec

        except Exception as e:
            logger.error(f"Failed to create skill from pattern: {e}")
            return None

    def create_skill_from_conversation(
        self, conversation: List[Dict[str, str]], learnings_context: Optional[str] = None
    ) -> Optional[SkillSpec]:
        """基于对话内容创建技能

        Args:
            conversation: 对话历史
            learnings_context: 从 learnings 系统获取的上下文

        Returns:
            创建的技能规范
        """
        # 检测技能创建意图
        intent = self.detect_skill_creation_intent(conversation)
        if not intent:
            return None

        # 从对话中提取技能信息
        full_text = "\n".join([msg["content"] for msg in conversation if "content" in msg])

        # 提取技能名称
        skill_name = intent.get("potential_name", "auto-generated-skill")
        # 清理名称
        skill_name = re.sub(r"[^a-zA-Z0-9-_]", "-", skill_name).lower()

        # 生成技能描述（从对话中提取）
        description_match = re.search(r"(?:description|描述)[:\s]+(.+?)(?:\n|$)", full_text, re.IGNORECASE)
        description = (
            description_match.group(1).strip() if description_match else f"基于对话自动创建的技能: {skill_name}"
        )

        # 生成指令
        instructions = f"""# {skill_name}

## 用途
{description}

## 上下文
基于以下对话自动创建：
{full_text[:1000]}{"..." if len(full_text) > 1000 else ""}

"""

        # 如果有 learnings 上下文，添加进去
        if learnings_context:
            instructions += f"\n## 相关经验\n{learnings_context}\n"

        # 添加使用说明
        instructions += """
## 使用方法
1. 调用此技能时提供必要的输入参数
2. 技能会根据对话中展示的模式执行相应操作
3. 返回执行结果

## 注意事项
- 此技能为自动生成，可能需要进一步优化
- 使用前请验证功能的正确性
"""

        # 定义输入参数
        inputs = [{"name": "input", "type": "string", "description": "输入参数", "required": True}]

        # 定义输出
        outputs = [{"name": "result", "type": "string", "description": "执行结果"}]

        spec = SkillSpec(
            name=skill_name,
            description=description,
            instructions=instructions,
            inputs=inputs,
            outputs=outputs,
            examples=[{"input": {"input": "测试输入"}, "output": {"result": "测试输出"}}],
            metadata={
                "created_from_conversation": True,
                "conversation_summary": intent.get("conversation_summary", ""),
                "detected_at": intent.get("detected_at", ""),
            },
        )

        logger.info(f"Created skill spec from conversation: {skill_name}")
        return spec

    def install_skill(self, spec: SkillSpec, force: bool = False) -> Path:
        """安装技能到技能目录

        Args:
            spec: 技能规范
            force: 是否强制覆盖

        Returns:
            技能文件路径
        """
        try:
            # 创建技能目录
            skill_dir = self.skills_dir / spec.name
            if skill_dir.exists() and not force:
                raise FileExistsError(f"Skill directory already exists: {skill_dir}")

            skill_dir.mkdir(exist_ok=True)

            # 生成 SKILL.md 内容
            skill_md = f"""# {spec.name}

**版本**: {spec.version}
**作者**: {spec.author}
**创建时间**: {spec.created_at.strftime("%Y-%m-%d %H:%M:%S")}
**分类**: {spec.category}

## 描述
{spec.description}

## 使用说明
{spec.instructions}

## 输入参数
"""
            for input_def in spec.inputs:
                skill_md += f"- **{input_def['name']}** ({input_def.get('type', 'string')})"
                if input_def.get("required", False):
                    skill_md += " [必需]"
                skill_md += f": {input_def.get('description', '')}\n"

            skill_md += "\n## 输出结果\n"
            for output_def in spec.outputs:
                skill_md += f"- **{output_def['name']}** ({output_def.get('type', 'string')}): {output_def.get('description', '')}\n"

            if spec.examples:
                skill_md += "\n## 示例\n"
                for i, example in enumerate(spec.examples, 1):
                    skill_md += f"\n### 示例 {i}\n"
                    skill_md += f"**输入**:\n```json\n{json.dumps(example.get('input', {}), ensure_ascii=False, indent=2)}\n```\n"
                    skill_md += f"**输出**:\n```json\n{json.dumps(example.get('output', {}), ensure_ascii=False, indent=2)}\n```\n"

            if spec.references:
                skill_md += "\n## 参考\n"
                for ref_name, ref_url in spec.references.items():
                    skill_md += f"- [{ref_name}]({ref_url})\n"

            if spec.metadata:
                skill_md += "\n## 元数据\n"
                skill_md += f"```json\n{json.dumps(spec.metadata, ensure_ascii=False, indent=2)}\n```\n"

            # 写入 SKILL.md
            skill_md_path = skill_dir / "SKILL.md"
            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(skill_md)

            # 保存技能规范
            spec_path = skill_dir / "spec.json"
            with open(spec_path, "w", encoding="utf-8") as f:
                spec_dict = spec.model_dump()
                # 处理 datetime 字段
                for key in ["created_at"]:
                    if key in spec_dict and isinstance(spec_dict[key], datetime):
                        spec_dict[key] = spec_dict[key].isoformat()
                json.dump(spec_dict, f, ensure_ascii=False, indent=2)

            logger.info(f"Installed skill: {spec.name} at {skill_md_path}")
            return skill_md_path

        except Exception as e:
            logger.error(f"Failed to install skill {spec.name}: {e}")
            raise

    def evaluate_existing_skills(self) -> List[Dict[str, Any]]:
        """评估现有技能效果

        Returns:
            技能评估结果列表
        """
        evaluations = []

        # 获取技能使用统计
        stats = self.usage_tracker.get_skill_stats(days=90)

        # 检查每个技能目录
        skill_dirs = [d for d in self.skills_dir.iterdir() if d.is_dir()]

        for skill_dir in skill_dirs:
            skill_name = skill_dir.name
            skill_stats = stats.get(skill_name, {})

            # 检查是否有 SKILL.md
            skill_md_path = skill_dir / "SKILL.md"
            has_skill_md = skill_md_path.exists()

            # 检查是否有 spec.json
            spec_path = skill_dir / "spec.json"
            has_spec = spec_path.exists()

            # 计算评估分数
            score = 0
            feedback = []

            if has_skill_md:
                score += 30
                feedback.append("✓ 有 SKILL.md 文档")
            else:
                feedback.append("✗ 缺少 SKILL.md 文档")

            if has_spec:
                score += 20
                feedback.append("✓ 有规范文件")
            else:
                feedback.append("✗ 缺少规范文件")

            if skill_stats:
                uses = skill_stats.get("total_uses", 0)
                success_rate = skill_stats.get("success_rate", 0)

                if uses > 0:
                    score += min(30, uses * 2)  # 最多30分
                    feedback.append(f"✓ 有使用记录 ({uses} 次)")

                if success_rate > 0.8:
                    score += 20
                    feedback.append(f"✓ 成功率良好 ({success_rate:.1%})")
                elif success_rate > 0.5:
                    score += 10
                    feedback.append(f"⚠ 成功率一般 ({success_rate:.1%})")
                else:
                    feedback.append(f"✗ 成功率较低 ({success_rate:.1%})")
            else:
                feedback.append("⚠ 无使用记录")

            evaluations.append(
                {
                    "skill_name": skill_name,
                    "score": score,
                    "feedback": feedback,
                    "stats": skill_stats,
                    "has_skill_md": has_skill_md,
                    "has_spec": has_spec,
                }
            )

        # 按分数排序
        evaluations.sort(key=lambda x: x["score"], reverse=True)
        return evaluations

    def optimize_skill(self, skill_name: str, based_on_feedback: Optional[List[Dict[str, Any]]] = None) -> bool:
        """优化技能

        Args:
            skill_name: 技能名称
            based_on_feedback: 基于反馈数据进行优化

        Returns:
            是否优化成功
        """
        try:
            skill_dir = self.skills_dir / skill_name
            if not skill_dir.exists():
                logger.warning(f"Skill directory not found: {skill_dir}")
                return False

            # 读取现有规范
            spec_path = skill_dir / "spec.json"
            if not spec_path.exists():
                logger.warning(f"Skill spec not found: {spec_path}")
                return False

            with open(spec_path, "r", encoding="utf-8") as f:
                spec_data = json.load(f)

            # 应用优化
            updated = False

            # 如果有反馈数据，基于反馈优化
            if based_on_feedback:
                # 分析常见问题并优化
                for feedback_item in based_on_feedback:
                    issue = feedback_item.get("issue", "")
                    suggestion = feedback_item.get("suggestion", "")

                    if "输入参数" in issue or "input" in issue.lower():
                        # 优化输入参数描述
                        updated = True
                        spec_data["description"] += f"\n\n优化说明: {suggestion}"

            # 更新版本号
            if "version" in spec_data:
                current_version = spec_data["version"]
                try:
                    # 增加修订版本号
                    import re

                    version_match = re.match(r"(\d+)\.(\d+)\.(\d+)", current_version)
                    if version_match:
                        major, minor, patch = map(int, version_match.groups())
                        spec_data["version"] = f"{major}.{minor}.{patch + 1}"
                        updated = True
                except:
                    pass

            # 保存更新后的规范
            if updated:
                with open(spec_path, "w", encoding="utf-8") as f:
                    json.dump(spec_data, f, ensure_ascii=False, indent=2)

                logger.info(f"Optimized skill: {skill_name}")
                return True
            else:
                logger.info(f"No optimization needed for skill: {skill_name}")
                return True

        except Exception as e:
            logger.error(f"Failed to optimize skill {skill_name}: {e}")
            return False

    def get_skill_metrics(
        self, skill_name: str, time_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """获取技能使用指标

        Args:
            skill_name: 技能名称
            time_range: 时间范围

        Returns:
            技能指标数据
        """
        # 获取技能使用统计
        all_stats = self.usage_tracker.get_skill_stats(days=365)  # 获取一年数据

        if skill_name not in all_stats:
            return {"error": "Skill not found or no usage data"}

        skill_stats = all_stats[skill_name]

        # 如果有时间范围，过滤数据
        if time_range:
            start_time, end_time = time_range
            # 这里简化实现，实际需要从原始记录中过滤
            pass

        # 计算额外指标
        total_uses = skill_stats.get("total_uses", 0)
        success_rate = skill_stats.get("success_rate", 0)
        avg_duration = skill_stats.get("avg_duration_ms", 0)

        # 计算效率指标
        efficiency_score = 0
        if total_uses > 0:
            # 基于成功率和使用频率计算效率
            efficiency_score = min(100, success_rate * 100 + min(40, total_uses / 10.0))

        metrics = {
            "skill_name": skill_name,
            "total_uses": total_uses,
            "success_rate": success_rate,
            "avg_duration_ms": avg_duration,
            "success_count": skill_stats.get("success_count", 0),
            "failure_count": skill_stats.get("failure_count", 0),
            "efficiency_score": efficiency_score,
            "input_patterns": skill_stats.get("input_patterns", []),
            "first_use": skill_stats.get("first_use", ""),
            "last_use": skill_stats.get("last_use", ""),
            "time_saved_minutes": skill_stats.get("estimated_savings", 0) * total_uses / 10.0,  # 估算节省时间
        }

        return metrics

    def list_skills(self) -> List[str]:
        """列出所有技能

        Returns:
            技能名称列表
        """
        skill_dirs = [d for d in self.skills_dir.iterdir() if d.is_dir()]
        return [d.name for d in skill_dirs]

    def get_skill_info(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """获取技能详细信息

        Args:
            skill_name: 技能名称

        Returns:
            技能信息字典
        """
        skill_dir = self.skills_dir / skill_name
        if not skill_dir.exists():
            return None

        info = {
            "name": skill_name,
            "directory": str(skill_dir),
            "has_skill_md": (skill_dir / "SKILL.md").exists(),
            "has_spec": (skill_dir / "spec.json").exists(),
            "created_at": None,
            "metrics": self.get_skill_metrics(skill_name),
        }

        # 尝试从 spec.json 获取创建时间
        spec_path = skill_dir / "spec.json"
        if spec_path.exists():
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec_data = json.load(f)
                    if "created_at" in spec_data:
                        info["created_at"] = spec_data["created_at"]
            except:
                pass

        return info
