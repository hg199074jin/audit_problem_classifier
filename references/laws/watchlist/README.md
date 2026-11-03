# 法规 Watchlist

本目录用于保存已发布未生效、正在修订、效力待确认或官方来源尚未完成核验的候选规则。

Watchlist 的硬规则：

- 不得因为文件出现在本目录就视为现行有效；
- `status` 应使用 `pending` 或 `unknown` 等非确定状态；
- `source.verified != true` 时，法规适用性 Gate 必须返回 `needs_review`；
- 完成官方来源、版本、时效和适用范围核验后，才能迁移到 `national/`、`henan/` 等正式目录。
