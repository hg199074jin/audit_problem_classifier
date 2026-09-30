# V2 Evals

本目录保存 Audit Problem Classifier V2 的行为回归案例。

- `cases/*.jsonl`：每行一个独立测试案例。
- `case.schema.json`：案例结构契约。
- `expected` 必须至少包含一个可机器检查字段；当前允许 `contains`、`not_contains`、`category`、`law_ids`、`record_count`、`finding_count`、`voucher_total`。
- `forbidden` 保存明确禁止出现的定性、引用或统计结果。
- 案例用于定义预期行为，不等同于法规事实来源。法规事实仍须通过结构化法规库和官方来源核验。

V1 的 6 个 `test-prompts.json` 场景已迁入本目录，同时增加 V2.0 的 P0 回归案例。后续真实项目返工应先匿名化，再新增失败案例，然后修改规则。
