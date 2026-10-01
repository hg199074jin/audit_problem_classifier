# V2 Evals — Contract 2.0.9

本目录保存 Audit Problem Classifier 的可重复行为回归案例。

## 冻结版本

当前 Gate D 合同版本：`2.0.9`。

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

所有 candidate result 在进入语义评分前必须先通过 `result.schema.json`。该 schema 统一约束已知顶层字段、类型、枚举、非负数量/金额和 `law_roles` object shape，避免 malformed machine result 在 scorer 内裸崩或被隐式容错。

## 为什么取消语义型 contains/not_contains

Gate D 首次真实 runtime 证明，裸子串无法识别中文否定句。例如：

“不能认定构成串通投标”

语义是**未认定**，但旧 scorer 会因为出现“构成串通投标”五个字而误判。

因此 V2.0.9 以后：

- 专业结论 → `conclusion_codes`
- 法规入选/排除 → `law_ids` / `excluded_law_ids`
- HARD-GATE → `gate_status`
- 法规适用 → `applicability_status`
- 文本 literal → 只服务真正格式规则

## Gate D 防污染与 anti-gaming

下一次独立 Gate D 开始前，`2.0.9` 的 case schema、expected 和 scorer 契约必须冻结；Gate E remediation 新增案例也必须纳入同一冻结清单。

Gate D 一旦开始：

1. 生成 runtime 不得读取 `expected`、`text_checks`、`format_forbid` 或 fixtures；
2. `passing-results.jsonl` / `failing-results.jsonl` 不得提供给生成 runtime；
3. 编排器只可机械添加 `id` 和 `contract_version`；
4. `gate_status/category/finding_types/conclusion_codes/applicability_status/law_ids/excluded_law_ids/record_count/finding_count/voucher_total` 必须来自 runtime 自己的机器结果，编排器不得补值；
5. 下一次 Gate D 运行开始后，不得根据实际输出修改 expected、case 或 scorer 来追求 PASS；新增案例后的通过标准按冻结后的总案例数执行。

## 文件

- `cases/*.jsonl`：正式案例；
- `case.schema.json`：案例结构契约；
- `result.schema.json`：machine-result 结构/类型契约；
- `score.py`：deterministic scorer；
- `fixtures/`：只用于验证 scorer 本身，不代表模型真实输出。

真实项目返工仍遵循 Skill-TDD：匿名化 → 先写失败案例 → 证明旧行为 FAIL → 最小修复 → 全量回归。


## V2.0.9 列表评分语义

V2.0.9 不再对所有数组字段统一使用 exact-set，也不回退到无约束 subset。

- 默认：`expected` 中的列表表示“这些值必须出现”；
- 若某字段写入 `expected.exact_fields`，则该字段要求精确集合；
- 未出现在 `expected` 中的字段不等于“必须为空”，但仍受全局不变量约束；
- unknown finding/conclusion code、伪 Law ID、`law_ids ∩ excluded_law_ids`、互斥结论、HARD-GATE 跨字段冲突继续直接 FAIL；
- `excluded_law_ids` 可包含额外真实结构化 Law ID，但不得批量枚举全库不匹配对象；
- `report_sections` 只允许在输入显式提供 `context.report_mode` 时输出，并使用稳定章节代码，不比较中文标题字面。


## V2.0.9 结果完整性

V2.0.9 在 field-aware 评分之上增加三层确定性安全门：

1. **Result schema**：类型、枚举、未知顶层字段、负数金额在语义评分前直接失败；
2. **Law role integrity**：
   - `law_ids` 非空时必须给出完整 `law_roles`；
   - mapping key 必须恰好覆盖选中的 Law ID；
   - role 必须与结构化 Law Object 的 `rule_role` 一致；
   - `liability_basis` 必须有 `context.user_requested_liability_analysis=true`；
3. **Source Record–Finding graph**：
   - Source Record ID / Finding ID 均不得重复；
   - Finding 必须引用真实 Source Record；
   - 记录数、Finding 数和凭证总额从结构化输入推导；
   - 金额字段不得为负。

对 `conclusion_codes`：expected 中声明的专业结论必须出现；未声明的实质性结论默认视为危险额外项并 FAIL。当前仅 `unverified_law_requires_review` 作为诊断型 review 提示允许额外出现。

## V2.0.9 Eval 覆盖

当前正式案例共 **26 个**。在原 21-case 基础上新增：

- 少收仍可追偿 ≠ 已造成损失；
- 先履行后补签 ≠ 倒签；
- 发票信息异常 ≠ 虚开发票；
- Mode A 完整报告：法规适用 + law role + Source Record/Finding + 金额去重；
- Mode B 完整专项报告：同上。

deterministic fixtures 只验证 scorer 本身，不代表真实 runtime 生成成功；真实行为仍必须通过独立 Gate D。
