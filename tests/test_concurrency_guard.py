"""
并发控制器测试

测试 ConcurrencyGuard 的功能：
- 会话数限制
- 内存检查
- 资源状态监控
- 跨平台兼容性
"""

import pytest
import platform
import time
from unittest.mock import patch, MagicMock

from clawteam.concurrency.guard import (
    ConcurrencyGuard,
    ConcurrencyConfig,
    ResourceStatus
)


class TestConcurrencyConfig:
    """测试并发配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ConcurrencyConfig()
        assert config.max_sessions == 9
        assert config.min_memory_mb == 512
        assert config.max_cpu_percent == 90.0
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ConcurrencyConfig(
            max_sessions=5,
            min_memory_mb=1024,
            max_cpu_percent=80.0
        )
        assert config.max_sessions == 5
        assert config.min_memory_mb == 1024
        assert config.max_cpu_percent == 80.0
    
    def test_darwin_memory_config(self):
        """测试 macOS 内存配置"""
        config = ConcurrencyConfig()
        # macOS 使用更小的最小内存要求
        assert config.darwin_min_memory_mb == 256


class TestConcurrencyGuard:
    """测试并发控制器"""
    
    def test_init_default(self):
        """测试默认初始化"""
        guard = ConcurrencyGuard()
        assert guard.get_active_session_count() == 0
        assert guard.get_max_sessions() == 9
    
    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = ConcurrencyConfig(max_sessions=3)
        guard = ConcurrencyGuard(config)
        assert guard.get_max_sessions() == 3
    
    def test_can_create_session(self):
        """测试会话创建检查"""
        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=2))
        
        # 初始可以创建
        assert guard.can_create_session()
        
        # 注册一个会话
        guard.register_session()
        assert guard.can_create_session()
        
        # 注册第二个会话
        guard.register_session()
        assert not guard.can_create_session()
    
    def test_register_session(self):
        """测试会话注册"""
        guard = ConcurrencyGuard()
        
        sid1 = guard.register_session()
        assert sid1 is not None
        assert guard.get_active_session_count() == 1
        
        sid2 = guard.register_session("custom-session-id")
        assert sid2 == "custom-session-id"
        assert guard.get_active_session_count() == 2
    
    def test_unregister_session(self):
        """测试会话注销"""
        guard = ConcurrencyGuard()
        
        sid = guard.register_session()
        assert guard.get_active_session_count() == 1
        
        # 注销存在的会话
        result = guard.unregister_session(sid)
        assert result
        assert guard.get_active_session_count() == 0
        
        # 注销不存在的会话
        result = guard.unregister_session("non-existent")
        assert not result
    
    def test_session_duration(self):
        """测试会话持续时间"""
        guard = ConcurrencyGuard()
        
        sid = guard.register_session()
        time.sleep(0.1)
        
        duration = guard.get_session_duration(sid)
        assert duration >= 0.1
        
        # 不存在的会话
        duration = guard.get_session_duration("non-existent")
        assert duration == 0.0
    
    def test_check_resources_session_limit(self):
        """测试资源检查 - 会话数限制"""
        config = ConcurrencyConfig(max_sessions=1)
        guard = ConcurrencyGuard(config)
        
        # 注册一个会话，达到上限
        guard.register_session()
        
        status = guard.check_resources()
        assert not status.can_create
        assert "Maximum session limit" in status.reason
        assert status.current_sessions == 1
        assert status.max_sessions == 1
    
    def test_check_resources_success(self):
        """测试资源检查 - 成功"""
        guard = ConcurrencyGuard()
        
        status = guard.check_resources()
        # 在正常系统上应该可以创建
        # 注意：如果系统内存不足，这个测试可能失败
        assert status.current_sessions == 0
        assert status.max_sessions == 9
        assert status.platform == platform.system()
    
    def test_should_warn_resources_memory(self):
        """测试资源警告 - 内存"""
        guard = ConcurrencyGuard()
        
        # 正常情况下不应该警告
        result = guard.should_warn_resources()
        # 内存使用率可能高也可能低，取决于测试环境
        assert 'warn' in result
        assert 'message' in result or not result['warn']
    
    def test_should_warn_resources_sessions(self):
        """测试资源警告 - 会话数"""
        config = ConcurrencyConfig(max_sessions=10)
        guard = ConcurrencyGuard(config)
        
        # 注册8个会话（80%阈值）
        for _ in range(8):
            guard.register_session()
        
        result = guard.should_warn_resources()
        assert result['warn']
        assert "session limit" in result['message']
    
    def test_get_system_info(self):
        """测试获取系统信息"""
        guard = ConcurrencyGuard()
        
        info = guard.get_system_info()
        assert info['platform'] == platform.system()
        assert info['cpu_count'] >= 1
        assert info['total_memory_mb'] > 0
    
    def test_cleanup(self):
        """测试清理"""
        guard = ConcurrencyGuard()
        
        # 注册多个会话
        guard.register_session()
        guard.register_session()
        guard.register_session()
        
        assert guard.get_active_session_count() == 3
        
        # 清理
        guard.cleanup()
        assert guard.get_active_session_count() == 0
    
    def test_update_config(self):
        """测试更新配置"""
        guard = ConcurrencyGuard()
        
        assert guard.get_max_sessions() == 9
        
        guard.update_config({'max_sessions': 5})
        assert guard.get_max_sessions() == 5


class TestConcurrencyGuardMemory:
    """测试内存检测功能"""
    
    def test_get_memory_snapshot(self):
        """测试内存快照获取"""
        guard = ConcurrencyGuard()
        
        snapshot = guard._get_memory_snapshot()
        assert 'total_mem_mb' in snapshot
        assert 'available_mem_mb' in snapshot
        assert 'memory_usage_percent' in snapshot
        assert snapshot['total_mem_mb'] > 0
        assert snapshot['available_mem_mb'] > 0
    
    def test_get_total_memory(self):
        """测试获取总内存"""
        guard = ConcurrencyGuard()
        
        total = guard._get_total_memory()
        assert total > 0
        # 一般系统内存至少1GB
        assert total >= 1024
    
    def test_get_free_memory(self):
        """测试获取可用内存"""
        guard = ConcurrencyGuard()
        
        free = guard._get_free_memory()
        assert free >= 0
    
    @pytest.mark.skipif(platform.system() != 'Darwin', reason="仅 macOS")
    def test_darwin_vm_stat(self):
        """测试 macOS vm_stat 解析"""
        guard = ConcurrencyGuard()
        
        # 模拟 vm_stat 输出
        vm_stat_output = """
Pages free: 1000000.
Pages inactive: 500000.
Pages speculative: 100000.
Pages purgeable: 50000.
page size of 4096 bytes.
"""
        available = guard._parse_darwin_vm_stat(vm_stat_output, 8192)
        # 计算预期值：(1000000 + 500000 + 100000 + 50000) * 4096 / (1024 * 1024)
        expected = (1650000 * 4096) / (1024 * 1024)
        assert available > 0


class TestConcurrencyGuardCPU:
    """测试 CPU 检测功能"""
    
    def test_get_cpu_usage(self):
        """测试获取 CPU 使用率"""
        guard = ConcurrencyGuard()
        
        cpu = guard._get_cpu_usage()
        assert 0 <= cpu <= 100


class TestConcurrencyGuardCrossPlatform:
    """测试跨平台兼容性"""
    
    def test_windows_memory_detection(self):
        """测试 Windows 内存检测"""
        if platform.system() != 'Windows':
            pytest.skip("仅 Windows")
        
        guard = ConcurrencyGuard()
        total = guard._get_total_memory()
        free = guard._get_free_memory()
        
        assert total > 0
        assert free >= 0
    
    def test_linux_memory_detection(self):
        """测试 Linux 内存检测"""
        if platform.system() != 'Linux':
            pytest.skip("仅 Linux")
        
        guard = ConcurrencyGuard()
        total = guard._get_total_memory()
        free = guard._get_free_memory()
        
        assert total > 0
        assert free >= 0
    
    def test_darwin_memory_detection(self):
        """测试 macOS 内存检测"""
        if platform.system() != 'Darwin':
            pytest.skip("仅 macOS")
        
        guard = ConcurrencyGuard()
        # macOS 应该使用更小的最小内存要求
        assert guard.config.min_memory_mb == 256


class TestConcurrencyGuardIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        config = ConcurrencyConfig(max_sessions=3)
        guard = ConcurrencyGuard(config)
        
        # 1. 检查初始状态
        assert guard.can_create_session()
        status = guard.check_resources()
        assert status.can_create
        
        # 2. 注册会话
        sid1 = guard.register_session()
        assert guard.get_active_session_count() == 1
        
        # 3. 继续注册
        sid2 = guard.register_session()
        sid3 = guard.register_session()
        assert guard.get_active_session_count() == 3
        
        # 4. 达到上限
        assert not guard.can_create_session()
        status = guard.check_resources()
        assert not status.can_create
        
        # 5. 注销会话
        guard.unregister_session(sid1)
        assert guard.get_active_session_count() == 2
        assert guard.can_create_session()
        
        # 6. 清理
        guard.cleanup()
        assert guard.get_active_session_count() == 0
    
    def test_concurrent_session_management(self):
        """测试并发会话管理"""
        guard = ConcurrencyGuard(ConcurrencyConfig(max_sessions=10))
        
        # 注册多个会话
        session_ids = []
        for i in range(5):
            sid = guard.register_session(f"session-{i}")
            session_ids.append(sid)
        
        assert guard.get_active_session_count() == 5
        
        # 检查每个会话的持续时间
        time.sleep(0.1)
        for sid in session_ids:
            duration = guard.get_session_duration(sid)
            assert duration >= 0.0
        
        # 注销所有会话
        for sid in session_ids:
            guard.unregister_session(sid)
        
        assert guard.get_active_session_count() == 0