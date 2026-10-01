# V2 Evals — Contract 2.0.6

本目录保存 Audit Problem Classifier 的可重复行为回归案例。

## 冻结版本

当前 Gate D 合同版本：`2.0.6`。

专业语义使用结构化字段评分：

- `gate_status`
- `category`
- `finding_types`
- `conclusion_codes`
- `applicability_status`
- `law_ids`
- `excluded_law_ids`
- `record_count`
- `finding_count`
- `voucher_total`
- `law_roles`
- `report_mode`
- `report_sections`

正文 literal 检查只允许用于 `report-format` 域，并通过 `text_checks` / `format_forbid` 表达。

## 为什么取消语义型 contains/not_contains

Gate D 首次真实 runtime 证明，裸子串无法识别中文否定句。例如：

“不能认定构成串通投标”

语义是**未认定**，但旧 scorer 会因为出现“构成串通投标”五个字而误判。

因此 V2.0.6 以后：

- 专业结论 → `conclusion_codes`
- 法规入选/排除 → `law_ids` / `excluded_law_ids`
- HARD-GATE → `gate_status`
- 法规适用 → `applicability_status`
- 文本 literal → 只服务真正格式规则

## Gate D 防污染与 anti-gaming

下一次独立 Gate D 开始前，`2.0.6` 的 case schema、expected 和 scorer 契约必须冻结；Gate E remediation 新增案例也必须纳入同一冻结清单。

Gate D 一旦开始：

1. 生成 runtime 不得读取 `expected`、`text_checks`、`format_forbid` 或 fixtures；
2. `passing-results.jsonl` / `failing-results.jsonl` 不得提供给生成 runtime；
3. 编排器只可机械添加 `id` 和 `contract_version`；
4. `gate_status/category/finding_types/conclusion_codes/applicability_status/law_ids/excluded_law_ids/record_count/finding_count/voucher_total` 必须来自 runtime 自己的机器结果，编排器不得补值；
5. 下一次 Gate D 运行开始后，不得根据实际输出修改 expected、case 或 scorer 来追求 PASS；新增案例后的通过标准按冻结后的总案例数执行。

## 文件

- `cases/*.jsonl`：正式案例；
- `case.schema.json`：案例结构契约；
- `score.py`：deterministic scorer；
- `fixtures/`：只用于验证 scorer 本身，不代表模型真实输出。

真实项目返工仍遵循 Skill-TDD：匿名化 → 先写失败案例 → 证明旧行为 FAIL → 最小修复 → 全量回归。


## V2.0.6 列表评分语义

V2.0.6 不再对所有数组字段统一使用 exact-set，也不回退到无约束 subset。

- 默认：`expected` 中的列表表示“这些值必须出现”；
- 若某字段写入 `expected.exact_fields`，则该字段要求精确集合；
- 未出现在 `expected` 中的字段不等于“必须为空”，但仍受全局不变量约束；
- unknown finding/conclusion code、伪 Law ID、`law_ids ∩ excluded_law_ids`、互斥结论、HARD-GATE 跨字段冲突继续直接 FAIL；
- `excluded_law_ids` 可包含额外真实结构化 Law ID，但不得批量枚举全库不匹配对象；
- `report_sections` 只允许在输入显式提供 `context.report_mode` 时输出，并使用稳定章节代码，不比较中文标题字面。
