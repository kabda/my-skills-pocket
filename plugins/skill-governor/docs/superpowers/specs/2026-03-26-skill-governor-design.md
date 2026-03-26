# Skill Governor — 设计规格

## 概述

Skill Governor 是一个诊断型 skill，用于审计所有已安装的 Claude Code skill，检测四类问题：重复、重叠、冲突、失效。手动触发，仅报告不修改，输出结构化终端报告。

## 需求

### 输入
- 扫描范围：`~/.claude/plugins/cache/` 下所有已安装 skill（全量扫描）
- 触发方式：用户手动调用 `/skill-governor`

### 输出
- 终端直接输出结构化 Markdown 报告
- 包含：统计摘要、按问题分类的诊断清单、推荐操作排序

### 约束
- 只读操作，不修改任何 skill 文件
- 多版本 skill 自动去重，只分析最新版本

### SKILL.md 有效性
- 必须包含 YAML frontmatter（`---` 分隔）
- frontmatter 必须包含 `name` 和 `description` 字段
- 不满足条件的文件（如 template/SKILL.md）跳过并在报告末尾标注为"已跳过"

## 四维检测定义

| 维度 | 定义 | 判定标准 | 默认严重等级 |
|------|------|---------|-------------|
| 重复 (Duplicate) | 两个 skill 解决的核心任务几乎一样，只是名字不同 | 同名跨套件直接标记；不同名但对同一用户请求在 >80% 场景下会同时触发 | 🔴 严重 |
| 重叠 (Overlap) | 两个 skill 部分场景相同，边界不清晰，容易同时触发 | 触发条件有交集，各有独有场景；交集超过 50% 触发场景时升为 🔴 | 🟡 警告（交集 >50% 升为 🔴） |
| 冲突 (Conflict) | 两个 skill 对同一类任务给出相反的规则、约定或策略 | 同一场景下两个 skill 的指令互相矛盾 | 🔴 严重 |
| 失效 (Stale) | skill 已过时、描述过宽、触发模糊、引用文件缺失 | 见下方子检测项 | 🔵 建议（引用缺失升为 🟡） |

### 失效检测子项
1. **引用缺失**：SKILL.md 中引用的 `references/`、`scripts/`、`assets/` 路径对应的文件在该 skill 目录下不存在
2. **描述过宽**：description 使用过于泛化的触发词（如 "use for anything"），缺乏具体场景
3. **触发模糊**：description 中没有明确的 "Use when" 类触发条件
4. **内部 skill 引用缺失**：SKILL.md 正文中引用的其他 skill（如 "use /foo instead"）不存在于已安装 skill 列表中

> **注**：不检查外部工具（如 MCP 服务器、CLI 工具）是否安装，因为这些依赖于用户环境配置，超出 skill 文件本身的审计范围。

## 严重等级

- 🔴 **严重 (Critical)**：会导致错误触发或规则冲突，影响日常使用，需要优先解决
- 🟡 **警告 (Warning)**：存在模糊边界，可能偶尔触发错误 skill
- 🔵 **建议 (Info)**：质量改进建议，不影响正常使用

## 技术架构

### 文件结构

```
skills/skill-governor/
├── SKILL.md                 # Skill 定义（frontmatter + 完整指令）
└── references/
    └── analysis-prompts.md  # 四个 subagent 的分析 prompt 模板
```

### 路径解析与套件识别

`~/.claude/plugins/cache/` 下的路径结构不统一，已知有三种模式：

| 模式 | 示例路径 | 套件提取 |
|------|---------|---------|
| 标准 | `cache/claude-plugins-official/superpowers/5.0.5/skills/brainstorming/SKILL.md` | 第二层 = 套件 |
| .claude 嵌套 | `cache/ui-ux-pro-max-skill/ui-ux-pro-max/2.5.0/.claude/skills/ui-ux-pro-max/SKILL.md` | 第二层 = 套件 |
| 扁平 | `cache/anthropic-agent-skills/document-skills/b0cbd3df1533/skills/pdf/SKILL.md` | 第二层 = 套件 |

**套件名提取规则**：取 `cache/` 之后的第一个路径段（即第二层目录名）作为套件标识。

### 版本去重策略

同一套件 + 同一 plugin 名下可能存在多个版本目录：

| 版本格式 | 示例 | 去重策略 |
|----------|------|---------|
| 语义版本 | `5.0.0`, `5.0.5`, `10.5.5` | 取版本号最大的 |
| Git hash | `b0cbd3df1533`, `61c0597779bd` | 取文件系统 mtime 最新的 |
| 混合 | 同一 plugin 下既有语义版本又有 hash | 语义版本优先于 hash |

### 执行流程：三阶段分析

#### 阶段一：发现与索引（主 agent）

1. **发现 skill 文件**：用 Glob 递归扫描 `~/.claude/plugins/cache/**/SKILL.md`
2. **有效性过滤**：Read 每个文件的前 10 行，检查是否有 YAML frontmatter 且包含 `name` 和 `description`
3. **版本去重**：按套件 + plugin 名分组，每组只保留最新版本
4. **提取元数据**：对每个有效 SKILL.md，提取 frontmatter 的 `name` 和 `description` 字段
5. **构建索引表**：将所有 skill 的元数据拼成一个紧凑的文本索引
6. **传递给阶段二**：索引表作为 prompt 上下文传递给 4 个分析 subagent

#### 阶段二：深度分析（4 个并行 subagent）

每个 subagent 收到完整的索引表，独立完成自己的分析维度。每个 subagent 自主决定哪些 skill 需要读取全文进一步分析。

| Subagent | 职责 | 工具使用 | Read 预算 |
|----------|------|---------|----------|
| 重复检测 | 找出核心任务相同的 skill 对 | Read（读取疑似 skill 全文） | 最多 15 个文件 |
| 重叠检测 | 找出触发条件有交集的 skill 对 | Read（读取疑似 skill 全文） | 最多 15 个文件 |
| 冲突检测 | 找出规则矛盾的 skill 对 | Read（读取疑似 skill 全文） | 最多 15 个文件 |
| 失效检测 | 找出过时/引用缺失/描述过宽的 skill | Read + Glob（验证引用文件） | 最多 20 个文件 |

**Subagent 输出 schema**（每个 subagent 必须严格按此格式返回 JSON）：

```json
{
  "type": "duplicate|overlap|conflict|stale",
  "findings": [
    {
      "id": "D-1",
      "severity": "critical|warning|info",
      "skills": ["skill-a (suite-a)", "skill-b (suite-b)"],
      "reason": "具体分析原因",
      "recommendation": "推荐操作",
      "details": {
        "overlap_scenarios": ["场景1", "场景2"],
        "boundary_suggestion": "边界建议",
        "conflict_points": ["冲突点1"],
        "missing_references": ["path/to/file"]
      }
    }
  ]
}
```

#### 阶段三：汇总与报告（主 agent）

1. 收集 4 个 subagent 的 JSON 结果
2. 合并去重（如果两个 subagent 都标记了同一对 skill，保留严重等级更高的）
3. 按严重等级降序排序（🔴 > 🟡 > 🔵）
4. 格式化为终端报告
5. 生成推荐操作摘要

## 报告格式

```
============================================================
                  Skill Governor 审计报告
============================================================
 扫描范围: ~/.claude/plugins/cache/
 Skill 总数: N (去重后)  |  来自 M 个插件套件
 已跳过: K 个无效文件
 发现问题: X 个  |  严重 A  警告 B  建议 C
============================================================

-- [严重] 重复 (DUPLICATE) ---------------------------------

[D-1] skill-a vs skill-b
  套件: suite-a vs suite-b
  原因: <具体分析>
  建议: <推荐操作>

-- [警告] 重叠 (OVERLAP) -----------------------------------

[O-1] skill-a vs skill-b
  重叠场景: <具体场景>
  边界建议: <如何区分>

-- [严重] 冲突 (CONFLICT) ----------------------------------

[C-1] skill-a vs skill-b
  冲突点: <具体矛盾>
  建议: <解决方案>

-- [建议] 失效 (STALE) -------------------------------------

[S-1] skill-name (suite)
  原因: <具体原因>
  建议: <推荐操作>

============================================================
                      推荐操作摘要
============================================================
1. [严重] <具体操作>
2. [警告] <具体操作>
3. [建议] <具体操作>

已跳过的文件:
- path/to/template/SKILL.md (缺少 name 字段)
```

### 零问题报告

当扫描完成且未发现任何问题时，输出：

```
============================================================
                  Skill Governor 审计报告
============================================================
 扫描范围: ~/.claude/plugins/cache/
 Skill 总数: N (去重后)  |  来自 M 个插件套件
 发现问题: 0 个

 所有 skill 通过审计，未发现重复、重叠、冲突或失效问题。
============================================================
```

## 设计决策

1. **三阶段而非全量读取**：60+ 个 skill 全文 token 开销太大，分阶段可节省 50-70% token
2. **4 个并行 subagent**：四种问题类型互不依赖，并行执行减少等待时间
3. **每个 subagent 自主识别疑似对象**：不由主 agent 预筛，因为主 agent 做预筛需要和 subagent 相同的分析能力
4. **Read 预算**：限制每个 subagent 的文件读取量，防止 token 爆炸
5. **仅报告不修改**：skill 文件修改影响较大，应由用户审查后决定
6. **版本去重**：避免旧版本 skill 产生噪音误报
7. **不检查外部依赖**：MCP 服务器和 CLI 工具的可用性取决于用户环境，不在审计范围内

## 不做的事

- 不修改任何 skill 文件
- 不缓存分析结果（每次运行重新分析以保证准确性）
- 不做 skill 推荐/安装建议
- 不分析 marketplace 中未安装的 skill
- 不检查外部工具/MCP 服务器是否存在
