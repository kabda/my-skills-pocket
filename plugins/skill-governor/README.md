# skill-governor

以手动审计命令为主的治理插件。审计所有已安装的 Claude Code skill，检查质量问题：重复、重叠、冲突和失效项；当检测到新安装的 plugin 或 skill 时，会在下一次会话开始时提醒用户是否执行扫描。

## 内容

| 类型 | 文件 | 说明 |
|------|------|------|
| 命令 | `commands/skill-governor.md` | 手动触发的 skill 审计命令（`/skill-governor`） |
| 扫描脚本 | `scripts/scan.py` | 发现与索引脚本，输出 JSON |
| 提示词模板 | `references/analysis-prompts.md` | 第二阶段 subagent 提示词模板 |
| 报告模板 | `templates/audit-report.md` | 标准审计报告模板（有发现时） |
| 报告模板 | `templates/audit-report-empty.md` | 零问题审计报告模板 |
| Hook | `hooks/hooks.json` | 会话开始时检查新安装，提示是否运行扫描 |
| Hook 脚本 | `hooks/suggest_scan.py` | SessionStart hook 的检测逻辑 |
| 测试 | `scripts/test_scan.py` | scan.py 的单元/集成测试 |
| 测试 | `hooks/test_suggest_scan.py` | suggest_scan.py 的单元测试 |

## 用法

安装后，通过 `/skill-governor` 手动触发审计。

如果 `skill-governor` 发现自上一次会话以来新增了 plugin 或 skill，会在下一次 `SessionStart` 时提示 Claude 询问用户是否要运行 `/skill-governor`。该 hook 只负责提示，不会自动执行扫描。

## 工作方式

整体分为三个阶段：

1. **发现与索引**：运行 `scripts/scan.py` 扫描所有已安装的 SKILL.md 文件，按版本去重，检测机械性问题（同名重复、引用缺失、描述质量），输出 JSON
2. **深度分析**：派发 2 个并行 subagent，分别检测"重复 + 冲突"和"重叠"
3. **汇总与报告**：合并所有发现（scan.py 机械性 + subagent 语义），按严重等级排序，使用模板生成结构化审计报告
