# skill-governor

人工触发的审计命令插件。审计所有已安装的 Claude Code skill，检查质量问题：重复、重叠、冲突和失效项。

## 内容

| 类型 | 文件 | 说明 |
|------|------|------|
| Command | `commands/skill-governor.md` | 手动触发的 skill 审计命令 |
| Reference | `references/analysis-prompts.md` | 第二阶段使用的 subagent 提示词模板 |
| Template | `templates/audit-report.md` | 标准审计报告模板 |
| Template | `templates/audit-report-empty.md` | 零问题时的审计报告模板 |

## 用法

安装后，通过 `/skill-governor` 手动触发审计。

## 工作方式

整体分为三个阶段：

1. **发现与索引**：扫描 `~/.claude/plugins/cache/` 下所有已安装的 `SKILL.md` 文件，并按版本去重
2. **深度分析**：派发 2 个并行 subagent，分别检测“重复 + 冲突”和“重叠”
3. **汇总与报告**：合并所有发现，生成结构化审计报告
