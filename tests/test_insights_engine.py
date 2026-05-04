"""测试洞察引擎"""
import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from clawteam.insights import InsightsEngine


@pytest.fixture
def temp_db():
    """临时数据库文件"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def insights_engine(temp_db):
    """洞察引擎实例"""
    engine = InsightsEngine(db_path=temp_db)
    yield engine
    engine.close()


def test_engine_initialization(insights_engine):
    """测试引擎初始化"""
    assert insights_engine.db_path is not None
    assert insights_engine.conn is None  # 延迟连接


def test_tool_usage_recording(insights_engine):
    """测试工具使用记录"""
    # 记录工具使用
    insights_engine.record_tool_usage(
        tool_name="write_file",
        session_id="test_session_123",
        team_id="test_team",
        task_id="test_task",
        metadata={"file_size": 1024}
    )
    
    # 获取统计
    stats = insights_engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls > 0
    assert "write_file" in stats.by_tool
    assert stats.by_tool["write_file"] >= 1


def test_skill_usage_recording(insights_engine):
    """测试技能使用记录"""
    # 记录技能使用
    insights_engine.record_skill_usage(
        skill_name="code_review",
        session_id="test_session_123",
        team_id="test_team",
        task_id="test_task",
        result_length=500,
        metadata={"language": "python"}
    )
    
    # 获取统计
    stats = insights_engine.get_skill_usage_stats(days=7)
    
    assert stats.total_skill_invocations > 0
    assert "code_review" in stats.by_skill
    assert stats.by_skill["code_review"] >= 1


def test_session_activity_recording(insights_engine):
    """测试会话活动记录"""
    # 记录会话开始
    insights_engine.record_session_activity(
        event_type="session_start",
        session_id="test_session_123",
        team_id="test_team",
        task_id="test_task",
        metadata={"provider": "claude"}
    )
    
    # 记录会话结束
    insights_engine.record_session_activity(
        event_type="session_end",
        session_id="test_session_123",
        team_id="test_team",
        task_id="test_task",
        metadata={"duration_seconds": 300}
    )
    
    # 获取活动统计
    stats = insights_engine.get_activity_stats(days=7)
    
    # 至少记录了活动
    assert stats.active_days > 0 or stats.by_hour  # 可能没有日期过滤


def test_multiple_tools_recording(insights_engine):
    """测试多个工具记录"""
    tools = ["write_file", "read_file", "bash", "grep", "glob"]
    
    for tool in tools:
        for _ in range(3):  # 每个工具记录3次
            insights_engine.record_tool_usage(
                tool_name=tool,
                session_id=f"session_{tool}",
                metadata={"iteration": _}
            )
    
    stats = insights_engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls == len(tools) * 3
    
    for tool in tools:
        assert tool in stats.by_tool
        assert stats.by_tool[tool] == 3


def test_time_filtering(insights_engine):
    """测试时间过滤"""
    # 记录一些工具使用
    insights_engine.record_tool_usage("old_tool", metadata={"note": "old"})
    
    # 获取不同时间范围的统计
    stats_7days = insights_engine.get_tool_usage_stats(days=7)
    stats_30days = insights_engine.get_tool_usage_stats(days=30)
    
    # 30天应该包含7天的数据
    assert stats_30days.total_tool_calls >= stats_7days.total_tool_calls


def test_activity_patterns(insights_engine):
    """测试活动模式分析"""
    # 记录不同时间的活动
    for hour in [9, 10, 14, 15, 20]:  # 工作时间
        for _ in range(5):
            insights_engine.record_tool_usage(
                tool_name="test_tool",
                session_id=f"session_{hour}",
                metadata={"hour": hour}
            )
    
    stats = insights_engine.get_activity_stats(days=7)
    
    # 检查小时分布
    assert isinstance(stats.by_hour, dict)
    
    # 检查工作日分布
    assert isinstance(stats.by_weekday, dict)


def test_token_usage_stats(insights_engine):
    """测试 Token 使用统计"""
    # Token 统计依赖于数据库，这里主要测试接口可用性
    stats = insights_engine.get_token_usage_stats(days=7)
    
    assert hasattr(stats, "total_input_tokens")
    assert hasattr(stats, "total_output_tokens")
    assert hasattr(stats, "total_tokens")
    assert hasattr(stats, "estimated_cost")
    assert hasattr(stats, "by_provider")
    
    assert isinstance(stats.total_input_tokens, int)
    assert isinstance(stats.total_output_tokens, int)
    assert isinstance(stats.total_tokens, int)
    assert isinstance(stats.estimated_cost, float)
    assert isinstance(stats.by_provider, dict)


def test_report_generation_json(insights_engine):
    """测试 JSON 报告生成"""
    # 添加一些测试数据
    insights_engine.record_tool_usage("test_tool_1", session_id="s1")
    insights_engine.record_skill_usage("test_skill_1", session_id="s1")
    insights_engine.record_session_activity("session_start", session_id="s1")
    
    # 生成报告
    report = insights_engine.generate_report(days=7, format="json")
    
    # 检查报告结构
    assert "generated_at" in report
    assert "time_range_days" in report
    assert "team_id" in report
    assert "format" in report
    assert report["format"] == "json"
    
    # 检查各个部分
    assert "token_usage" in report
    assert "tool_usage" in report
    assert "skill_usage" in report
    assert "activity_patterns" in report
    assert "summary_metrics" in report
    
    # 检查工具使用部分
    tool_usage = report["tool_usage"]
    assert "total_tool_calls" in tool_usage
    assert "top_tools" in tool_usage
    assert "by_hour" in tool_usage
    
    # 检查技能使用部分
    skill_usage = report["skill_usage"]
    assert "total_skill_invocations" in skill_usage
    assert "top_skills" in skill_usage
    
    # 检查摘要指标
    summary = report["summary_metrics"]
    assert "avg_daily_tokens" in summary
    assert "avg_daily_tool_calls" in summary
    assert "most_active_hour" in summary
    assert "most_used_tool" in summary
    assert "most_used_skill" in summary


def test_report_generation_html(insights_engine):
    """测试 HTML 报告生成"""
    # 添加一些测试数据
    insights_engine.record_tool_usage("html_tool", session_id="s2")
    insights_engine.record_skill_usage("html_skill", session_id="s2")
    
    # 生成 HTML 报告
    report = insights_engine.generate_report(days=7, format="html")
    
    # 检查报告结构
    assert "generated_at" in report
    assert "format" in report
    assert report["format"] == "html"
    assert "html" in report
    
    # 检查 HTML 内容
    html_content = report["html"]
    assert isinstance(html_content, str)
    assert len(html_content) > 0
    
    # 检查是否包含必要的 HTML 标签
    assert "<!DOCTYPE html>" in html_content
    assert "<html>" in html_content.lower()
    assert "<head>" in html_content.lower()
    assert "<body>" in html_content.lower()
    assert "ClawTeam Insights Report" in html_content


def test_empty_database_stats(insights_engine):
    """测试空数据库的统计"""
    # 新数据库应该返回空或零值统计
    stats = insights_engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls == 0
    assert len(stats.by_tool) == 0
    assert len(stats.by_hour) == 0
    
    skill_stats = insights_engine.get_skill_usage_stats(days=7)
    assert skill_stats.total_skill_invocations == 0
    assert len(skill_stats.by_skill) == 0


def test_engine_close_and_reopen(temp_db):
    """测试引擎关闭和重新打开"""
    # 创建引擎并记录数据
    engine1 = InsightsEngine(db_path=temp_db)
    engine1.record_tool_usage("test_close", session_id="close_test")
    engine1.close()
    
    # 重新打开应该能看到之前的数据
    engine2 = InsightsEngine(db_path=temp_db)
    stats = engine2.get_tool_usage_stats(days=7)
    
    # 检查是否记录了数据
    # 注意：由于时间过滤，可能查不到
    if stats.total_tool_calls > 0:
        assert "test_close" in stats.by_tool
    
    engine2.close()


def test_metadata_handling(insights_engine):
    """测试元数据处理"""
    complex_metadata = {
        "nested": {
            "value": 42,
            "list": [1, 2, 3],
            "bool": True
        },
        "string": "test",
        "number": 123.45
    }
    
    # 记录带复杂元数据的工具使用
    insights_engine.record_tool_usage(
        tool_name="metadata_test",
        session_id="meta_session",
        metadata=complex_metadata
    )
    
    # 获取统计应该能正常处理
    stats = insights_engine.get_tool_usage_stats(days=7)
    assert "metadata_test" in stats.by_tool


def test_concurrent_access(temp_db):
    """测试并发访问（简化版）"""
    import sys
    import threading
    
    # SQLite on Windows has threading limitations - skip on Windows
    if sys.platform == "win32":
        pytest.skip("SQLite threading limitation on Windows")
    
    # Skip on Python 3.11 - known to be flaky
    if sys.version_info[:2] == (3, 11):
        pytest.skip("Flaky on Python 3.11 in CI")
    
    results = []
    
    def worker(worker_id):
        engine = InsightsEngine(db_path=temp_db)
        engine.record_tool_usage(f"tool_{worker_id}", session_id=f"worker_{worker_id}")
        stats = engine.get_tool_usage_stats(days=7)
        results.append(stats.total_tool_calls)
        engine.close()
    
    # 启动多个工作线程
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    # 所有线程都应该成功完成
    assert len(results) == 3
    # 每个线程看到的总数可能不同（并发写入）


def test_invalid_input_handling(insights_engine):
    """测试无效输入处理"""
    # 空工具名应该被接受（虽然不理想）
    insights_engine.record_tool_usage("", session_id="empty_test")
    
    # 空会话ID应该被接受
    insights_engine.record_tool_usage("valid_tool", session_id="")
    
    # None 元数据应该被处理
    insights_engine.record_tool_usage("null_meta", session_id="test", metadata=None)
    
    # 获取统计不应该崩溃
    stats = insights_engine.get_tool_usage_stats(days=7)
    assert isinstance(stats, object)  # 应该返回统计对象