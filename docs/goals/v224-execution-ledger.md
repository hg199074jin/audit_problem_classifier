# V2.2.4 Execution Ledger（append-only）

## [ZCODE-V224-BASELINE] — 2026-11-18

- Branch: `feature/v2.2.4-audit-object-grounding` @ `a3cde83375feddbce2406863ee35620ea43d8aa7`
  - Ancestor verified: `0ec55b8243e14e1de5b59a8571e524e7da04443b`…（准确值 `0ec55b8243e14e1de5b59a8571e524e7da044...` 以 `git merge-base --is-ancestor` 实测通过为准；branch 含 6 个 docs-only 提交：设计/计划/goal 入口）
  - Working tree clean（.DS_Store 已清）
- Runtime: macOS arm64, Python 3.12.14（venv `/tmp/goal-venv` 本日重建：pytest / PyYAML / jsonschema）
- Baseline commands & actual counts（本次实跑）:
  - `pytest -q` → **280 passed**（4.31s）
  - `python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl` → **SUMMARY 26/26 passed**, exit 0
  - negative fixture（failing-results.jsonl）→ **exit 1**（负控有效）
- 历史定位（不重跑、不改写）：
  - V2.2.3 Gate D = 25/26 **BLOCKED**（Issue #8 issuecomment-6631961306）
  - 唯一 FAIL = case-10 `p2-invoice-irregularity-not-false-invoicing`：runtime 输出 FY `expense_supporting_documents_nonstandard`，oracle 要求 `invoice_information_irregularity`（SW）
  - case-10 raw 存档：`~/workspace/default/audit-skill-goal-20261103/v2.2.3-gate-d/runtime-outputs/case-10.{json,md}`（sha256 见同目录 evidence-hashes.json；本地私有，不上传公开仓库）
  - case-10 oracle（frozen，不改）：prompt="报销发票记载的购买方信息与实际报销单位存在不一致，但交易真实、货物确已取得，目前没有虚构交易、无真实业务开票或其他虚开发票证据。请定性。" expected finding_types=["invoice_information_irregularity"], conclusion_codes=["invoice_irregularity_not_false_invoicing_established"]
- 根因（承接 R3-FINAL）：`invoice_split_gate` 的 `independent_invoice_object` / `false_invoicing_dispute` 输入是模型裸 bool；"没有…虚开发票证据"被解读为"无虚开争议"，Gate B 未触发，发票维度被 expense-context FY 默认吸收。输入权威不受证据约束 = 架构缺陷。
- 模型/runtime 记录：ZCode Goal controller（GLM-5.3-Flash 主模型 + fresh general-purpose subagents 做 runtime/裁定/审查）；模型/参数在每次真实运行批次记录于对应 checkpoint。

下一步：Task 1 专业裁定入档（用户 2026-11-18 APPROVED 的《V2.2.4 审计认定对象分类专业规则裁定》全文 + fresh reviewer 反例挑战）。
