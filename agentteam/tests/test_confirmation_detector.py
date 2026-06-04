"""
确认检测器测试

测试 ConfirmationDetector 的功能：
- 高置信度模式检测
- 中等置信度模式检测
- Provider 配置支持
"""

import pytest
import re
from agentteam.parser.confirmation_detector import (
    ConfirmationDetector,
    ProviderConfirmationConfig,
    get_default_detector,
    detect_confirmation
)
from agentteam.parser.types import ConfirmationDetection


class TestProviderConfirmationConfig:
    """测试 Provider 确认配置"""
    
    def test_config_creation(self):
        """测试配置创建"""
        config = ProviderConfirmationConfig(
            high_patterns=[r'\(Y/n\)'],
            medium_patterns=[r'Continue\?']
        )
        
        assert len(config.high_patterns) == 1
        assert len(config.medium_patterns) == 1
    
    def test_config_default_factory(self):
        """测试默认工厂"""
        config = ProviderConfirmationConfig()
        
        assert config.high_patterns == []
        assert config.medium_patterns == []


class TestConfirmationDetector:
    """测试确认检测器"""
    
    def test_init_default(self):
        """测试默认初始化"""
        detector = ConfirmationDetector()
        
        assert detector.high_patterns is not None
        assert detector.medium_patterns is not None
    
    def test_init_custom_patterns(self):
        """测试自定义模式初始化"""
        custom_high = [re.compile(r'Custom\?', re.IGNORECASE)]
        custom_medium = [re.compile(r'Custom medium', re.IGNORECASE)]
        
        detector = ConfirmationDetector(
            high_patterns=custom_high,
            medium_patterns=custom_medium
        )
        
        assert len(detector.high_patterns) > 0
        assert len(detector.medium_patterns) > 0
    
    def test_from_config(self):
        """测试从配置创建"""
        config = ProviderConfirmationConfig(
            high_patterns=[r'\(Y/n\)'],
            medium_patterns=[r'Continue\?']
        )
        
        detector = ConfirmationDetector.from_config(config)
        
        # 应包含自定义模式和默认模式
        assert len(detector.high_patterns) > 1  # 自定义 + 默认


class TestConfirmationDetectorDetection:
    """测试检测功能"""
    
    def test_detect_high_confidence_y_n(self):
        """测试高置信度检测 - (Y/n)"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Allow tool use? (Y/n)")
        
        assert result is not None
        assert result.confidence == "high"
    
    def test_detect_high_confidence_y_N(self):
        """测试高置信度检测 - (y/N)"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Proceed? (y/N)")
        
        assert result is not None
        assert result.confidence == "high"
    
    def test_detect_high_confidence_brackets(self):
        """测试高置信度检测 - [Y/n]"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Confirm? [Y/n]")
        
        assert result is not None
        assert result.confidence == "high"
    
    def test_detect_medium_confidence_continue(self):
        """测试中等置信度检测 - Continue?"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Continue?")
        
        assert result is not None
        assert result.confidence == "medium"
    
    def test_detect_medium_confidence_are_you_sure(self):
        """测试中等置信度检测 - Are you sure"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Are you sure you want to delete this file?")
        
        assert result is not None
        assert result.confidence == "medium"
    
    def test_detect_medium_confidence_do_you_want(self):
        """测试中等置信度检测 - Do you want"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Do you want to proceed with the installation?")
        
        assert result is not None
        assert result.confidence == "medium"
    
    def test_detect_no_match(self):
        """测试无匹配"""
        detector = ConfirmationDetector()
        
        result = detector.detect("This is a normal output line")
        
        assert result is None
    
    def test_detect_allow_pattern(self):
        """测试 Allow 模式"""
        detector = ConfirmationDetector()
        
        result = detector.detect("Allow Bash(cmd)? (y)")
        
        assert result is not None
        assert result.confidence == "high"
        assert "Bash" in result.prompt_text or "cmd" in result.prompt_text
    
    def test_detect_case_insensitive(self):
        """测试大小写不敏感"""
        detector = ConfirmationDetector()
        
        # 小写
        result1 = detector.detect("continue?")
        assert result1 is not None
        
        # 大写
        result2 = detector.detect("CONTINUE?")
        assert result2 is not None


class TestConfirmationDetection:
    """测试检测结果"""
    
    def test_detection_creation(self):
        """测试检测结果创建"""
        detection = ConfirmationDetection(
            confidence="high",
            prompt_text="Allow tool use?",
            original_line="Allow tool use? (Y/n)"
        )
        
        assert detection.confidence == "high"
        assert detection.prompt_text == "Allow tool use?"
        assert detection.original_line == "Allow tool use? (Y/n)"


class TestDefaultDetector:
    """测试默认检测器"""
    
    def test_get_default_detector(self):
        """测试获取默认检测器"""
        detector = get_default_detector()
        
        assert detector is not None
        assert isinstance(detector, ConfirmationDetector)
    
    def test_detect_confirmation_function(self):
        """测试便捷函数"""
        result = detect_confirmation("Continue?")
        
        assert result is not None
        assert result.confidence == "medium"


class TestConfirmationDetectorIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建检测器
        detector = ConfirmationDetector()
        
        # 2. 检测多种确认请求
        test_cases = [
            ("Allow Read(file.py)? (Y/n)", "high"),
            ("Continue?", "medium"),
            ("Normal output", None),
            ("Are you sure?", "medium"),
            ("[Y/n] Confirm?", "high"),
        ]
        
        for line, expected_confidence in test_cases:
            result = detector.detect(line)
            if expected_confidence is None:
                assert result is None
            else:
                assert result is not None
                assert result.confidence == expected_confidence
    
    def test_provider_specific_config(self):
        """测试 Provider 特定配置"""
        # Claude 特有模式
        config = ProviderConfirmationConfig(
            high_patterns=[r'Allow\s+\w+\s*\?.*\(y\)'],
            medium_patterns=[r'Shall I']
        )
        
        detector = ConfirmationDetector.from_config(config)
        
        result = detector.detect("Allow Bash? (y)")
        assert result is not None
        assert result.confidence == "high"