# 覆盖与金额规则

## Source Record 与 Finding

`Source Record` 是原始问题、凭证、合同或清单行的唯一覆盖单元。一个 Source Record 可以拆成**多个 Finding**，但拆分只增加问题点数，不复制原始记录。

必须同时维护：

- 原始记录数：按唯一 `source_record_id` 统计；
- Finding 数：按独立问题点统计；
- `voucher_amount`：**只允许由 Source Record 持有**，原始凭证金额按唯一 `source_record_id` 汇总一次；Finding 不再保存该字段；
- `issue_amount`：与具体 Finding 直接相关的金额；
- `confirmed_difference`：有明确依据的已确认差额；
- `pending_amount`：证据不足、尚不能正式认定的金额。

## 禁止重复

同一 Source Record 拆为多个 Finding 时，**原始记录数和 `voucher_amount` 不得重复计算**。任何需要覆盖统计的机器校验都应从 Source Records 重算，而不是信任候选结果自行声明的总额。不得因为三个 Finding 就把一张 10,000.00元凭证累计为 30,000.00元。

## 覆盖校验

报告应说明“共纳入 X 条原始问题；拆分后形成 Y 个问题点”。未分类原始记录必须列明原因；完成勾稽前不得声称全量覆盖。


## 集合级完整性

当机器上下文同时提供 `source_records` 与 `findings` 时，必须执行图完整性校验：

- `source_record_id` 在集合内唯一；
- `finding_id` 在集合内唯一；
- 每个 Finding 的 `source_record_id` 必须引用一个真实存在的 Source Record，禁止孤儿 Finding；
- `voucher_amount` 只能由 Source Record 持有，且不得为负数；
- Finding 的 `issue_amount / confirmed_difference / pending_amount` 不得为负数；
- 如果存在结构化 `findings`，`finding_count` 必须从实际 Finding 集合推导，不信任 candidate 自报；
- 如果同时存在 `requested_findings`，其值必须与结构化 Finding 数一致。

上述检查属于 coverage contract，不因为候选结果“总数正好对上”就跳过。
