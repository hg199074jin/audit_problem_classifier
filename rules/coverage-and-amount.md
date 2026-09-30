# 覆盖与金额规则

## Source Record 与 Finding

`Source Record` 是原始问题、凭证、合同或清单行的唯一覆盖单元。一个 Source Record 可以拆成**多个 Finding**，但拆分只增加问题点数，不复制原始记录。

必须同时维护：

- 原始记录数：按唯一 `source_record_id` 统计；
- Finding 数：按独立问题点统计；
- `voucher_amount`：原始凭证金额，只能按 Source Record 汇总一次；
- `issue_amount`：与具体 Finding 直接相关的金额；
- `confirmed_difference`：有明确依据的已确认差额；
- `pending_amount`：证据不足、尚不能正式认定的金额。

## 禁止重复

同一 Source Record 拆为多个 Finding 时，**原始记录数和 `voucher_amount` 不得重复计算**。不得因为三个 Finding 就把一张 10,000.00元凭证累计为 30,000.00元。

## 覆盖校验

报告应说明“共纳入 X 条原始问题；拆分后形成 Y 个问题点”。未分类原始记录必须列明原因；完成勾稽前不得声称全量覆盖。
