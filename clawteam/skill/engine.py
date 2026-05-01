"""
SkillEngine - 技能引擎

参考 SpectrAI/src/main/skill/SkillEngine.ts 实现
处理 Prompt Skill 的模板展开和变量解析

功能：
- 提示词模板展开
- 变量解析（--varname=value 格式）
- 默认值填充
- 必填变量验证

@author ClawTeam
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SkillType(Enum):
    """技能类型"""
    PROMPT = "prompt"  # 提示词模板类型
    NATIVE = "native"  # 原生类型（直接透传给 Provider）
    ORCHESTRATION = "orchestration"  # 多 Provider 编排类型


class SkillSource(Enum):
    """技能来源"""
    BUILTIN = "builtin"  # 内置
    USER = "user"  # 用户创建
    MCP = "mcp"  # MCP 安装
    IMPORTED = "imported"  # 导入


@dataclass
class SkillVariable:
    """技能变量定义"""
    name: str  # 变量名
    description: str  # 变量描述
    required: bool = False  # 是否必填
    default_value: Optional[str] = None  # 默认值
    type: str = "text"  # 变量类型：text, select, number
    options: Optional[List[str]] = None  # select 类型的选项列表


@dataclass
class Skill:
    """技能定义"""
    id: str  # 技能 ID
    name: str  # 技能名称
    description: str  # 技能描述
    category: str  # 分类：development, writing, analysis, custom
    slash_command: Optional[str] = None  # 触发命令（不含 /）
    type: SkillType = SkillType.PROMPT  # 技能类型
    compatible_providers: Union[str, List[str]] = "all"  # 兼容的 Provider
    
    # Prompt Skill 字段
    prompt_template: Optional[str] = None  # 提示词模板
    system_prompt_addition: Optional[str] = None  # 系统提示词补充
    input_variables: Optional[List[SkillVariable]] = None  # 输入变量定义
    
    # Native Skill 字段
    native_config: Optional[Dict[str, Any]] = None  # 原生配置
    
    # 其他字段
    required_mcps: Optional[List[str]] = None  # 所需 MCP ID 列表
    is_installed: bool = True  # 是否已安装
    is_enabled: bool = True  # 是否启用
    source: SkillSource = SkillSource.BUILTIN  # 来源
    version: Optional[str] = None  # 版本
    author: Optional[str] = None  # 作者
    tags: Optional[List[str]] = None  # 标签
    created_at: Optional[str] = None  # 创建时间
    updated_at: Optional[str] = None  # 更新时间
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


class SkillEngine:
    """
    技能引擎
    
    处理 Prompt Skill 的模板展开和变量解析。
    
    使用示例：
        # 定义技能
        skill = Skill(
            id='translate',
            name='翻译',
            prompt_template='请将以下内容翻译为{{lang}}：\\n\\n{{user_input}}',
            input_variables=[
                SkillVariable(name='lang', default_value='中文')
            ]
        )
        
        # 展开模板
        prompt = SkillEngine.expand(skill, 'Hello World', {'lang': '英文'})
        # 结果: "请将以下内容翻译为英文：\\n\\nHello World"
        
        # 解析变量
        result = SkillEngine.parse_variables('/translate --lang=英文 这段文字', skill.input_variables)
        # result.parsed_variables = {'lang': '英文'}
        # result.remaining_input = '这段文字'
    """
    
    @staticmethod
    def expand(
        skill: Skill,
        user_input: str,
        variables: Optional[Dict[str, str]] = None
    ) -> str:
        """
        展开技能提示词模板
        
        Args:
            skill: Skill 定义
            user_input: 用户输入（/command 后的文本）
            variables: 已解析的变量值
            
        Returns:
            展开后的提示词
        """
        if not skill.prompt_template:
            # 没有模板，直接返回用户输入
            return user_input
        
        prompt = skill.prompt_template
        
        # 替换用户输入占位符
        prompt = prompt.replace('{{user_input}}', user_input)
        prompt = prompt.replace('{{input}}', user_input)
        
        # 替换已提供的变量值
        if variables:
            for key, value in variables.items():
                prompt = re.sub(
                    r'\{\{' + re.escape(key) + r'\}\}',
                    value,
                    prompt
                )
        
        # 用默认值填充未提供的变量
        if skill.input_variables:
            for variable in skill.input_variables:
                if variable.default_value is not None:
                    prompt = re.sub(
                        r'\{\{' + re.escape(variable.name) + r'\}\}',
                        variable.default_value,
                        prompt
                    )
        
        # 移除仍未替换的占位符（留空）
        prompt = re.sub(r'\{\{[a-zA-Z_][a-zA-Z0-9_]*\}\}', '', prompt)
        
        # 前置系统提示词补充
        if skill.system_prompt_addition:
            prompt = f"{skill.system_prompt_addition}\n\n{prompt}"
        
        return prompt.strip()
    
    @staticmethod
    def parse_variables(
        user_input: str,
        variables: Optional[List[SkillVariable]]
    ) -> Dict[str, Any]:
        """
        从用户输入中解析 --varname=value 格式的变量
        
        例如：/translate --lang=英文 这段文字
        返回：{'parsed_variables': {'lang': '英文'}, 'remaining_input': '这段文字'}
        
        Args:
            user_input: 用户输入文本
            variables: Skill 定义的变量列表
            
        Returns:
            dict: {parsed_variables: dict, remaining_input: str}
        """
        parsed_variables: Dict[str, str] = {}
        remaining = user_input
        
        if not variables:
            return {'parsed_variables': parsed_variables, 'remaining_input': remaining}
        
        # 匹配 --varname=value 或 --varname="value with spaces"
        var_pattern = r'--(\w+)=(?:"([^"]*)"|(\S+))'
        matches = list(re.finditer(var_pattern, user_input))
        
        # 获取定义的变量名列表
        defined_var_names = [v.name for v in variables]
        
        for match in matches:
            var_name = match.group(1)
            var_value = match.group(2) or match.group(3) or ''
            
            # 只解析 skill 定义了的变量
            if var_name in defined_var_names:
                parsed_variables[var_name] = var_value
                remaining = remaining.replace(match.group(0), '').strip()
        
        return {
            'parsed_variables': parsed_variables,
            'remaining_input': remaining
        }
    
    @staticmethod
    def validate_variables(
        skill: Skill,
        provided: Dict[str, str]
    ) -> List[str]:
        """
        验证所有必填变量是否已提供
        
        Args:
            skill: Skill 定义
            provided: 已提供的变量值
            
        Returns:
            缺少的必填变量名列表（空数组=验证通过）
        """
        if not skill.input_variables:
            return []
        
        missing = []
        for v in skill.input_variables:
            if v.required:
                # 检查是否已提供或有默认值
                if not provided.get(v.name) and not v.default_value:
                    missing.append(v.name)
        
        return missing
    
    @staticmethod
    def get_variable_defaults(skill: Skill) -> Dict[str, str]:
        """
        获取技能变量的默认值
        
        Args:
            skill: Skill 定义
            
        Returns:
            变量默认值字典
        """
        defaults = {}
        if skill.input_variables:
            for v in skill.input_variables:
                if v.default_value:
                    defaults[v.name] = v.default_value
        return defaults
    
    @staticmethod
    def is_compatible_with_provider(skill: Skill, provider_id: str) -> bool:
        """
        检查技能是否兼容特定 Provider
        
        Args:
            skill: Skill 定义
            provider_id: Provider ID
            
        Returns:
            是否兼容
        """
        if skill.compatible_providers == "all":
            return True
        
        if isinstance(skill.compatible_providers, list):
            return provider_id in skill.compatible_providers
        
        return False
    
    @staticmethod
    def process_skill_command(
        skill: Skill,
        command_input: str
    ) -> Dict[str, Any]:
        """
        处理技能命令的完整流程
        
        Args:
            skill: Skill 定义
            command_input: 命令输入（不含 /command 部分）
            
        Returns:
            dict: {
                prompt: str,  # 展开后的提示词
                variables: dict,  # 解析的变量
                missing: list,  # 缺少的必填变量
                valid: bool  # 是否有效
            }
        """
        # 解析变量
        parse_result = SkillEngine.parse_variables(command_input, skill.input_variables)
        variables = parse_result['parsed_variables']
        remaining_input = parse_result['remaining_input']
        
        # 验证必填变量
        missing = SkillEngine.validate_variables(skill, variables)
        
        # 展开模板
        prompt = SkillEngine.expand(skill, remaining_input, variables)
        
        return {
            'prompt': prompt,
            'variables': variables,
            'missing': missing,
            'valid': len(missing) == 0
        }


# 内置技能定义
BUILTIN_SKILLS: List[Skill] = [
    Skill(
        id='builtin-code-review',
        name='代码审查',
        description='对代码进行全面审查，涵盖逻辑、性能、安全性和可维护性',
        category='development',
        slash_command='code-review',
        type=SkillType.PROMPT,
        compatible_providers='all',
        prompt_template="""请对以下代码进行全面审查：

{{user_input}}

请从以下维度分析：
1. **逻辑正确性** - 是否存在逻辑错误或边界情况未处理
2. **性能** - 是否有性能瓶颈或可优化点
3. **安全性** - 是否有安全漏洞（注入、越权、数据泄露等）
4. **可读性** - 命名、注释、结构是否清晰
5. **可维护性** - 是否符合最佳实践，是否便于扩展

请以结构化格式输出审查结果，并给出具体的改进建议（附代码示例）。""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['code', 'review', 'quality']
    ),
    Skill(
        id='builtin-translate',
        name='翻译',
        description='将内容翻译为指定语言，保持原文语气和格式',
        category='language',
        slash_command='translate',
        type=SkillType.PROMPT,
        compatible_providers='all',
        input_variables=[
            SkillVariable(
                name='lang',
                description='目标语言',
                required=False,
                default_value='中文',
                type='select',
                options=['中文', '英文', '日语', '韩语', '法语', '德语', '西班牙语', '俄语']
            )
        ],
        prompt_template="""请将以下内容翻译为{{lang}}，保持原文的语气、风格和格式：

{{user_input}}

注意：
- 专业术语保持准确
- 不要过度意译，尊重原文表达
- 如有歧义，优先参考上下文""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['language', 'translation']
    ),
    Skill(
        id='builtin-explain',
        name='解释代码',
        description='用通俗易懂的语言解释代码的功能和实现原理',
        category='development',
        slash_command='explain',
        type=SkillType.PROMPT,
        compatible_providers='all',
        prompt_template="""请解释以下代码：

{{user_input}}

请包含：
1. **整体功能**（1-2 句话概括）
2. **关键逻辑步骤**（按执行顺序说明）
3. **使用的主要技术/模式**
4. **潜在注意事项**（边界情况、副作用等）

用通俗易懂的语言，适合中等水平开发者理解。""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['code', 'explain', 'learning']
    ),
    Skill(
        id='builtin-write-test',
        name='生成测试',
        description='为代码或函数生成完整的单元测试',
        category='development',
        slash_command='write-test',
        type=SkillType.PROMPT,
        compatible_providers='all',
        input_variables=[
            SkillVariable(
                name='framework',
                description='测试框架',
                required=False,
                default_value='pytest',
                type='select',
                options=['pytest', 'unittest', 'jest', 'vitest', 'mocha', 'go test', 'JUnit']
            )
        ],
        prompt_template="""请为以下代码使用 {{framework}} 编写完整的单元测试：

{{user_input}}

测试要求：
- 覆盖正常流程、边界情况和异常情况
- 测试命名清晰描述意图（given-when-then 风格）
- 使用 {{framework}} 的最佳实践
- 包含必要的 mock 和 stub
- 目标测试覆盖率 ≥ 80%""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['testing', 'code', 'quality']
    ),
    Skill(
        id='builtin-write-doc',
        name='生成文档',
        description='为代码、函数或模块生成文档注释',
        category='documentation',
        slash_command='write-doc',
        type=SkillType.PROMPT,
        compatible_providers='all',
        input_variables=[
            SkillVariable(
                name='style',
                description='文档风格',
                required=False,
                default_value='docstring',
                type='select',
                options=['docstring', 'JSDoc', 'TSDoc', 'GoDoc', 'Markdown README']
            )
        ],
        prompt_template="""请为以下代码生成 {{style}} 格式的文档注释：

{{user_input}}

文档需包含：
- 简短描述（一句话说明用途）
- 参数说明（类型、含义、是否可选）
- 返回值说明
- 使用示例（如适用）
- 注意事项（如异常情况、副作用等）""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['documentation', 'code']
    ),
    Skill(
        id='builtin-refactor',
        name='重构建议',
        description='分析代码并给出具体重构建议，提升代码质量',
        category='development',
        slash_command='refactor',
        type=SkillType.PROMPT,
        compatible_providers='all',
        prompt_template="""请分析以下代码并给出具体的重构建议：

{{user_input}}

重点关注：
- **消除重复**（DRY 原则）
- **简化复杂逻辑**（降低圈复杂度）
- **改善命名和抽象**（提升可读性）
- **应用合适的设计模式**

对每个建议：
1. 说明当前问题
2. 解释重构理由
3. 提供重构后的代码示例""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['refactoring', 'code', 'quality']
    ),
    Skill(
        id='builtin-commit-msg',
        name='Commit Message',
        description='根据代码改动生成规范的 Git commit message',
        category='git',
        slash_command='commit-msg',
        type=SkillType.PROMPT,
        compatible_providers='all',
        prompt_template="""请根据以下代码改动生成规范的 Git commit message：

{{user_input}}

要求：
- 遵循 Conventional Commits 规范：<type>(<scope>): <description>
- type 选项：feat/fix/chore/docs/refactor/test/style/perf/ci
- 标题简洁（中文 ≤ 30 字，英文 ≤ 72 字符）
- 如有必要，添加详细描述（body）说明原因和影响
- 中文描述优先""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['git', 'commit']
    ),
    Skill(
        id='builtin-debug',
        name='Debug 协助',
        description='分析错误信息和代码，帮助定位和解决 Bug',
        category='development',
        slash_command='debug',
        type=SkillType.PROMPT,
        compatible_providers='all',
        prompt_template="""请帮我分析以下问题：

{{user_input}}

请：
1. **分析可能的根本原因**（列出所有可能性，按可能性排序）
2. **指出最可能的原因**及判断依据
3. **给出具体的修复方案**（附代码示例）
4. **提供预防建议**（如何避免此类问题再次出现）

如果信息不足，请告诉我需要提供什么额外信息。""",
        is_installed=True,
        is_enabled=True,
        source=SkillSource.BUILTIN,
        version='1.0.0',
        author='ClawTeam',
        tags=['debug', 'bug', 'troubleshoot']
    ),
]


def get_builtin_skill_by_command(command: str) -> Optional[Skill]:
    """根据 slash 命令获取内置技能"""
    for skill in BUILTIN_SKILLS:
        if skill.slash_command == command:
            return skill
    return None


def get_all_builtin_skills() -> List[Skill]:
    """获取所有内置技能"""
    return BUILTIN_SKILLS.copy()