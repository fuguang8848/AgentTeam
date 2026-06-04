"""
AgentTeam .learnings 自动闭环系统测试

测试 P12 实现：
- .learnings 文件格式解析
- 错误/修正/技巧自动提取
- 结构化存储
- 与 session 关联
- 查询/回放
- 应用到新任务上下文注入
- 去重/合并/优先级排序
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from agentteam.learnings.auto_capture import (
    LearningType,
    ExperienceEntry,
    AutoCaptureEngine,
    PatternDetector
)


class TestLearningType:
    """测试学习类型枚举"""
    
    def test_learning_type_values(self):
        """测试枚举值"""
        assert LearningType.ERROR.value == "error"
        assert LearningType.LEARNING.value == "learning"
        assert LearningType.BEST_PRACTICE.value == "best_practice"
        assert LearningType.FEATURE_REQUEST.value == "feature_request"
        assert LearningType.KNOWLEDGE_GAP.value == "knowledge_gap"
        
    def test_learning_type_iteration(self):
        """测试枚举迭代"""
        types = list(LearningType)
        assert len(types) == 5
        assert all(isinstance(t, LearningType) for t in types)


class TestExperienceEntry:
    """测试经验条目"""
    
    def test_experience_entry_creation(self):
        """测试创建经验条目"""
        entry = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="测试错误",
            details="这是一个测试错误详情",
            category="correction",
            area="backend",
            priority="high"
        )
        
        assert entry.entry_type == LearningType.ERROR
        assert entry.summary == "测试错误"
        assert entry.details == "这是一个测试错误详情"
        assert entry.category == "correction"
        assert entry.area == "backend"
        assert entry.priority == "high"
        assert entry.count == 1
        assert not entry.resolved
        assert entry.resolution is None
        
    def test_experience_entry_defaults(self):
        """测试默认值"""
        entry = ExperienceEntry(
            entry_type=LearningType.BEST_PRACTICE,
            summary="最佳实践测试"
        )
        
        assert entry.entry_id.startswith("exp_")
        assert entry.first_seen is not None
        assert entry.last_seen is not None
        assert entry.tags == []
        assert entry.occurrences == []
        assert entry.session_ids == []
        assert entry.related_task_ids == []
        
    def test_experience_entry_json_serialization(self):
        """测试 JSON 序列化"""
        entry = ExperienceEntry(
            entry_type=LearningType.LEARNING,
            summary="学习测试"
        )
        
        # 转换为字典
        data = entry.model_dump(mode="json")
        
        assert data["entry_type"] == "learning"
        assert data["summary"] == "学习测试"
        assert "entry_id" in data
        assert "first_seen" in data
        assert "last_seen" in data
        
        # 测试 ISO 格式时间字符串
        assert isinstance(data["first_seen"], str) or isinstance(data["first_seen"], datetime)
        assert isinstance(data["last_seen"], str) or isinstance(data["last_seen"], datetime)


class TestPatternDetector:
    """测试模式检测器"""
    
    def test_detect_repetitive_patterns(self):
        """测试检测重复模式"""
        detector = PatternDetector()
        
        # 创建测试活动数据
        activities = []
        for i in range(15):
            activity = {
                "index": i,
                "status": "success" if i % 3 != 0 else "error",
                "error_type": "timeout" if i % 3 == 0 else None,
                "tool": "bash" if i < 10 else "python"
            }
            activities.append(activity)
        
        patterns = detector.detect_repetitive_patterns(activities, window_size=10)
        
        # 应该检测到一些模式
        assert isinstance(patterns, list)
        
        # 检查模式类型
        pattern_types = [p["type"] for p in patterns]
        assert "error_cluster" in pattern_types or "tool_pattern" in pattern_types
        
    def test_calculate_pattern_confidence(self):
        """测试计算模式置信度"""
        detector = PatternDetector()
        
        # 测试错误集群模式
        error_pattern = {
            "type": "error_cluster",
            "error_types": ["timeout"]
        }
        
        confidence = detector.calculate_pattern_confidence(error_pattern, [])
        assert 0.0 <= confidence <= 1.0
        
        # 测试工具模式
        tool_pattern = {
            "type": "tool_pattern",
            "tools": ["bash"]
        }
        
        confidence = detector.calculate_pattern_confidence(tool_pattern, [])
        assert 0.0 <= confidence <= 1.0
        
    def test_pattern_detection_with_empty_data(self):
        """测试空数据模式检测"""
        detector = PatternDetector()
        
        patterns = detector.detect_repetitive_patterns([], window_size=10)
        assert patterns == []
        
        patterns = detector.detect_repetitive_patterns([{"status": "success"}], window_size=10)
        assert patterns == []


class TestAutoCaptureEngine:
    """测试自动经验捕获引擎"""
    
    @pytest.fixture
    def temp_learnings_dir(self):
        """创建临时学习目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def engine(self, temp_learnings_dir):
        """创建测试引擎实例"""
        return AutoCaptureEngine(learnings_dir=str(temp_learnings_dir))
    
    def test_engine_initialization(self, engine, temp_learnings_dir):
        """测试引擎初始化"""
        assert engine.learnings_dir == temp_learnings_dir
        assert engine.learnings_dir.exists()
        assert isinstance(engine.pattern_detector, PatternDetector)
        assert isinstance(engine._experiences, dict)
        
    def test_evaluate_task_result_success(self, engine):
        """测试评估成功任务结果"""
        task_result = {
            "status": "success",
            "task_id": "test-task-123",
            "session_id": "test-session-456",
            "time_saved_minutes": 45,
            "method": "高效方法"
        }
        
        entry = engine.evaluate_task_result(task_result)
        # 成功且节省时间多的任务应该生成最佳实践
        assert entry is not None
        assert entry.entry_type == LearningType.BEST_PRACTICE
        assert "节省" in entry.summary
        assert "test-task-123" in entry.details
        
    def test_evaluate_task_result_failure(self, engine):
        """测试评估失败任务结果"""
        task_result = {
            "status": "failed",
            "error": "任务执行超时",
            "task_id": "test-task-123",
            "session_id": "test-session-456"
        }
        
        entry = engine.evaluate_task_result(task_result)
        assert entry is not None
        assert entry.entry_type == LearningType.ERROR
        assert "任务失败" in entry.summary or "超时" in entry.summary
        assert entry.priority in ["medium", "high"]
        assert "test-task-123" in entry.details
        
    def test_evaluate_task_result_with_feedback(self, engine):
        """测试带用户反馈的任务评估"""
        task_result = {
            "status": "success",
            "task_id": "test-task-123",
            "session_id": "test-session-456"
        }
        
        user_feedback = "这个结果很好！不错！优秀！"
        
        entry = engine.evaluate_task_result(task_result, user_feedback)
        assert entry is not None
        assert entry.entry_type == LearningType.BEST_PRACTICE
        assert "用户反馈" in entry.details
        
    def test_detect_area(self, engine):
        """测试检测任务领域"""
        # 测试前端任务
        frontend_task = {
            "tools_used": ["html", "css", "javascript"],
            "description": "创建React组件"
        }
        area = engine._detect_area(frontend_task)
        assert area == "frontend"
        
        # 测试后端任务
        backend_task = {
            "tools_used": ["python", "api", "database"],
            "description": "实现REST API"
        }
        area = engine._detect_area(backend_task)
        assert area == "backend"
        
        # 测试测试任务
        test_task = {
            "tools_used": ["pytest", "test"],
            "description": "编写测试用例"
        }
        area = engine._detect_area(test_task)
        assert area == "tests"
        
        # 测试通用任务
        general_task = {
            "tools_used": [],
            "description": "常规任务"
        }
        area = engine._detect_area(general_task)
        assert area == "general"
        
    def test_record_experience_new(self, engine, temp_learnings_dir):
        """测试记录新经验"""
        entry = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="新错误",
            details="这是一个新错误",
            area="backend"
        )
        
        entry_id = engine.record_experience(entry)
        assert entry_id == entry.entry_id
        
        # 检查文件是否创建
        entry_file = temp_learnings_dir / f"experience_{entry_id}.json"
        assert entry_file.exists()
        
        # 检查内容
        with open(entry_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
            assert saved_data["entry_id"] == entry_id
            assert saved_data["summary"] == "新错误"
            
    def test_record_experience_merge(self, engine):
        """测试合并相似经验"""
        # 创建第一个经验条目
        entry1 = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="相同的错误",
            details="错误详情1",
            area="backend",
            session_ids=["session1"]
        )
        
        entry1_id = engine.record_experience(entry1)
        
        # 创建相似的第二个经验条目
        entry2 = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="相同的错误",  # 相同摘要
            details="错误详情2",
            area="backend",  # 相同领域
            session_ids=["session2"]
        )
        
        entry2_id = engine.record_experience(entry2)
        
        # 应该合并到第一个条目
        assert entry2_id == entry1_id
        
        # 检查计数增加
        merged_entry = engine._experiences[entry1_id]
        assert merged_entry.count == 2
        assert set(merged_entry.session_ids) == {"session1", "session2"}
        
    def test_calculate_similarity(self, engine):
        """测试计算文本相似度"""
        similarity = engine._calculate_similarity("hello world", "hello world")
        assert similarity == 1.0
        
        similarity = engine._calculate_similarity("hello world", "hello there")
        assert 0.0 < similarity < 1.0
        
        similarity = engine._calculate_similarity("hello world", "goodbye world")
        assert 0.0 < similarity < 1.0
        
        similarity = engine._calculate_similarity("hello", "")
        assert similarity == 0.0
        
        similarity = engine._calculate_similarity("", "world")
        assert similarity == 0.0
        
    def test_check_for_promotion(self, engine):
        """测试检查晋升"""
        # 创建一些经验条目
        for i in range(5):
            entry = ExperienceEntry(
                entry_type=LearningType.BEST_PRACTICE if i % 2 == 0 else LearningType.ERROR,
                summary=f"经验{i}",
                details=f"详情{i}",
                count=4 if i % 2 == 0 else 2,  # 最佳实践出现4次，错误出现2次
                area="backend"
            )
            engine.record_experience(entry)
        
        candidates = engine.check_for_promotion(min_occurrences=3, min_confidence=0.8)
        
        # 应该找到出现3次以上的最佳实践
        assert isinstance(candidates, list)
        assert len(candidates) >= 1
        
        for candidate in candidates:
            assert candidate.count >= 3
            assert not candidate.resolved
            
    def test_search_experiences(self, engine):
        """测试搜索经验"""
        # 创建测试经验
        entries = [
            ExperienceEntry(
                entry_type=LearningType.ERROR,
                summary="数据库连接错误",
                details="无法连接MySQL数据库",
                area="backend",
                tags=["database", "mysql"]
            ),
            ExperienceEntry(
                entry_type=LearningType.BEST_PRACTICE,
                summary="前端性能优化",
                details="使用虚拟滚动优化列表性能",
                area="frontend",
                tags=["performance", "react"]
            ),
            ExperienceEntry(
                entry_type=LearningType.LEARNING,
                summary="Python异步编程",
                details="asyncio最佳实践",
                area="backend",
                tags=["python", "async"]
            )
        ]
        
        for entry in entries:
            engine.record_experience(entry)
        
        # 搜索数据库相关经验
        results = engine.search_experiences("数据库", limit=10)
        assert len(results) >= 1
        assert any("数据库" in r.summary for r in results)
        
        # 搜索后端相关经验
        results = engine.search_experiences("backend", limit=10)
        assert len(results) >= 2
        
        # 按类型过滤搜索
        results = engine.search_experiences("优化", entry_type=LearningType.BEST_PRACTICE, limit=10)
        assert len(results) >= 1
        assert all(r.entry_type == LearningType.BEST_PRACTICE for r in results)
        
    def test_generate_learning_summary(self, engine):
        """测试生成学习摘要"""
        # 创建一些近期经验
        recent_entry = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="近期错误",
            details="今天发生的错误",
            priority="high"
        )
        engine.record_experience(recent_entry)
        
        # 生成摘要
        summary = engine.generate_learning_summary(days=7, format="markdown")
        assert isinstance(summary, str)
        assert "学习摘要" in summary
        assert "近期错误" in summary
        
        # 测试 JSON 格式
        json_summary = engine.generate_learning_summary(days=7, format="json")
        assert isinstance(json_summary, str)
        data = json.loads(json_summary)
        assert "total_entries" in data
        assert "statistics" in data
        
        # 测试文本格式
        text_summary = engine.generate_learning_summary(days=7, format="text")
        assert isinstance(text_summary, str)
        assert "AgentTeam" in text_summary or "学习摘要" in text_summary
        
    def test_get_context_for_task(self, engine):
        """测试为任务获取上下文"""
        # 创建相关经验
        entry = ExperienceEntry(
            entry_type=LearningType.BEST_PRACTICE,
            summary="API设计最佳实践",
            details="REST API设计规范",
            area="backend",
            tags=["api", "rest", "design"]
        )
        engine.record_experience(entry)
        
        # 获取相关任务上下文 — use a query that matches the entry summary
        context = engine.get_context_for_task("API设计", max_entries=3)
        assert isinstance(context, str)
        assert "API设计" in context
        
    def test_list_experiences(self, engine):
        """测试列出经验"""
        # 创建不同类型和状态的经验
        entries = [
            ExperienceEntry(
                entry_type=LearningType.ERROR,
                summary="错误1",
                details="未解决的错误",
                area="backend",
                resolved=False
            ),
            ExperienceEntry(
                entry_type=LearningType.BEST_PRACTICE,
                summary="最佳实践1",
                details="已解决的最佳实践",
                area="frontend",
                resolved=True
            ),
            ExperienceEntry(
                entry_type=LearningType.ERROR,
                summary="错误2",
                details="另一个错误",
                area="infra",
                resolved=False
            )
        ]
        
        for entry in entries:
            engine.record_experience(entry)
        
        # 列出所有经验
        all_entries = engine.list_experiences()
        assert len(all_entries) >= 3
        
        # 按类型过滤
        error_entries = engine.list_experiences(entry_type=LearningType.ERROR)
        assert all(e.entry_type == LearningType.ERROR for e in error_entries)
        
        # 按解决状态过滤
        unresolved_entries = engine.list_experiences(resolved=False)
        assert all(not e.resolved for e in unresolved_entries)
        
        # 按领域过滤
        backend_entries = engine.list_experiences(area="backend")
        assert all(e.area == "backend" for e in backend_entries)
        
    def test_mark_as_resolved(self, engine):
        """测试标记为已解决"""
        entry = ExperienceEntry(
            entry_type=LearningType.ERROR,
            summary="待解决错误",
            details="需要解决的错误"
        )
        
        entry_id = engine.record_experience(entry)
        
        # 标记为已解决
        result = engine.mark_as_resolved(entry_id, "已通过更新修复")
        assert result is True
        
        # 检查状态更新
        updated_entry = engine._experiences[entry_id]
        assert updated_entry.resolved is True
        assert updated_entry.resolution == "已通过更新修复"
        
        # 测试不存在的条目
        result = engine.mark_as_resolved("nonexistent", "修复")
        assert result is False
        
    def test_promote_to_documentation(self, engine, temp_learnings_dir):
        """测试晋升到文档系统"""
        entry = ExperienceEntry(
            entry_type=LearningType.BEST_PRACTICE,
            summary="重要最佳实践",
            details="应该记录到文档中",
            count=5,
            priority="high"
        )
        
        engine.record_experience(entry)
        
        # 晋升到 AGENTS.md
        result = engine.promote_to_documentation(entry, "AGENTS.md")
        assert result is True
        
        # 检查文档是否创建
        doc_path = temp_learnings_dir.parent / "AGENTS.md"
        assert doc_path.exists()
        
        # 检查文档内容
        with open(doc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "重要最佳实践" in content
            assert "best_practice" in content
            
        # 检查条目标记为已解决
        assert entry.resolved is True
        assert "已晋升到 AGENTS.md" in entry.resolution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])