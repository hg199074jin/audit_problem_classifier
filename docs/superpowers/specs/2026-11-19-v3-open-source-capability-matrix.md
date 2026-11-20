# V3.0 开源能力借鉴、复用选型与范围控制矩阵

> 日期：2026-11-19。性质：**DESIGN INPUT / 非选型结论**。本矩阵用于 ZCode Goal 设计与独立审查；所列外部项目的许可证、最新 commit、API、维护状态、安全性、商用条款需由 Goal controller **当场核验并在台账记录**，不能仅凭项目 README 描述直接安装和并入产品。  
> 本期范围：通用证据约束、动态法规库、原始资料定位与证据导出；**不涉及账户、订阅、计费、客户隔离**。

## 1. 必须纳入 V3.0 核心规范的四项能力

| ID | 目标能力 | 候选仓库 | 纳入范围（V3.0） | 具体设计产物 | 验收与停发条件 |
| --- | --- | --- | --- | --- | --- |
| OS-01 | 官方法规智能检索 | [cn-law-hub](https://github.com/ZongziForu/cn-law-hub) | **P0 / 必须设计**；检索候选与法规适用判定分开 | `LawSearchProvider`：`search_exact(document_no,title,article)`、`search_fulltext(query,filters)`、`get_official_source(id)`，统一结果含 `version_id`、`provision_id`、`official_url`、`retrieval_timestamp`、`source_status`、`license_status`；外部工具只能进入候选列表 | 找不到、超时、第三方镜像、同名/不同版本时不得自动发射 `applicable`；官方原件链路未核验必须 `needs_review` |
| OS-02 | 法规自动发现、更新、增量对比 | [Law-Crawler-RPA-RAG-MCP](https://github.com/Yuhamixli/Law-Crawler-RPA-RAG-MCP)、[china-laws](https://github.com/whthomas/china-laws) | **P0 / 必须设计**；参考采集与台账而非无审核合并 | `OfficialSourceAdapter`、`LawChangeEvent`、`LawRelease` 与增量游标、失败隔离、版本对照、审核队列及 GitHub PR 发布流程 | 官方来源访问/许可单独实测；非官方数据只能辅助定位；无审核、仅网页下线、OCR 错字、版本链不清时禁止发布新有效法版本 |
| OS-03 | PDF/Word/Excel/扫描件结构化解析与原文定位 | [Docling](https://github.com/docling-project/docling)、[MinerU](https://github.com/opendatalab/MinerU) | **P0 / 必须设计且技术预研**；保留 `EvidenceArtifact` / `EvidenceSpan` / `parser_run_id` | `DocumentParserAdapter` 接口：`parse(uri,mime,options)`→ `text_snapshot`、`blocks`、`tables`、`locator`、`confidence`、`parser_version`、`sha256`；支持可选后端、OCR 需要时使用、审计数据默认本地处理 | 中英文 PDF 原生文本、扫描件、重复文本、跨页表格、DOCX 段落/表格、XLSX sheet/单元格定位和回跳测试；任何错误页码、伪造 quote、hash 不匹配均阻断正式证据引用 |
| OS-04 | 审计结论—证据链关联底稿 | [cpa-skills](https://github.com/adoptai/cpa-skills)、[accounting-ai-skills](https://github.com/KRASA-AI/accounting-ai-skills) | **P1 / 本轮必须设计**；不抢先构建全能审计软件 | `AuditWorkingPaper` 数据视图：`finding_id`、事实与反证、`evidence_span_ids`、法条版本、`decision_trace_id`、未完成事项、编制/复核状态、导出 MD/DOCX 的字段映射和回链 | 可从报告问题点返回源文件指定页/行/单元格；审计问题/金额/法规/修改状态与结构化结果一致；复核状态不得由模型伪装人工签署 |

### 对 OS-03 的必须决策

**Docling 与 MinerU 并非要求两者同时安装，也不指定某一个永远胜出。** ZCode Goal 必须设计基于相同合成样本的选型比较，至少覆盖：版面与表格保真、原文/页码/Excel 定位、OCR 回看、中文识别质量、Mac 本地运行、资源占用、失败恢复、依赖/许可证、安全与离线能力。可允许不同文件类型采用不同后端，但统一 `DocumentParserAdapter` 契约；不存在清晰、稳定回源时标 `needs_review`，不以解析成功冒充事实真实。

### 对 OS-04 的必须决策

工作底稿的第一个版本只需**证据追溯卡 + 可导出的审计问题工作底稿**，不新增无关的审计计划、电子签名、权限流、法定审计报告签署或完整事务所管理系统。内部 reviewer 可以在结构化审查记录中明确记录判断，但不允许声称已获得真实 CPA 签字。

## 2. 仅预留接口的后续能力（不作为 V3.0 发布门）

| ID | 候选方向 | 参考项目 | 未来接口与前置条件 | 本轮范围 |
| --- | --- | --- | --- | --- |
| OS-05 | 审计抽样与异常凭证识别 | [cpa-skills](https://github.com/adoptai/cpa-skills) | `DetectionCandidate`→ `SourceRecord`；记录异常算法版本、规则、数据范围和误报率；将“异常”与“已查实违规”严格隔离 | **P2 / 只定义边界**，不开发异常检测或审计抽样器 |
| OS-06 | 银行流水对账、金额勾稽 | [finance-audit](https://github.com/sdrplk/finance-audit) | `ReconciliationResult`→ `FactClaim`，多账户、借贷方向、余额连续性、整数分/Decimal、日期排序与重复交易检测 | **P2 / 只预留数据适配**，不重新设计会计核算引擎 |
| OS-07 | XBRL 与财务报表分析 | [SkillsforAudit](https://github.com/GenAICPA/SkillsforAudit) | `FinancialStatementFact`→ `FactClaim`，口径、会计准则、期间及数据来源映射 | **P3 / Backlog**，不在 V3.0 交付或验收 |

这些扩展项**不得进入 V3.0 当前独立 Gate 的必测功能**；但它们也不能绕过未来的共同证据/规则/法规适用门。

## 3. 复用还是自研：统一的选型门

每个候选开源仓库都要生成一张 `ThirdPartyEvaluation`，至少记录：

- `repository_url`、`evaluated_commit_sha`、`evaluated_at`、`license_spdx`（无法判明则标记 unknown）、许可证适用范围及使用/分发限制；
- 最近维护记录、公开安全问题、引入依赖与权限、离线处理能力、是否上传资料到第三方；
- 原生输入输出和数据身份能否映射现有 Evidence/Law Schema；是否可以选型为独立 Adapter 而非直接耦合主引擎；
- 合成样本技术实测结果、失败/限流/结构变化表现、主要维护成本；
- `adopt | wrap | reference_only | reject | pending_review` 的明确结论和专业/技术 reviewer。

**不能未经许可复制代码；没有 license 文件时不能假定“GitHub 公开即可商用”。** 官方法规内容的抓取和再分发也需独立核查来源条款与授权情况。

## 4. 设计 Goal 必须补充的产物

- `docs/validation/v30-third-party-evaluation.md`：7 项能力逐项“已纳入/预留/排除”的设计审核状态，至少前四项与接口契约可追溯；候选代码许可证/实测证据未明时标 `pending_review`。
- `docs/contracts/v30-contract-examples.md`：`LawSearchProvider` / `DocumentParserAdapter` / `AuditWorkingPaper` 字段与示例，以及 Evidence/Law 核心契约。
- `docs/validation/v30-design-review-matrix.md`：新增 OS-01 至 OS-04 四个强制设计检查点；OS-05 至 OS-07 仅审核边界，不影响设计 Gate 通过。

## 5. 对既有 V3 规范和发布范围的解释

- **P0 法规检索与动态更新、P0 原始证据定位、P1 证据工作底稿导出**在 V3.0 **设计**阶段必须落实接口和可验收用例；后续 V3.0 代码发布是否实现应以新的实现计划和冻结后的发布范围为准，不能把“设计列入”表述为“已开发”。
- 即使 ZCode Goal 检索到第三方项目完整工作流，也不能跳过已经设计好的 `law_applicability.py`、v2.2.4 的发票对象授权、HARD-GATE 与 Source Record 金额去重。
- 若候选项目不存在、许可证不兼容、接口不稳定或存在隐私风险，只能选 `reference_only` / `reject` / `pending_review` 并给出替代设计；**不因开源选型失败而造假或引入高风险依赖**。
