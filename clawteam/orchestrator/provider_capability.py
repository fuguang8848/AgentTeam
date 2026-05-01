"""Provider 能力注册表

声明每个 AI Provider 对 MCP 和 Skill 的支持能力。
参考 SpectrAI ProviderCapabilityRegistry.ts 实现。

@author ClawTeam
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class McpFallbackType(str, Enum):
    """MCP 降级方式"""
    NONE = "none"  # 不支持降级
    PROMPT_INJECTION = "prompt-injection"  # 通过提示词注入


@dataclass
class ProviderMcpCapability:
    """Provider MCP 能力"""
    native: bool = False  # 是否原生支持 MCP
    config_flag: str = ""  # 配置参数名（如 --mcp-config）
    config_format: str = "json"  # 配置格式
    config_env_var: str = ""  # 配置环境变量
    fallback: McpFallbackType = McpFallbackType.NONE


@dataclass
class ProviderSkillCapability:
    """Provider Skill 能力"""
    slash_commands: bool = False  # 是否支持斜杠命令
    system_prompt: bool = False  # 是否支持系统提示词
    native_skill_dir: str = ""  # 原生技能目录


@dataclass
class ProviderCapability:
    """Provider 完整能力描述"""
    provider_id: str
    mcp_support: ProviderMcpCapability = field(default_factory=ProviderMcpCapability)
    skill_support: ProviderSkillCapability = field(default_factory=ProviderSkillCapability)
    
    # 扩展能力
    supports_streaming: bool = True
    supports_tools: bool = True
    supports_images: bool = False
    max_context_tokens: int = 100000
    supports_long_context: bool = False
    
    # 额度信息
    default_quota_limit: int = -1  # -1 = unlimited
    default_rate_limit_per_minute: int = -1
    
    def to_dict(self) -> dict:
        return {
            "providerId": self.provider_id,
            "mcpSupport": {
                "native": self.mcp_support.native,
                "configFlag": self.mcp_support.config_flag,
                "configFormat": self.mcp_support.config_format,
                "configEnvVar": self.mcp_support.config_env_var,
                "fallback": self.mcp_support.fallback.value,
            },
            "skillSupport": {
                "slashCommands": self.skill_support.slash_commands,
                "systemPrompt": self.skill_support.system_prompt,
                "nativeSkillDir": self.skill_support.native_skill_dir,
            },
            "supportsStreaming": self.supports_streaming,
            "supportsTools": self.supports_tools,
            "supportsImages": self.supports_images,
            "maxContextTokens": self.max_context_tokens,
            "supportsLongContext": self.supports_long_context,
            "defaultQuotaLimit": self.default_quota_limit,
            "defaultRateLimitPerMinute": self.default_rate_limit_per_minute,
        }


# 预定义的 Provider 能力
PROVIDER_CAPABILITIES: dict[str, ProviderCapability] = {
    "claude-code": ProviderCapability(
        provider_id="claude-code",
        mcp_support=ProviderMcpCapability(
            native=True,
            config_flag="--mcp-config",
            config_format="json",
            fallback=McpFallbackType.NONE,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=True,
            system_prompt=True,
            native_skill_dir=".claude/commands",
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=200000,
        supports_long_context=True,
        default_quota_limit=-1,
        default_rate_limit_per_minute=60,
    ),
    "codex": ProviderCapability(
        provider_id="codex",
        mcp_support=ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.PROMPT_INJECTION,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=128000,
        supports_long_context=False,
        default_quota_limit=-1,
        default_rate_limit_per_minute=30,
    ),
    "gemini-cli": ProviderCapability(
        provider_id="gemini-cli",
        mcp_support=ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.PROMPT_INJECTION,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=1000000,
        supports_long_context=True,
        default_quota_limit=-1,
        default_rate_limit_per_minute=60,
    ),
    "iflow": ProviderCapability(
        provider_id="iflow",
        mcp_support=ProviderMcpCapability(
            native=True,
            config_flag="--mcp-config",
            config_format="json",
            fallback=McpFallbackType.NONE,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        default_quota_limit=-1,
        default_rate_limit_per_minute=30,
    ),
    "opencode": ProviderCapability(
        provider_id="opencode",
        mcp_support=ProviderMcpCapability(
            native=True,
            config_env_var="OPENCODE_CONFIG",
            config_format="json-opencode",
            fallback=McpFallbackType.NONE,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=100000,
        supports_long_context=False,
        default_quota_limit=-1,
        default_rate_limit_per_minute=30,
    ),
    "kimi": ProviderCapability(
        provider_id="kimi",
        mcp_support=ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.PROMPT_INJECTION,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=False,
        max_context_tokens=200000,
        supports_long_context=True,
        default_quota_limit=-1,
        default_rate_limit_per_minute=30,
    ),
    "qwen": ProviderCapability(
        provider_id="qwen",
        mcp_support=ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.PROMPT_INJECTION,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=False,
            system_prompt=True,
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=128000,
        supports_long_context=True,
        default_quota_limit=-1,
        default_rate_limit_per_minute=60,
    ),
    "openclaw": ProviderCapability(
        provider_id="openclaw",
        mcp_support=ProviderMcpCapability(
            native=True,
            config_flag="--mcp-config",
            config_format="json",
            fallback=McpFallbackType.NONE,
        ),
        skill_support=ProviderSkillCapability(
            slash_commands=True,
            system_prompt=True,
            native_skill_dir=".openclaw/skills",
        ),
        supports_streaming=True,
        supports_tools=True,
        supports_images=True,
        max_context_tokens=200000,
        supports_long_context=True,
        default_quota_limit=-1,
        default_rate_limit_per_minute=60,
    ),
}


class ProviderCapabilityRegistry:
    """Provider 能力注册表
    
    声明每个 AI Provider 对 MCP 和 Skill 的支持能力。
    """
    
    @staticmethod
    def get(provider_id: str) -> Optional[ProviderCapability]:
        """获取指定 Provider 的完整能力描述"""
        return PROVIDER_CAPABILITIES.get(provider_id)
    
    @staticmethod
    def get_all() -> list[ProviderCapability]:
        """获取所有 Provider 的能力列表"""
        return list(PROVIDER_CAPABILITIES.values())
    
    @staticmethod
    def get_mcp_capability(provider_id: str) -> ProviderMcpCapability:
        """获取指定 Provider 的 MCP 能力（未注册时返回保守默认值）"""
        cap = PROVIDER_CAPABILITIES.get(provider_id)
        if cap:
            return cap.mcp_support
        return ProviderMcpCapability(
            native=False,
            fallback=McpFallbackType.NONE,
        )
    
    @staticmethod
    def get_skill_capability(provider_id: str) -> ProviderSkillCapability:
        """获取指定 Provider 的 Skill 能力"""
        cap = PROVIDER_CAPABILITIES.get(provider_id)
        if cap:
            return cap.skill_support
        return ProviderSkillCapability(
            slash_commands=False,
            system_prompt=False,
        )
    
    @staticmethod
    def supports_native_mcp(provider_id: str) -> bool:
        """是否原生支持 MCP"""
        cap = PROVIDER_CAPABILITIES.get(provider_id)
        return cap.mcp_support.native if cap else False
    
    @staticmethod
    def supports_mcp_fallback(provider_id: str) -> bool:
        """是否支持 MCP Prompt Injection 降级"""
        cap = PROVIDER_CAPABILITIES.get(provider_id)
        if cap:
            return cap.mcp_support.fallback == McpFallbackType.PROMPT_INJECTION
        return False
    
    @staticmethod
    def get_registered_ids() -> list[str]:
        """获取所有已注册的 Provider ID"""
        return list(PROVIDER_CAPABILITIES.keys())
    
    @staticmethod
    def has(provider_id: str) -> bool:
        """检查是否已注册"""
        return provider_id in PROVIDER_CAPABILITIES
    
    @staticmethod
    def register(capability: ProviderCapability) -> None:
        """动态注册新的 Provider 能力"""
        PROVIDER_CAPABILITIES[capability.provider_id] = capability
    
    @staticmethod
    def unregister(provider_id: str) -> bool:
        """注销 Provider 能力"""
        if provider_id in PROVIDER_CAPABILITIES:
            del PROVIDER_CAPABILITIES[provider_id]
            return True
        return False
    
    @staticmethod
    def get_summary() -> dict:
        """获取能力注册表摘要"""
        return {
            "totalProviders": len(PROVIDER_CAPABILITIES),
            "providers": [cap.to_dict() for cap in PROVIDER_CAPABILITIES.values()],
            "nativeMcpProviders": [
                pid for pid, cap in PROVIDER_CAPABILITIES.items()
                if cap.mcp_support.native
            ],
            "fallbackMcpProviders": [
                pid for pid, cap in PROVIDER_CAPABILITIES.items()
                if cap.mcp_support.fallback == McpFallbackType.PROMPT_INJECTION
            ],
            "slashCommandProviders": [
                pid for pid, cap in PROVIDER_CAPABILITIES.items()
                if cap.skill_support.slash_commands
            ],
        }