============================================================
                  Skill Governor 审计报告
============================================================
 扫描范围: ~/.claude/plugins/cache/
 Skill 总数: {TOTAL} (去重后)  |  来自 {SUITES} 个插件套件
 已跳过: {SKIPPED} 个无效文件
 发现问题: {ISSUES} 个  |  严重 {CRITICAL}  警告 {WARNING}  建议 {INFO}
============================================================

-- [严重] 重复 (DUPLICATE) ---------------------------------

[{id}] {skill-a} vs {skill-b}
  套件: {suite-a} vs {suite-b}
  原因: {reason}
  建议: {recommendation}

-- [警告] 重叠 (OVERLAP) -----------------------------------

[{id}] {skill-a} vs {skill-b}
  重叠场景: {overlap_scenarios}
  边界建议: {boundary_suggestion}

-- [严重] 冲突 (CONFLICT) ----------------------------------

[{id}] {skill-a} vs {skill-b}
  冲突点: {reason}
  建议: {recommendation}

-- [建议] 失效 (STALE) -------------------------------------

[{id}] {skill-name} ({suite})
  原因: {reason}
  建议: {recommendation}

============================================================
                      推荐操作摘要
============================================================
1. [严重] {recommendation}
2. [警告] {recommendation}
3. [建议] {recommendation}

已跳过的文件:
- {path} ({skip_reason})
