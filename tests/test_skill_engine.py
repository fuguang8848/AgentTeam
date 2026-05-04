"""
技能引擎测试

测试 SkillEngine 的功能：
- 提示词模板展开
- 变量解析
- 默认值填充
- 必填变量验证
"""

import pytest
from clawteam.skill.engine import (
    SkillEngine,
    Skill,
    SkillVariable,
    SkillType,
    SkillSource,
    BUILTIN_SKILLS,
    get_builtin_skill_by_command,
    get_all_builtin_skills
)


class TestSkillType:
    """测试技能类型"""
    
    def test_prompt_type(self):
        """测试提示词类型"""
        assert SkillType.PROMPT.value == "prompt"
    
    def test_native_type(self):
        """测试原生类型"""
        assert SkillType.NATIVE.value == "native"
    
    def test_orchestration_type(self):
        """测试编排类型"""
        assert SkillType.ORCHESTRATION.value == "orchestration"


class TestSkillSource:
    """测试技能来源"""
    
    def test_builtin_source(self):
        """测试内置来源"""
        assert SkillSource.BUILTIN.value == "builtin"
    
    def test_user_source(self):
        """测试用户来源"""
        assert SkillSource.USER.value == "user"
    
    def test_mcp_source(self):
        """测试 MCP 来源"""
        assert SkillSource.MCP.value == "mcp"


class TestSkillVariable:
    """测试技能变量"""
    
    def test_variable_creation(self):
        """测试变量创建"""
        var = SkillVariable(
            name='lang',
            description='目标语言',
            required=False,
            default_value='中文'
        )
        
        assert var.name == 'lang'
        assert var.description == '目标语言'
        assert not var.required
        assert var.default_value == '中文'
    
    def test_variable_with_options(self):
        """测试带选项的变量"""
        var = SkillVariable(
            name='framework',
            description='测试框架',
            type='select',
            options=['pytest', 'unittest', 'jest']
        )
        
        assert var.type == 'select'
        assert len(var.options) == 3


class TestSkill:
    """测试技能定义"""
    
    def test_skill_creation(self):
        """测试技能创建"""
        skill = Skill(
            id='test-skill',
            name='测试技能',
            description='这是一个测试技能',
            category='development',
            slash_command='test',
            type=SkillType.PROMPT,
            prompt_template='请处理: {{user_input}}'
        )
        
        assert skill.id == 'test-skill'
        assert skill.name == '测试技能'
        assert skill.slash_command == 'test'
        assert skill.prompt_template == '请处理: {{user_input}}'
        assert skill.is_installed
        assert skill.is_enabled
    
    def test_skill_with_variables(self):
        """测试带变量的技能"""
        skill = Skill(
            id='translate',
            name='翻译',
            description='翻译技能',
            category='language',
            slash_command='translate',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', default_value='中文')
            ],
            prompt_template='翻译为{{lang}}: {{user_input}}'
        )
        
        assert len(skill.input_variables) == 1
        assert skill.input_variables[0].name == 'lang'
    
    def test_skill_auto_timestamp(self):
        """测试自动时间戳"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test'
        )
        
        assert skill.created_at is not None
        assert skill.updated_at is not None


class TestSkillEngineExpand:
    """测试模板展开"""
    
    def test_expand_simple(self):
        """测试简单展开"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='处理: {{user_input}}'
        )
        
        result = SkillEngine.expand(skill, 'Hello World')
        assert result == '处理: Hello World'
    
    def test_expand_with_variables(self):
        """测试带变量展开"""
        skill = Skill(
            id='translate',
            name='Translate',
            description='Translate',
            category='language',
            prompt_template='翻译为{{lang}}: {{user_input}}',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', default_value='中文')
            ]
        )
        
        result = SkillEngine.expand(skill, 'Hello', {'lang': '英文'})
        assert result == '翻译为英文: Hello'
    
    def test_expand_with_default_value(self):
        """测试使用默认值展开"""
        skill = Skill(
            id='translate',
            name='Translate',
            description='Translate',
            category='language',
            prompt_template='翻译为{{lang}}: {{user_input}}',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', default_value='中文')
            ]
        )
        
        # 不提供 lang 变量，使用默认值
        result = SkillEngine.expand(skill, 'Hello')
        assert result == '翻译为中文: Hello'
    
    def test_expand_with_system_prompt(self):
        """测试带系统提示词展开"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='处理: {{user_input}}',
            system_prompt_addition='你是一个专业的助手'
        )
        
        result = SkillEngine.expand(skill, 'Hello')
        assert '你是一个专业的助手' in result
        assert '处理: Hello' in result
    
    def test_expand_no_template(self):
        """测试无模板"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template=None
        )
        
        result = SkillEngine.expand(skill, 'Hello')
        assert result == 'Hello'
    
    def test_expand_multiple_variables(self):
        """测试多变量展开"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='{{var1}} 和 {{var2}}: {{user_input}}',
            input_variables=[
                SkillVariable(name='var1', description='变量1', default_value='A'),
                SkillVariable(name='var2', description='变量2', default_value='B')
            ]
        )
        
        result = SkillEngine.expand(skill, 'content', {'var1': 'X'})
        # var1 使用提供的值，var2 使用默认值
        assert result == 'X 和 B: content'
    
    def test_expand_input_alias(self):
        """测试 input 别名"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='处理: {{input}}'
        )
        
        result = SkillEngine.expand(skill, 'Hello')
        assert result == '处理: Hello'
    
    def test_expand_removes_unfilled_placeholders(self):
        """测试移除未填充的占位符"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='处理: {{user_input}} {{unknown_var}}'
        )
        
        result = SkillEngine.expand(skill, 'Hello')
        # unknown_var 应被移除
        assert '{{unknown_var}}' not in result
        assert result == '处理: Hello'


class TestSkillEngineParseVariables:
    """测试变量解析"""
    
    def test_parse_simple_variable(self):
        """测试简单变量解析"""
        variables = [SkillVariable(name='lang', description='目标语言')]
        
        result = SkillEngine.parse_variables('--lang=英文 这段文字', variables)
        
        assert result['parsed_variables']['lang'] == '英文'
        assert result['remaining_input'] == '这段文字'
    
    def test_parse_quoted_variable(self):
        """测试带引号的变量解析"""
        variables = [SkillVariable(name='text', description='文本内容')]
        
        result = SkillEngine.parse_variables('--text="Hello World" 其他内容', variables)
        
        assert result['parsed_variables']['text'] == 'Hello World'
        assert result['remaining_input'] == '其他内容'
    
    def test_parse_multiple_variables(self):
        """测试多变量解析"""
        variables = [
            SkillVariable(name='lang', description='目标语言'),
            SkillVariable(name='style', description='风格')
        ]
        
        result = SkillEngine.parse_variables('--lang=英文 --style=formal 翻译内容', variables)
        
        assert result['parsed_variables']['lang'] == '英文'
        assert result['parsed_variables']['style'] == 'formal'
        assert result['remaining_input'] == '翻译内容'
    
    def test_parse_undefined_variable_ignored(self):
        """测试未定义变量被忽略"""
        variables = [SkillVariable(name='lang', description='目标语言')]
        
        result = SkillEngine.parse_variables('--lang=英文 --unknown=value 内容', variables)
        
        # unknown 不在定义中，应被忽略
        assert 'unknown' not in result['parsed_variables']
        assert result['parsed_variables']['lang'] == '英文'
    
    def test_parse_no_variables_defined(self):
        """测试无定义变量"""
        result = SkillEngine.parse_variables('--lang=英文 内容', None)
        
        assert result['parsed_variables'] == {}
        assert result['remaining_input'] == '--lang=英文 内容'


class TestSkillEngineValidateVariables:
    """测试变量验证"""
    
    def test_validate_all_provided(self):
        """测试全部提供"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', required=True)
            ]
        )
        
        missing = SkillEngine.validate_variables(skill, {'lang': '英文'})
        assert len(missing) == 0
    
    def test_validate_missing_required(self):
        """测试缺少必填"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', required=True)
            ]
        )
        
        missing = SkillEngine.validate_variables(skill, {})
        assert 'lang' in missing
    
    def test_validate_required_with_default(self):
        """测试必填但有默认值"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', required=True, default_value='中文')
            ]
        )
        
        # 有默认值，不算缺少
        missing = SkillEngine.validate_variables(skill, {})
        assert len(missing) == 0
    
    def test_validate_no_variables(self):
        """测试无变量"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test'
        )
        
        missing = SkillEngine.validate_variables(skill, {})
        assert len(missing) == 0


class TestSkillEngineHelperMethods:
    """测试辅助方法"""
    
    def test_get_variable_defaults(self):
        """测试获取默认值"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', default_value='中文'),
                SkillVariable(name='style', description='风格', default_value='formal')
            ]
        )
        
        defaults = SkillEngine.get_variable_defaults(skill)
        assert defaults['lang'] == '中文'
        assert defaults['style'] == 'formal'
    
    def test_is_compatible_with_provider_all(self):
        """测试兼容所有 Provider"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            compatible_providers='all'
        )
        
        assert SkillEngine.is_compatible_with_provider(skill, 'claude-code')
        assert SkillEngine.is_compatible_with_provider(skill, 'codex')
    
    def test_is_compatible_with_provider_specific(self):
        """测试兼容特定 Provider"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            compatible_providers=['claude-code', 'codex']
        )
        
        assert SkillEngine.is_compatible_with_provider(skill, 'claude-code')
        assert SkillEngine.is_compatible_with_provider(skill, 'codex')
        assert not SkillEngine.is_compatible_with_provider(skill, 'gemini')


class TestSkillEngineProcessCommand:
    """测试命令处理"""
    
    def test_process_skill_command(self):
        """测试处理技能命令"""
        skill = Skill(
            id='translate',
            name='Translate',
            description='Translate',
            category='language',
            slash_command='translate',
            prompt_template='翻译为{{lang}}: {{user_input}}',
            input_variables=[
                SkillVariable(name='lang', description='目标语言', default_value='中文')
            ]
        )
        
        result = SkillEngine.process_skill_command(skill, '--lang=英文 Hello World')
        
        assert result['valid']
        assert result['variables']['lang'] == '英文'
        assert result['missing'] == []
        assert '翻译为英文' in result['prompt']
        assert 'Hello World' in result['prompt']
    
    def test_process_skill_command_missing_required(self):
        """测试缺少必填变量"""
        skill = Skill(
            id='test',
            name='Test',
            description='Test',
            category='test',
            prompt_template='{{required}}: {{user_input}}',
            input_variables=[
                SkillVariable(name='required', description='必填变量', required=True)
            ]
        )
        
        result = SkillEngine.process_skill_command(skill, 'content')
        
        assert not result['valid']
        assert 'required' in result['missing']


class TestBuiltinSkills:
    """测试内置技能"""
    
    def test_builtin_skills_exist(self):
        """测试内置技能存在"""
        assert len(BUILTIN_SKILLS) > 0
    
    def test_get_builtin_skill_by_command(self):
        """测试按命令获取内置技能"""
        skill = get_builtin_skill_by_command('code-review')
        
        assert skill is not None
        assert skill.name == '代码审查'
    
    def test_get_builtin_skill_not_found(self):
        """测试获取不存在的技能"""
        skill = get_builtin_skill_by_command('non-existent')
        
        assert skill is None
    
    def test_get_all_builtin_skills(self):
        """测试获取所有内置技能"""
        skills = get_all_builtin_skills()
        
        assert len(skills) == len(BUILTIN_SKILLS)
    
    def test_translate_skill(self):
        """测试翻译技能"""
        skill = get_builtin_skill_by_command('translate')
        
        assert skill is not None
        assert skill.name == '翻译'
        assert len(skill.input_variables) == 1
        assert skill.input_variables[0].name == 'lang'
    
    def test_code_review_skill(self):
        """测试代码审查技能"""
        skill = get_builtin_skill_by_command('code-review')
        
        assert skill is not None
        assert skill.name == '代码审查'
        assert skill.prompt_template is not None
    
    def test_debug_skill(self):
        """测试 Debug 技能"""
        skill = get_builtin_skill_by_command('debug')
        
        assert skill is not None
        assert skill.name == 'Debug 协助'
    
    def test_commit_msg_skill(self):
        """测试 Commit Message 技能"""
        skill = get_builtin_skill_by_command('commit-msg')
        
        assert skill is not None
        assert skill.name == 'Commit Message'


class TestSkillEngineIntegration:
    """集成测试"""
    
    def test_full_workflow_with_builtin_skill(self):
        """测试使用内置技能的完整流程"""
        skill = get_builtin_skill_by_command('translate')
        
        # 处理命令
        result = SkillEngine.process_skill_command(skill, '--lang=英文 Hello World')
        
        assert result['valid']
        assert '英文' in result['prompt']
        assert 'Hello World' in result['prompt']
    
    def test_builtin_skill_default_values(self):
        """测试内置技能默认值"""
        skill = get_builtin_skill_by_command('translate')
        
        # 不提供 lang 变量
        result = SkillEngine.process_skill_command(skill, 'Hello World')
        
        # 应使用默认值 '中文'
        assert result['valid']
        assert '中文' in result['prompt']
    
    def test_write_test_skill(self):
        """测试生成测试技能"""
        skill = get_builtin_skill_by_command('write-test')
        
        result = SkillEngine.process_skill_command(
            skill,
            '--framework=pytest def add(a, b): return a + b'
        )
        
        assert result['valid']
        assert 'pytest' in result['prompt']
        assert 'def add' in result['prompt']
    
    def test_explain_skill(self):
        """测试解释代码技能"""
        skill = get_builtin_skill_by_command('explain')
        
        result = SkillEngine.process_skill_command(
            skill,
            'def factorial(n): return 1 if n <= 1 else n * factorial(n-1)'
        )
        
        assert result['valid']
        assert 'factorial' in result['prompt']