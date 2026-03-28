============================================================
                  Skill Governor 审计报告
============================================================
 扫描范围: ~/.claude/plugins/cache/
 Skill 总数: {total} (去重后)  |  来自 {suites} 个插件套件
 已跳过: {skipped} 个无效文件
 发现问题: {issues} 个  |  严重 {critical}  警告 {warning}  建议 {info}
============================================================

-- [严重] 重复 (DUPLICATE) ---------------------------------

[{id}] {skill_a} vs {skill_b}
  套件: {suite_a} vs {suite_b}
  原因: {reason}
  建议: {recommendation}

-- [警告] 重叠 (OVERLAP) -----------------------------------

[{id}] {skill_a} vs {skill_b}
  重叠场景: {overlap_scenarios}
  边界建议: {boundary_suggestion}

-- [严重] 冲突 (CONFLICT) ----------------------------------

[{id}] {skill_a} vs {skill_b}
  冲突点: {reason}
  建议: {recommendation}

-- [建议] 失效 (STALE) -------------------------------------

[{id}] {skill_name} ({suite})
  原因: {reason}
  建议: {recommendation}

============================================================
                      推荐操作摘要
============================================================
1. [{severity}] {recommendation}

已跳过的文件:
- {path} ({reason})
