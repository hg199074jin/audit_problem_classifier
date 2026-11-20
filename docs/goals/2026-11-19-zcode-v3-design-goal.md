# ZCode Goal 启动入口：V3.0 设计规范定稿（DESIGN ONLY）

**在本机 ZCode 的 Goal 模式粘贴下面完整提示词。** Github 本身不会启动本机 ZCode；本文件和 Issue 是通信与审查中转。

## 一次性 Goal Prompt

启动 Goal 模式，处理 GitHub 仓库 @@hg199074jin/audit_problem_classifier@@ 的 **Issue #12 [ZCODE-V30-DESIGN-GOAL]**。

### 任务边界（不可改变）

这是**仅设计** Goal。本轮交付《V3.0 通用证据引擎与动态法规库技术设计规范》、可编码契约样例、兼容矩阵、独立验收方案与审查证据。**不实现功能、不发布 V3.0、不开发账户/订阅/计费/客户隔离等商业设施。**

优先质量，可使用足够的 token、Superpowers、专业/技术 fresh-context reviewer 和适当 subagents。你是唯一 Goal controller；无需为每个常规文档修订、Git 提交、审查、PR 更新再请示用户。任何专业争议/来源无法验证/独立审查 Critical/Important 无法关闭时，诚实标为 BLOCKED，不编造已完成状态。

### 必须先读

1. GitHub Issue #12: https://github.com/hg199074jin/audit_problem_classifier/issues/12
2. 设计分支 @@design/v3.0-evidence-law-spec-20261119@@（fetch 后检查 SHA、祖先、工作树）
3. 规范 @@docs/superpowers/specs/2026-11-19-v3-evidence-law-design.md@@
4. 计划 @@docs/superpowers/plans/2026-11-19-v3-design-goal-plan.md@@
5. @@SKILL.md@@、@@rules/@@、@@schemas/@@、@@scripts/@@、@@references/laws/@@、@@evals/@@、@@tests/@@ 及 v2.2.4 Issue #9 最终记录。

### 完整执行顺序

- D0: 只读基线审计：旧接口、未完成 Holdout/Gate E、现行数据模型。建立 @@docs/goals/v30-design-ledger.md@@，先在 #12 写 @@[ZCODE-V30-DESIGN-BASELINE]@@。
- D1-D3: 将 EvidenceArtifact/EvidenceSpan/FactClaim/FactAssessment/RuleDefinition/DecisionTrace/LawDocument/LawVersion/LawProvision/LawChangeEvent/LawRuleBinding/LawRelease 的数据字典、字段约束、引用/时间/状态语义审到开发可直接实现的程度。至少两套可核验 JSON 契约样例，补专门 @@docs/contracts/v30-contract-examples.md@@。补否定、假设、转述、OCR、证据冲突、采购未询价与未见询价资料、发票虚开边界的决策表。
- D4-D5: 核实官方法规渠道现状，逐来源记录检索入口/权限/稳定性/重试/数据许可状态；设计源码保存、条款拆分、时间版本、差异检测、审核 PR、不可变发布与回滚。不要把第三方镜像或未实测 API 当权威法源。
- D6-D7: 完成 v2.2.4 兼容矩阵、新旧状态映射、报告 A/B、金额去重、历史法效力与新 36+ holdout 蓝图。为全部安全失败建立明确的 fail-closed 口径，Gate D 不复用旧 raw 冒充 fresh。
- D8: 至少一名 fresh-context 审计专业 reviewer + 一名 fresh-context 技术 reviewer，独立找反例和接口矛盾；记录发现、严重程度、修改、复核，重要问题未关闭则 DESIGN BLOCKED。
- 回写 #12 各 checkpoint，更新文档 PR。只在达到本设计 Goal 0 Critical / 0 Important 和合同完成度要求后，报告 @@[ZCODE-V30-FINAL] DESIGN_PASS@@；否则 @@BLOCKED@@。

### 硬禁止

- 不直接写 main、不 force-push、不移动旧标签、不改变 v2.2.4 专业真值迎合现有模型结果；
- 不把用户保密审计材料、银行流水原件、客户名单、登录凭据放到公开仓库或第三方模型；
- 不把“法规 Schema 通过”写成“法规官方核验完成”；不把“设计完成”写成“V3.0 代码/模型验收完成”；
- 不让未经授权的 LLM 裸布尔决定关键事实、法规适用或严重违规认定；
- 不为抢进度降低验收门槛；有阻断原因照实列明，提供下一次 Goal 的最小工作清单。

### 成果交付格式

在 Issue #12 的 @@[ZCODE-V30-FINAL]@@ 评论中提供准确状态、设计分支/PR/commit SHA、已核验来源数/未核验来源、数据模型契约清单、三值规则实例、V2 兼容检查结果、独立 reviewer 两份结论和未解决风险。**整个 Goal 到此停止，不自动开始 V3 实现或建收费系统。**
