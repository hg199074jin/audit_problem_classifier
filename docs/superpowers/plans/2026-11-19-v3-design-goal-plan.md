# [ZCODE-V30-DESIGN] 一次性 Goal 执行与独立审查计划

> 目标是**形成可直接交给开发实施的 V3.0 技术设计和验收方案**，不是本轮立即实现 V3.0 功能或发布版本。  
> 唯一设计基线：`docs/superpowers/specs/2026-11-19-v3-evidence-law-design.md`；仓库 `hg199074jin/audit_problem_classifier`。  
> 分支：`design/v3.0-evidence-law-spec-20261119`；基于 `main@17d985cec07f9be5dce1e46cd7ba0d5f2005bf39`。  
> 禁止事项：账户/订阅/计费/租户设计、真实用户数据上公共 GitHub、修改 main、改旧 Oracle、伪造已完成验收。

## 0. 固定输入和检查清单

先读取：
- `README.md`、`SKILL.md`、`rules/*.md`、`schemas/*.json`、`scripts/{law_applicability,audit_object_grounding,conclusion_grounding,classification_emission,verify_skill_delivery}.py`；
- `references/laws/**` 及现行 `schemas/law.schema.json`、`docs/decisions/v224-invoice-audit-object-adjudication.md`；
- Issue #9 [ZCODE-V224-FINAL]、发布 v2.2.4 的事实边界，特别是 holdout 14/26、Gate E 未执行、A/B UAT 未完整验收；
- V3 规范及本文件。查清未审查的最近分支变化后，仅在隔离设计分支编修文档。

产物 `docs/goals/v30-design-ledger.md`（追加式）：当前 main SHA/tag/CI、文件树、核心接口、已有测试数、遗留 V2.2.4 风险、外部官方来源可访问结果、差异清单。不得宣称“所有法规核验通过”。

## 1. Goal 的任务拆解（设计级，不写产品代码）

| 顺序 | 任务 | 必须产出 | 验收 |
| --- | --- | --- | --- |
| D0 | 环境与数据审计 | 基线 ledger，现有 schema/API 调用关系图 | 代码与已有接口真实一致 |
| D1 | 证据/事实领域建模 | EvidenceArtifact、Span、FactClaim、Assessment、DecisionTrace、Finding 的字段字典及 JSON 样例 | ID、状态、时间、金额、反证均完整 |
| D2 | 专业规则判定设计 | TRUE/FALSE/UNKNOWN 表、授权/拒绝/待核规则、严重定性专门门 | 每个判断有独立正反边界样例 |
| D3 | 法规对象与版本设计 | Document/Version/Provision/Change/Binding/Release Schema 草案、边界和迁移表 | 发布日≠施行日；历史引用不污染现行 |
| D4 | 官方法规源接入验证 | Sources registry（官方/权限/访问方式/可获取性/故障退化），最少 3 个优先适配器技术验证计划 | 不夸称任何未实测 API 稳定 |
| D5 | 更新和回滚设计 | 发现→下载→差异→人工审核→测试→发布→回滚的状态图与 GitHub PR 流程 | 无人工审核不能进入正式规则索引 |
| D6 | V2.2.4 兼容设计 | 旧函数和 schema 接口矩阵、V3 adapter 输入输出示例、影子运行方案 | 不破坏 Source Record 去重、HARD-GATE、Mode A/B |
| D7 | 测试/独立验收设计 | 36+ 预注册 holdout 蓝图、变异/反例分类、发布失败定义、CPA 人工 UAT 清单 | 安全事故零容忍、错误不隐瞒 |
| D8 | 独立复核与成稿 | fresh-context 审计专业 reviewer + fresh-context 技术 reviewer 两份报告；合并勘误与最终 spec | Critical/Important 全部关闭，Minor 排期；不能自称真人审查 |

D0-D8 的文档至少落到：
- `docs/superpowers/specs/2026-11-19-v3-evidence-law-design.md`（规范主文）；
- `docs/superpowers/plans/2026-11-19-v3-design-goal-plan.md`（本执行计划）；
- `docs/goals/2026-11-19-zcode-v3-design-goal.md`（本地 Goal 启动入口）；
- `docs/goals/v30-design-ledger.md`（任务运行时创建，真实检查后才填写）；
- `docs/validation/v30-design-review-matrix.md`（任务运行时创建，审核结论/缺口/责任/风险）。

建议补充 `docs/contracts/v30-contract-examples.md`，包含标准 JSON 样例、状态机迁移与例外规则，以防主文多是概念描述。可由 ZCode Goal 在审查中自主决定更优文件布局，但不得删除内容或无法追踪决策。

## 2. 独立 reviewer 工作范围

**专业 reviewer**（不接触作者内心推理，独立输入完整规范+现有代码+规定来源）：
- 事实“已陈述”与“已查实”界限；
- 无合同/未提供合同、事后补签/倒签、采购未询价/未见资料；
- FY/CG/SW 分类及政府采购范围、财政资金混合、法律历史施行日期；
- 严重定性（虚开、挪用、串通、损失、责任）的证据门；
- 2026 年现行法规来源是否支持本系统处理方式（勿将示例门当作全国统一法律义务）。

**技术 reviewer**：
- 引文定位 offset 与 parser hash、PDF/Excel/OCR、CJK Unicode；
- 事实图的 ID、引用链、支持/反证、时间属性及可复算性；
- 三值逻辑 UNKNOWN 与 FALSE、模型自授权/恶意输入/提示注入；
- 数据 Schema 迁移、半开日期区间与 V2 inclusive/exclusive 边界；
- 官方 source adapter 幂等、时间戳、失败重试、许可与状态机；
- 独立 holdout、基线冻结、CI、发布和回滚证据链。

每条审查问题必须记录 ID、严重度（Critical/Important/Minor）、证据、复现/专业理由、修订、复核结果。对重大专业规则存在不同意见，要独立书面裁定并显式记录；禁止为了“设计通过”降低专业要求。

## 3. 完成标准

### DESIGN PASS

- D0-D8 文档和独立审查结果齐全，**0 Critical / 0 Important** 未解决；
- 所有关键数据对象具备字段、类型、ID 与交叉引用、版本生命周期、错误状态；
- 行为规则可由他人编写确定性测试；不可确定的语义已明示人工复核/needs_review；
- 来源清单区分官方域、查询入口、原件证明、权限/许可及“待实测”；
- 原 V2.2.4 的专业、安全与金额边界全部列入兼容矩阵；
- 独立验收项具备明确输入集合、正确预期、错误裁定、负责角色和阻断条件；
- 禁止商业系统和本轮编写产品运行代码；
- 独立评审可定位到具体 commit/tree SHA 和文档哈希。

### DESIGN BLOCKED

任何未完成必需设计、专业争议无法裁决、官方来源不可验证却被写成已就绪、无审查即声称通过、旧架构不兼容、源数据保密风险未关闭，则标记 `BLOCKED`，列明最小决策缺口；保留文档与 Issue 评论，不得假装已批准。不要反复要求用户重答已给出的约束。

## 4. GitHub 中转与检查点

- GitHub Issue：由本设计 Goal Issue（创建后写入号码）唯一承载状态。
- 文档 PR：`design/v3.0-evidence-law-spec-20261119 → main`，保持 DRAFT，直到设计审查完成。
- 检查点评论：`[ZCODE-V30-DESIGN-BASELINE]`、`[ZCODE-V30-DATA-CONTRACT]`、`[ZCODE-V30-LAW-SOURCES]`、`[ZCODE-V30-COMPATIBILITY]`、`[ZCODE-V30-REVIEW]`、`[ZCODE-V30-FINAL] DESIGN_PASS|BLOCKED`。
- 每条记录包括 HEAD、文件 SHA、已核验证据、风险/未决问题；不要打印凭据或真实客户材料。
- 交付状态仅表述**设计**通过/阻断；绝不写“V3.0 已实现”或“通过 V3.0 模型 Gate D”。

## 5. Goal 完成后的下一阶段边界

经过设计 PASS，才允许另起 **V3.0 IMPLEMENTATION Goal**，按证据引擎→法规版本库→官方适配器→集成→独立实时验收推进。设计 Goal 不能顺手改产品 runtime/发 Release/tag。

**重要：GitHub Issue 和文件只是 ZCode 的中转资料，不会自动在你的 Mac 启动 ZCode。用户需在本机已安装的 ZCode 内开启 Goal 模式，将仓库和 Goal Issue 作为输入。**

## 6. 开源优先能力补充任务（与 D0-D8 同步执行）

必须读取 [V3.0 开源能力借鉴矩阵](../specs/2026-11-19-v3-open-source-capability-matrix.md)，该矩阵是本计划的规范性附件，不是“可选建议”。

- **D4-OS（P0）**：评估 `cn-law-hub`、`Law-Crawler-RPA-RAG-MCP`、`china-laws` 的官方来源、许可证、维护状态、API/采集稳定性，将官方查法与现有 Law Applicability 严格分层。交付 `LawSearchProvider` 和官方 adapter 合同。
- **D2-OS（P0）**：对 Docling / MinerU 设计基于同一套中英文 PDF（原生/扫描）、跨页表格、DOCX 与 XLSX 合成样本的对照选型；交付 `DocumentParserAdapter`、精确回源 locator 与 OCR 不确定性门。可以判定“选型待验证”，不可虚报安装实测。
- **D6-OS（P1）**：参考 `cpa-skills` / `accounting-ai-skills`，设计可回查的 `AuditWorkingPaper`，包含证据引用、专业规则决策轨迹、法规版本、待核查和人工复核状态；只设计 MD/DOCX 底稿导出映射，不扩建审计业务 SaaS。
- **Backlog OS-05/06/07（P2/P3）**：抽样、凭证异常、银行核对、XBRL 仅设计未来输入适配边界，不作为本轮交付或发布门。
- **必交文档**：`docs/validation/v30-third-party-evaluation.md`：7项能力的范围、`ThirdPartyEvaluation` 和使用/拒绝理由，至少前四项的接口/独立测试可落地。
- **设计审查增加**：OS-01～OS-04 的实际资料引用、输入输出契约、许可/隐私安全、错误路径和验收；未明确处理即不能标 `DESIGN_PASS`。

不改变“只完成设计、不实施产品功能、不开发任何账户/订阅/计费/客户隔离设施”的边界。
