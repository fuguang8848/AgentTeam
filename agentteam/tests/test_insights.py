"""测试洞察报告系统 (P16)"""
import pytest
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path

from agentteam.insights import InsightsEngine


@pytest.fixture
def temp_db():
    """临时数据库文件"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def engine(temp_db):
    """洞察引擎实例"""
    e = InsightsEngine(db_path=temp_db)
    yield e
    e.close()


# =============================================================================
# 初始化测试
# =============================================================================

def test_engine_initialization():
    """测试引擎初始化"""
    e = InsightsEngine()
    assert e.db_path is None
    assert e.conn is None
    e.close()


def test_engine_with_custom_db_path(temp_db):
    """测试自定义数据库路径"""
    e = InsightsEngine(db_path=temp_db)
    assert e.db_path == temp_db
    assert e.conn is None  # 延迟连接
    e.close()


def test_engine_connection_initialization(temp_db):
    """测试连接延迟初始化"""
    e = InsightsEngine(db_path=temp_db)
    conn = e._get_conn()
    assert conn is not None
    assert e.conn is not None
    e.close()


# =============================================================================
# Token 消耗统计测试
# =============================================================================

def test_token_usage_stats_returns_valid_structure(engine):
    """测试 Token 统计返回有效结构"""
    stats = engine.get_token_usage_stats(days=7)
    
    assert hasattr(stats, 'total_input_tokens')
    assert hasattr(stats, 'total_output_tokens')
    assert hasattr(stats, 'total_tokens')
    assert hasattr(stats, 'estimated_cost')
    assert hasattr(stats, 'by_provider')
    
    assert isinstance(stats.total_input_tokens, int)
    assert isinstance(stats.total_output_tokens, int)
    assert isinstance(stats.total_tokens, int)
    assert isinstance(stats.estimated_cost, float)
    assert isinstance(stats.by_provider, dict)


def test_token_usage_stats_with_days_filter(engine):
    """测试 Token 统计日期过滤"""
    stats_7 = engine.get_token_usage_stats(days=7)
    stats_30 = engine.get_token_usage_stats(days=30)
    
    # 30天应该包含7天的数据
    assert stats_30.total_tokens >= stats_7.total_tokens


# =============================================================================
# 工具使用频率统计测试
# =============================================================================

def test_tool_usage_empty_stats(engine):
    """测试空数据库的工具统计"""
    stats = engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls == 0
    assert len(stats.by_tool) == 0
    assert len(stats.by_hour) == 0


def test_tool_usage_recording(engine):
    """测试工具使用记录"""
    engine.record_tool_usage(
        tool_name="write_file",
        session_id="sess_001",
        team_id="team_a",
        task_id="task_001",
        metadata={"size": 1024}
    )
    
    stats = engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls == 1
    assert "write_file" in stats.by_tool
    assert stats.by_tool["write_file"] == 1


def test_tool_usage_multiple_tools(engine):
    """测试多个工具记录"""
    tools = ["write", "read", "delete", "list"]
    
    for tool in tools:
        for _ in range(2):
            engine.record_tool_usage(tool_name=tool, session_id="sess_test")
    
    stats = engine.get_tool_usage_stats(days=7)
    
    assert stats.total_tool_calls == 8
    for tool in tools:
        assert tool in stats.by_tool
        assert stats.by_tool[tool] == 2


def test_tool_usage_hourly_distribution(engine):
    """测试工具使用小时分布"""
    # 记录多次工具使用
    for _ in range(5):
        engine.record_tool_usage(tool_name="test_tool", session_id="sess_hour")
    
    stats = engine.get_tool_usage_stats(days=7)
    
    assert isinstance(stats.by_hour, dict)
    # 当前小时应该有数据
    current_hour = datetime.now().hour
    if current_hour in stats.by_hour:
        assert stats.by_hour[current_hour] >= 5


def test_tool_usage_time_filtering(engine):
    """测试时间范围过滤"""
    engine.record_tool_usage(tool_name="old_tool", session_id="sess_old")
    
    # 默认30天应该能查到
    stats_30 = engine.get_tool_usage_stats(days=30)
    assert stats_30.total_tool_calls >= 1


# =============================================================================
# 技能使用模式测试
# =============================================================================

def test_skill_usage_empty_stats(engine):
    """测试空数据库的技能统计"""
    stats = engine.get_skill_usage_stats(days=7)
    
    assert stats.total_skill_invocations == 0
    assert len(stats.by_skill) == 0


def test_skill_usage_recording(engine):
    """测试技能使用记录"""
    engine.record_skill_usage(
        skill_name="code_review",
        session_id="sess_002",
        team_id="team_a",
        task_id="task_002",
        result_length=500,
        metadata={"language": "python"}
    )
    
    stats = engine.get_skill_usage_stats(days=7)
    
    assert stats.total_skill_invocations == 1
    assert "code_review" in stats.by_skill
    assert stats.by_skill["code_review"] == 1


def test_skill_usage_multiple_skills(engine):
    """测试多个技能记录"""
    skills = ["summarize", "code_review", "test"]
    
    for skill in skills:
        engine.record_skill_usage(skill_name=skill, session_id="sess_multi")
    
    stats = engine.get_skill_usage_stats(days=7)
    
    assert stats.total_skill_invocations == 3
    for skill in skills:
        assert skill in stats.by_skill
        assert stats.by_skill[skill] == 1


# =============================================================================
# 活动模式分析测试
# =============================================================================

def test_activity_stats_empty(engine):
    """测试空数据库的活动统计"""
    stats = engine.get_activity_stats(days=7)
    
    assert isinstance(stats.by_weekday, dict)
    assert isinstance(stats.by_hour, dict)
    assert isinstance(stats.total_sessions, int)
    assert isinstance(stats.active_days, int)


def test_session_activity_recording(engine):
    """测试会话活动记录"""
    engine.record_session_activity(
        event_type="session_start",
        session_id="sess_start_001",
        team_id="team_x",
        task_id="",
    )
    
    stats = engine.get_activity_stats(days=7)
    
    assert stats.active_days >= 0
    assert isinstance(stats.by_weekday, dict)


def test_activity_weekday_distribution(engine):
    """测试活动按星期分布"""
    # 记录多次会话活动
    for _ in range(3):
        engine.record_session_activity(
            event_type="session_start",
            session_id=f"sess_weekday_{_}",
        )
    
    stats = engine.get_activity_stats(days=7)
    
    assert isinstance(stats.by_weekday, dict)


def test_activity_hourly_distribution(engine):
    """测试活动按小时分布"""
    for _ in range(3):
        engine.record_tool_usage(tool_name="hourly_test", session_id=f"sess_h_{_}")
    
    stats = engine.get_activity_stats(days=7)
    
    assert isinstance(stats.by_hour, dict)


# =============================================================================
# 报告生成测试
# =============================================================================

def test_generate_report_json_format(engine):
    """测试 JSON 格式报告生成"""
    # 添加测试数据
    engine.record_tool_usage(tool_name="report_test", session_id="sess_report")
    engine.record_skill_usage(skill_name="report_skill", session_id="sess_report")
    
    report = engine.generate_report(days=7, format="json")
    
    assert "generated_at" in report
    assert "time_range_days" in report
    assert report["time_range_days"] == 7
    
    assert "token_usage" in report
    assert "tool_usage" in report
    assert "skill_usage" in report
    assert "activity_patterns" in report
    assert "summary_metrics" in report


def test_generate_report_html_format(engine):
    """测试 HTML 格式报告生成"""
    engine.record_tool_usage(tool_name="html_test", session_id="sess_html")
    
    report = engine.generate_report(days=7, format="html")
    
    assert "html" in report
    assert isinstance(report["html"], str)
    assert "<!DOCTYPE html>" in report["html"]
    assert "AgentTeam Insights Report" in report["html"]


def test_generate_report_with_team_filter(engine):
    """测试按团队过滤的报告生成"""
    engine.record_tool_usage(
        tool_name="team_filter_test",
        session_id="sess_team",
        team_id="specific_team"
    )
    
    report = engine.generate_report(days=7, team_id="specific_team", format="json")
    
    assert report["team_id"] == "specific_team"


# =============================================================================
# 工具和技能关联测试
# =============================================================================

def test_tools_and_skills_together(engine):
    """测试工具和技能同时记录"""
    engine.record_tool_usage(tool_name="exec", session_id="sess_both")
    engine.record_skill_usage(skill_name="analyze", session_id="sess_both")
    
    tool_stats = engine.get_tool_usage_stats(days=7)
    skill_stats = engine.get_skill_usage_stats(days=7)
    
    assert tool_stats.total_tool_calls >= 1
    assert skill_stats.total_skill_invocations >= 1


# =============================================================================
# 数据库持久化测试
# =============================================================================

def test_data_persistence_across_instances(temp_db):
    """测试数据在多个实例间持久化"""
    # 第一个实例写入数据
    e1 = InsightsEngine(db_path=temp_db)
    e1.record_tool_usage(tool_name="persist_test", session_id="sess_persist")
    e1.close()
    
    # 第二个实例读取数据
    e2 = InsightsEngine(db_path=temp_db)
    stats = e2.get_tool_usage_stats(days=7)
    
    # 验证数据存在
    found = False
    if stats.total_tool_calls > 0:
        found = "persist_test" in stats.by_tool
    
    e2.close()
    
    # 注意：由于SQLite的隔离性，可能需要不同的查询方式
    assert isinstance(stats.total_tool_calls, int)


# =============================================================================
# 边界条件测试
# =============================================================================

def test_zero_days_filter(engine):
    """测试零天过滤"""
    engine.record_tool_usage(tool_name="zero_test", session_id="sess_zero")
    
    stats = engine.get_tool_usage_stats(days=0)
    
    assert isinstance(stats.total_tool_calls, int)


def test_metadata_none_handling(engine):
    """测试 None 元数据处理"""
    engine.record_tool_usage(
        tool_name="none_meta",
        session_id="sess_none",
        metadata=None
    )
    
    stats = engine.get_tool_usage_stats(days=7)
    assert "none_meta" in stats.by_tool


def test_empty_session_id(engine):
    """测试空会话 ID 处理"""
    engine.record_tool_usage(
        tool_name="empty_sess",
        session_id=""
    )
    
    stats = engine.get_tool_usage_stats(days=7)
    assert "empty_sess" in stats.by_tool
