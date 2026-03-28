# Skill Governor Command

人工触发的审计命令。用于诊断审计所有已安装的 Claude Code skill。检测四类问题：重复、重叠、冲突和失效项。只读执行，只报告问题，不修改任何 skill 文件。

## 三阶段分析

```dot
digraph phases {
  rankdir=LR;
  "阶段 1\n发现与索引" -> "阶段 2\n2 个并行 Subagent" -> "阶段 3\n汇总与报告";
}
```

## 阶段 1：发现与索引（由你直接执行）

### 第 1 步：运行扫描脚本

~~~bash
# 找到已安装脚本（与版本无关）：
SCAN=$(ls ~/.claude/plugins/cache/my-skills-pocket/skill-governor/*/scripts/scan.py 2>/dev/null | sort -V | tail -1)
python3 "$SCAN"
~~~

或者从项目源码目录运行：
~~~bash
python3 <path-to-skill-governor-plugin>/scripts/scan.py
~~~

脚本以 `installed_plugins.json` 为权威数据源（而非裸扫 cache 目录），因此仅已注册安装的插件会被扫描——孤立的 cache 残留条目会被自动排除。

脚本会输出一个 JSON 对象，包含：
- `skills`：所有已安装 skill 的 `name`、`description`、`suite`、`plugin`、`path`、`body_preview`（frontmatter 后前 50 行）
- `commands`、`agents`、`hooks`、`mcps`：其他已安装组件
- `findings`：已自动检测出的机械性问题（如跨套件同名重复、引用文件缺失、描述质量问题）
- `skipped`：无法解析的 SKILL.md 文件（含 `path` 和 `reason`）

### 第 2 步：解析 JSON 输出

读取脚本输出。`findings` 数组中的问题已经确认，无需再次分析，直接写入最终报告。

### 第 3 步：构建语义索引

从 `skills` 数组中整理出第二阶段 subagent 使用的索引表：

```
[N] name: <name> | suite: <suite> | plugin: <plugin>
    path: <path>
    description: <description>
    preview: <first 3 lines of body_preview>
```

统计 skill 总数和 suite 总数。如果 `skipped` 数组非空，记录跳过文件数量。

### 第 4 步：进入阶段 2

## 阶段 2：语义分析（派发 2 个并行 subagent）

读取插件目录下 `references/analysis-prompts.md` 中的提示词模板。

使用 Agent 工具在一条消息中同时派发以下两个 subagent（并行执行）：

1. **重复 + 冲突 Agent**：使用“重复与冲突检测 Subagent”提示词模板
2. **重叠检测 Agent**：使用“重叠检测 Subagent”提示词模板

对每个 subagent：
- 用阶段 1 生成的语义索引替换 `{INDEX_TABLE}`
- 将 `subagent_type` 设为 `general-purpose`

等待两个 subagent 全部完成后，再进入阶段 3。

## 阶段 3：汇总结果并生成报告

### 第 1 步：解析并合并所有发现

合并以下三类来源的发现：
1. `scan.py` 输出中的 `findings` 数组（机械性问题，已确认，无需复核）
2. 重复 + 冲突 subagent 返回的 JSON
3. 重叠检测 subagent 返回的 JSON

去重规则：如果同一对 skill 同时出现在两个语义 subagent 的结果中，保留严重等级更高的那条。

### 第 2 步：按严重等级排序

排序顺序：`critical`、`warning`、`info`。

### 第 3 步：格式化并输出报告

先读取插件目录下的 `templates/audit-report.md`。

**关键要求：** 模板文件中的所有中文必须逐字原样复制。不要重写，也不要重新生成中文内容，否则容易出现转写错误和乱码。

输出报告时，只填写模板中的 `{PLACEHOLDER}`。每条 finding 都重复对应区块。没有内容的区块整体省略。如果 `skipped` 数组为空，则省略”已跳过的文件”区块。

**推荐操作摘要规则**：从所有 finding 的 recommendation 字段中去重，按严重等级（critical → warning → info）排列，编号输出。每条推荐前标注其严重等级。

### 零问题报告

如果 `scan.py` 的 `findings` 为空，且两个 subagent 都返回空结果，则读取并输出插件目录下的 `templates/audit-report-empty.md`，只填写其中的 `{PLACEHOLDER}`。

### 省略空区块

如果某个类别没有任何 finding（例如没有重复项），则在报告中省略整个区块。只展示有内容的部分。
