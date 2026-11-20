# V3.0 通用证据引擎与动态法规库技术设计规范

> 状态：**DESIGN DRAFT / 待独立专业与技术审查**；仅设计，不代表开发、运行或验收完成。  
> 日期：2026-11-19；范围：`hg199074jin/audit_problem_classifier`；设计起点：`main@17d985cec07f9be5dce1e46cd7ba0d5f2005bf39`。  
> 历史：`v2.2.4` 已发布，正式 Gate D 26/26；但 Issue #9 记载独立 Holdout 14/26 执行、发现 Schema/语义偏差，最终 Gate E、完整 Mode A/B UAT 未完成。**不能将发布等同于全套质量门已通过。**  
> 总体目标：保留中国 CPA 审计问题报告化 Skill，将“证据→事实→专业条件→法规→Finding→报告”形成可核验、可拒绝、可复算、可追踪的完整链，并建立法规官方发现、版本变更、核验、发布与重评机制。

## 0. 决策、边界、不可变约束

- 本期**明确不做**账户、订阅、计费、客户隔离、商业许可证、支付、团队 SaaS、营销后台；不因未来订阅规划而重构运行时。
- 不推倒现有 `SKILL.md` 13 步、HARD-GATE、12 主类、Source Record/Finding 去重、Mode A/B、`law_applicability.py` 六维过滤及 `v2.2.4` 授权边界。新增 V3 层必须包容并验证上述不变量。
- **LLM 提议、程序核验、专业人员复核**。模型输出的 `is_confirmed`、`is_applicable`、`authorized` 等裸布尔**永不成为可信事实或授权来源**。
- 不用关键词命中、引文存在、OCR 置信度、检索排名、模型投票，直接证明事实真实或法律适用。
- 结论安全边界：缺附件≠业务未发生；无询价资料≠必然未询价；资金最终流向个人≠虚开；事后补签≠倒签；已缴款较少≠已形成损失；否定句≠肯定事实。
- 原始证据不可覆盖；任何纠错都产生新事实/新决策/新法规版本，旧记录可以标记废止、被反证或被取代，但不能静默擦除。
- 所有真实审计底稿、合同、个人信息、凭据及模型请求原文按敏感资料处理；不得上传本公共 GitHub 仓库、Issue、PR、外部 RAG 或未授权模型。仓库仅使用脱敏、合成、可公开证据。
- 本规范先锁定**数据语义与验收口径**；无法当场独立核实的外部官方接口只标记“待技术验证”，绝不宣称已经具备稳定批量采集能力。

## 1. 目标用户与两个可观察场景

### 1.1 通用证据引擎

输入财务收支审计问题、凭证、合同、台账、整改反馈或委托范围后，系统输出：原始记录覆盖、可定位证据、事实与反证、认定条件、候选/待核/正式 Finding、缺证清单、适用法规及报告。CPA 可在“认定依据卡”逐层查看证据链和阻断理由。

### 1.2 动态法规库

给定主体（如河南县级事业单位）、事项日期、资金、事项性质和已证实事实，系统能定位法规候选并展示**官方来源、对应全文/条文版本、效力、六维适用和缺口**。发现修订、废止或替代时生成差异与受影响规则清单，经审核、回归后生成独立可追溯数据发布版本。

## 2. 共同身份、数据模型与不可变来源

### 2.1 对象及主外键

| 对象 | 用途 / 主键 | 关系与硬约束 |
| --- | --- | --- |
| `ProjectContext` | `project_id` | 项目地区、主体类型、期间、资金、报告模式；保留现有 project-level 事实 |
| `SourceRecord` | `source_record_id` | 原始问题行/凭证/合同事项，用户唯一覆盖统计单元；不能因拆 Finding 重复金额 |
| `EvidenceArtifact` | `evidence_id` | 上传/获取的**原始字节**哈希 SHA-256、MIME、来源、存储 URI、获取时间、保密级别 |
| `EvidenceSpan` | `span_id` | `evidence_id` + 文本或页/表/单元格定位 + 原文逐字引文 + 解析快照哈希 |
| `FactClaim` | `fact_id` | 事实候选，引用一或多条 span，支持/反证关系；不等同于确定事实 |
| `FactAssessment` | `assessment_id` | 针对事实的核实状态、核实者、时间、反证及理由；不可覆盖历史 |
| `RuleDefinition` | `rule_id` + `rule_revision` | 结构化条件、必需事实、例外与风险等级，绑定法规条款的具体版本或事务所方法规则 |
| `DecisionTrace` | `decision_id` | 评估输入哈希/规则版/结果/失败条件/执行器版；用于复算 |
| `Finding` | `finding_id` | 引用 Source Record、Fact、Decision 和条文；每个 Finding 唯一主类；强制人工终审标志 |
| `LawDocument` | `document_id` | 一部正式法规/制度的稳定身份，不把文件标题当唯一主键 |
| `LawVersion` | `version_id` | 官方文本某个有效历史版本、生效关系、原件哈希及审核状态 |
| `LawProvision` | `provision_id` | 条款级全文 + 版本归属 + 内容哈希；不可跨版本混引 |
| `LawChangeEvent` | `change_id` | 发布、施行、修订、解释、废止、替代、失效、冲突/待核等变化 |
| `LawRuleBinding` | `binding_id` | 将已核验条款版本投影为现有 Law Object 或审计认定规则的映射 |
| `LawRelease` | `release_id` | 已审核法规数据集合的不可变 manifest、哈希、签署/审核记录 |

所有引用必须带明确 ID；`source_record_id`、`fact_id`、`law_version_id` 不得用无根据的模型自由文字暗中匹配。同一 `FactClaim` 可由多份证据支持或反驳，禁止“仅绑定一条引文”的单证据结构限制。

### 2.2 EvidenceArtifact / EvidenceSpan 最低契约

    EvidenceArtifact:
      evidence_id: "EV-0001"
      source_record_ids: ["SR-0001"]
      sha256: "<64位十六进制真实字节摘要>"
      mime_type: "application/pdf"
      original_filename: "sample.pdf"
      origin: "user_upload"           # user_upload | official_fetch | generated_fixture
      acquired_at: "2026-11-19T10:00:00+08:00"
      confidentiality: "restricted"   # public | internal | restricted
      storage_ref: "local://..."      # 仅可信内部 URI，不写私有外部下载链接
      immutable: true

    EvidenceSpan:
      span_id: "ES-0001"
      evidence_id: "EV-0001"
      parser_run_id: "PARSE-0001"
      extraction_sha256: "<规范化解析文本摘要>"
      locator:
        type: "pdf_text"
        page: 3                    # 用户可见页码，从 1 开始
        start_char: 18             # 在 parser_run 的固定 UTF-8 解码文本中的 Unicode code-point 偏移
        end_char: 29               # 右开区间，需核对 text[start:end] == quote
      quote: "..."
      extraction_method: "native_text"  # native_text | ocr | manual
      extraction_confidence: null       # 仅识别质量指标，不是事实真实性

Locator 至少支持 `text` / `pdf_text` / `pdf_ocr` / `xlsx_cell_range` / `docx_paragraph`；扫描页另附 bbox、坐标系、分辨率。Excel 必须带 sheet 名、行列；Word 带段落或表格单元格坐标。引用存在性要在同一个固定 parser_run 中验证；解析升级后不得沿用旧字符偏移而不重建/核对。

原始字节与解析文本分离：`sha256` 校验源文件未变；`extraction_sha256` 校验引用所见文本未变。引文重复出现时以定位符 + 精确范围消歧；不得仅用 `quote in file` 授权。对无法可靠定位的扫描件允许展示“待人工确认”，不能自动升级为查实事实。

### 2.3 FactClaim / FactAssessment 最低契约

    FactClaim:
      fact_id: "FC-0001"
      project_id: "P-001"
      source_record_ids: ["SR-0001"]
      proposition: "该笔款项的发票购买方与实际报销单位不一致"
      subject: {type: "organization", ref: "ORG-001"}
      predicate: "invoice_buyer_mismatch" # 受控 registry，允许扩展但不得自由发射高危语义
      object: {type: "invoice", ref: "INV-001"}
      polarity: "affirmative"       # affirmative | negative
      modality: "asserted"          # asserted | hypothetical | question | reported
      source_scope: "invoice"       # 凭证/句子/主体/期间等作用域
      event_date: "2025-06-30"      # 不能从审计期间默默猜一日
      evidence_links:
        - {span_id: "ES-0001", relation: "supports", provenance: "primary"}
        - {span_id: "ES-0002", relation: "refutes", provenance: "primary"}
      candidate_origin: "llm"       # 人、模型或确定性提取器

    FactAssessment:
      assessment_id: "FA-0001"
      fact_id: "FC-0001"
      state: "conflicting"
      reviewer: "human-or-policy-engine"
      considered_links: ["ES-0001", "ES-0002"]
      reasons: ["CONTRADICTORY_PRIMARY_EVIDENCE"]
      assessed_at: "2026-11-19T10:01:00+08:00"

状态集合：`confirmed`（足够且适当证据）、`partially_supported`、`unverified`、`conflicting`、`refuted`、`hypothetical`。声明内容只出现在“情况说明”里，应区分“说明作出该陈述”与“陈述事实确实成立”，不能由 `quote` 自动得出 `confirmed`。`confirmed` 需指定被授权的核验策略/人工核验记录；不得由模型自填。

### 2.4 决策与审计 Finding

    DecisionTrace:
      decision_id: "DT-0001"
      rule_id: "EXPENSE-SUPPORT-001"
      rule_revision: "1"
      rule_input_hash: "<sha256>"
      fact_assessment_ids: ["FA-0001"]
      law_binding_ids: ["LB-0001"]
      evaluator_version: "3.0.0"
      result: "needs_review"      # authorized | not_established | needs_review | rejected
      failed_or_unknown_conditions: ["REQUIRES_VALID_SERVICE_PERFORMANCE_EVIDENCE"]
      reason_codes: ["MISSING_MATERIAL_FACT"]
      evaluated_at: "..."
      override: null              # 禁止 runtime 自填 authorized

`Finding` 引用 `decision_id`，与原 Source Record、现有 `primary_category` / `secondary_type`、证据等级、金额、`decision_status` 兼容；未批准不得 `final`。金额采用 Decimal/整数分，按 Source Record 的唯一凭证标识聚合，不从拆分 Finding 总和重算原始流水总金额。对于多个独立 Finding，只有条件支持的结论进入正式报告；其余仅列待核实和补证清单。

## 3. 规则判定引擎：受控三值逻辑 + 严重结论授权

### 3.1 固定调用链

`原始文件→解析快照→EvidenceSpan→LLM FactClaim 候选→来源校验→状态核实/反证检查→RuleDefinition 条件求值→Law Applicability→DecisionTrace→Finding→双重交付门+完整引用校验→报告`。

必须做到：模型不可直接生成 `authorized`、`confirmed` 或可用于正式报告的 `applicable`；即使输出里自填这些字段，下游门也必须重新从受保护输入复算并拒绝不一致。旧 `audit_objects` 继续经 v2.2.4 的发票授权门处理，V3 不得覆盖其权威。

### 3.2 RuleDefinition 结构

    rule_id: "CG-INQUIRY-001"
    rule_revision: "1"
    target_finding_type: "procurement_inquiry_missing"
    severity: "material"          # ordinary | material | high_risk
    condition:
      all:
        - {fact: "procurement_subject_in_scope", op: "eq", value: true}
        - {fact: "procurement_covered_funds", op: "eq", value: true}
        - {fact: "procedure_legally_required", op: "eq", value: true}
        - {fact: "procedure_not_performed", op: "eq", value: true}
    counterevidence:
      - "approved_procedure_exemption"
      - "valid_alternative_compliance_path"
    required_law_roles: ["direct_basis"]
    on_unknown: "needs_review"
    on_counterevidence: "needs_review"
    wording_cap: "no_fraud_or_collusion_without_separate_rule"
    policy_owner: "audit-professional-reviewer"

**示例只是可执行语义骨架，不宣称所有政府采购都法定须询价**；`procedure_legally_required` 必须从事项、金额、时间、适用条款及例外取得结构化证明。禁止将“未提供询价记录”替换成 `procedure_not_performed=true`。

### 3.3 求值语义必须锁定

- 条件原子值：`TRUE`、`FALSE`、`UNKNOWN`；`FALSE` 表示**证据证实条件不满足**，`UNKNOWN` 表示不能判断，绝非同义。
- `ALL`：任意 FALSE → FALSE；无 FALSE 但有 UNKNOWN → UNKNOWN；全 TRUE → TRUE。
- `ANY`：任意 TRUE → TRUE；无 TRUE 但有 UNKNOWN → UNKNOWN；全 FALSE → FALSE。
- `NOT`：TRUE/FALSE 互换，UNKNOWN 仍 UNKNOWN；`refuted` 不得简单反转成任意其他事实。
- `authorizable` = 全部必要条件 TRUE、无未解决实质反证、条款版本与适用性通过、未触发 HARD-GATE。
- 明确条件 FALSE → `not_established`（不能宣称已成立）；未知/冲突/例外待核/法规不确定 → `needs_review`；输入伪造、source hash 不一致、非法结构、模型自授权 → `rejected`。
- 即使普通事项的已知部分可成文，也不能把未决事实“补足”为正式违规；风险高的违法、违纪、虚开、串通、挪用、损失/责任结论独立配置更高门槛，且必须人工最终核验。
- 条件表达式使用 allowlist 操作符 + 明确类型；禁止 `eval`、动态 Python、任意生成的可执行规则；规则数据不能含任意 prompt 执行指令。
- `DecisionTrace` 逐条记录每个条件对应 FactAssessment、证据跨度及理由；支持按版本回放。

### 3.4 反证/冲突机制

对相同主体、客体、期间、金额和谓词建立支持/反驳图，区分直接矛盾、日期口径不同、审批/交付/验收不同事件、情况说明与外部原始凭证；不能按文本相似就判矛盾。冲突达到影响正式结论条件时，该条件 UNKNOWN，返回 `needs_review`。不允许多数模型一致投票自动消除原始证据冲突。

### 3.5 通用范围与渐进扩展

第一阶段重点覆盖 `FY`（附件缺失/支出真实性）、`CG`（采购程序与例外）、`SW`（发票对象）三个专业族；V2.2.4 所有 12 主类保持可用。其他类别可先生成有证据引用的事实整理和待核实，禁止宣称“通用引擎已覆盖所有违法定性”。逐族制定 predicate registry、RuleDefinition、正反例，专业 reviewer 签署后才开放正式结论。

## 4. 法规知识体系：原件、版本、条款、规则投影分层

### 4.1 LawDocument / LawVersion / LawProvision

- `LawDocument`：稳定身份以发布机关、文号、文件性质、发布日期及官方识别号为主，多机关或无文号文件按人工去重决策；标题/URL 单独不得视为唯一主键。
- `LawVersion`：`version_id`、`document_id`、`promulgated_at`（公布）、`published_at`（网页公开）、`effective_from`（施行）、`effective_end_exclusive`（若能证实）、`status_as_of`、`status_evidence`、`official_source_id`、`raw_sha256`、`text_sha256`、`review_state`、`reviewed_by`、`reviewed_at`、`supersedes_versions`、`change_event_ids`。
- `LawProvision`：`provision_id`、`version_id`、`article_path`、`ordinal`、`text`、`text_sha256`、`official_locator`；同一条号在不同版本下是不同 `provision_id`。人工确认条款拆分/合并与条号变化，不能仅用序号对照。
- `LawRuleBinding`：`version_id` + `provision_id` → `rules/law-applicability.md` 的 `Law Object` ID / 适用约束 / `direct_basis|supporting_basis|liability_basis`；绑定有审核状态和自己的版本。法规文本准确≠当前案例适用。
- `LawChangeEvent`：记录变更性质、官方文件来源、影响范围、发布与生效时间、过渡条款、受影响的 Rule IDs / Finding IDs / 数据集版本。

V3 采用半开时间区间 `[effective_from, effective_end_exclusive)` 表达事实发生日的适用版本；**V2 的 `effective_to` 边界语义不能擅自转换**：须先通过现有实现+历史回归确认是含末日还是不含末日，再设计经测试的兼容投影。公布日期、施行日期、网页发现日、审计报告日严格分离。过渡规定、不同条款施行日期与上位法/下位规范并存时，无法自动判定则 `needs_review`。

### 4.2 法规数据阶段

状态机：`discovered → fetched → parsed → identity_matched → diffed → pending_review → approved/rejected/deferred → regression_passed → published`。

失败的文件永久保留可复核的候选元数据与错误记录，但**不得进入正式适用索引**。发生变更时绝不覆盖历史；旧版本从时序上停止新增适用，而符合历史时间条件的审计事项仍可引用旧版。不能把“官网页面下线”直接解释为“法规废止”。

### 4.3 官方数据源注册表（首批名单）

| source_id | 官方网址 | 用途 | 首期校验策略 |
| --- | --- | --- | --- |
| `npc_flk` | https://flk.npc.gov.cn/ | 法律/行政法规/地方性法规等 | 官方检索页 + 原文/公报校验；内部查询接口待验证 |
| `moj_admin` | https://xzfg.moj.gov.cn/ | 行政法规历史文本与沿革 | 官方现行/历史版本比对 |
| `mof` | https://www.mof.gov.cn/ | 财政、会计、预算、资金、财经制度 | 部委页面及正式文件入口 |
| `ccgp` | https://www.ccgp.gov.cn/zcfg/ | 政府采购法律法规政策 | 按发布机关与日期增量发现 |
| `tax_policy` | https://fgk.chinatax.gov.cn/ | 税费/发票相关政策 | 官方政策法规库 |
| `henan_gov` | https://www.henan.gov.cn/ | 河南省政策文件 | 官方来源交叉核验 |
| `henan_procurement` | https://zfcg.henan.gov.cn/ | 河南政府采购规则 | 必须核查具体单位级次和资金范围 |

地方市县规范性文件可进入第二批 adapter，须先确认公开来源及获取许可。用户上传的本地制度文件进入“私有候选”而非自动“全国正式法规”。技术上首批仅建至少 3 个可持续检测的官方来源 adapter（建议 `moj_admin`、`tax_policy`、`ccgp`），其他 source profiles 在完成实际访问验证后逐个启用；**不假定存在稳定公开 API**。

外部开源 `cn-law-hub`、`china-laws`、采集类项目只作为 adapter/格式/思路的参考；版本、许可证、限流、使用条款和商业再分发权限逐项复核，不把非官方仓库内容作为最终法源。

### 4.4 获取与证据归档

- 每个 adapter 实现固定接口 `discover(since_cursor)`、`fetch(identifier)`、`parse(bytes)`、`healthcheck()`；返回结构化 `candidate`、`official_url`、抓取时间、状态码、ETag/Last-Modified（若有）、raw hash、parse hash、可核查失败类型。
- 有限流、指数退避、最长超时、分页/游标幂等、条件 GET（如果支持），遵守来源许可、robots/服务条款，不绕验证码/鉴权，不以公开可浏览等同于允许批量转载。
- 内容提取无损优先，PDF 表格/图片不能用未经人工比对的 OCR 文本直接变成已核验法规。无法提取、链接失效、文本冲突时列入隔离。
- 原始文件保存独立路径/对象存储（仓库内只放依法可公开或明确获许可的样本和元数据），记录 manifest 中的 SHA、获取证据和人工核验结论。
- 发布前验证文号、机关、全文完整度、施行/废止证据、版本链无环、同一条款未误配；同题不同文号不能自动判为修订。
- 只存储及传播许可允许的文本；数据二次分发范围另行评估，不把抓取到的官方全文默认做公开 Git 仓库镜像。

### 4.5 法规变化、差异与人工审查

- `VersionMatcher`：先官方 ID/文号+机关+日期，再内容哈希/版本历史；歧义进入人工任务。
- `DiffEngine`：按条款身份做新增、删除、条号迁移、文本改写、适用时间/资金/主体/金额阈值变化；词面差异只能作为**候选变更**，不得自动得出法律效果结论。
- `ImpactAnalyzer`：从 `LawProvision` 和 `LawRuleBinding` 建反向索引，产生受影响的 `RuleDefinition`、模板、历史/现行 Finding 清单与需要复测的案例；不自动重写历史报告。
- `Reviewer Queue`：显示官方原文及页面、抽取文本、前后版本红线、变更原因、适用口径及建议测试。审核人必须显式批准、驳回或延期；关键法规至少独立复核，不允许“模型自审等于人工签署”。
- `ReleaseBuilder`：只有审批记录齐、Schema/引用/版本链/时间测试及关键回归全部通过才能生成不可变 `law-release-YYYYMMDD.N`，包含 `manifest.json`（源哈希、版本清单、规则投影哈希、审查时间、程序基线 SHA、发布状态）。发现正式版本错误则新建勘误版本，不移动旧 SHA。

### 4.6 检索与适用：两套独立的门

1. `Retrieve`：精确文号/法规名称/条款/时间检索优先，全文/BM25+中文语义向量召回补充；结果是“候选列表”，必须显示命中的**具体条款版本**。未找到不能报告“确定不存在法规”。
2. `Apply`：使用现有 `law_applicability.py` 时效→地域→主体→事项→资金→事实/证据六维，另加 `provision.version_is_approved` + `binding_review_approved` + 来源哈希核验；结果 `applicable | not_applicable | needs_review` 和逐层理由。版本不明、不生效、来源非官方或资金归属不清，绝不可升级为正式直接依据。
3. `Cite`：正式报告含法规名称、文号、具体条号、适用版本/发生日、官方 URI 与检索/核验时间。`applicable` 表示这项特定规则的适用条件通过，**不表示全部违法构成、损失/责任条件已经成立**。
4. `Reevaluate`：当新法规发布时只标记需要复核的 Finding，不后台静默修改已签发报告；历史业务坚持按业务发生时的适用法判断。

## 5. V2.2.4 接口兼容与迁移

| 现有组件 | V3 适配方式 | 不可破坏的行为 |
| --- | --- | --- |
| `SKILL.md` 13 步 | 在读取材料/Source Record 与证据等级之间插入证据图；法规过滤前加载法规 release；交付前加通用 gate | HARD-GATE 先于重大定性；自然语言可完成 A/B |
| `schemas/source-record.schema.json` | 不移除或改写已有字段；新 V3 Evidence/Fact 独立表引用旧 ID | 原始记录覆盖与金额不重计 |
| `schemas/finding.schema.json` | 保留主类/现有状态/事实/金额等；可由 adapter 生成 V2 Finding | `pending/conflicting` 不能 `final` |
| `schemas/audit-object.schema.json` | 发票门维持原机制，V3 FactClaim 经**附加**验证后映射旧 audit_objects | `authorized_sw` 仍要 v2.2.4 门重算 |
| `scripts/conclusion_grounding.py` | V3 事实图做更强上游，保留原必查结论码及文本证据校验 | 不新增无依据审核失职结论 |
| `scripts/verify_skill_delivery.py` | 作为兼容必过门；新增通用 gate 是**额外条件** | 禁止裸 bool / 未授权 SW |
| `scripts/law_applicability.py` | 经 LawRuleBinding 生成旧 Law Object 并维持原六维执行 | 旧时间/资金/来源 fail-closed；Mode A/B 成对字段 |
| `evals/result.schema.json` | 原合同 `2.2.4` 冻结；另加 `schemas/v3-result.schema.json` + 版本显式 adapter | 不偷偷把历史样例改成新预期 |
| `references/laws/**` | 既有 YAML 继续可用，生成 V3 条款/版本候选需人工核验；新 release 只能引用审核通过对象 | legacy/watchlist/historical 不自动等同现行有效 |
| `profiles/firm-default.yaml` / 模板 | 只扩展引用卡/报告配置，不调整既有默认格式 | 文本输出与机读结果一致 |

迁移按“**双轨读取、只新增、不先替换**”：
- 阶段 1：V3 引擎独立运行/影子输出，现有 V2.2.4 正式交付保持不变；收集匿名差异，不上传真实材料。
- 阶段 2：适配器实现 V3→V2 结构映射，比较分类、金额、法规、报告与拒绝语义；旧有真值集未经专业裁定不得更改。
- 阶段 3：完成独立验收后才将 V3 门纳入正式 Skill 工作流；影响 schema 的升级明确标注 `3.0.0`，不得将破坏性字段改动当 2.2.4 补丁。
- 阶段 4：法规数据更新采用独立 `law_release_id`，可回滚到前一个已审核法规 manifest，同时保留历史。

## 6. 开发实施分解与出口标准

| Task | 交付 | 前置 / 验收 |
| --- | --- | --- |
| T0 | 只读 baseline、Issue #9 遗留问题矩阵、原始测试哈希与开发分支 | 当前 main/tag/CI/旧 oracle 与未完成 Gate 明确登记 |
| T1 | V3 Schema/ID 注册表及引文定位规范 | 失败样例 RED；字段完整、无任意信任 bool |
| T2 | 文件/表格 span 和 hash/locator 校验器 | PDF/DOCX/XLSX 中英文/重复原文/扫描件 fail-closed |
| T3 | FactClaim 与状态、支持反证图 | 否定、转述、假设、时间错位、冲突例全过 |
| T4 | RuleDefinition 解释器、三值逻辑、DecisionTrace | TRUE/FALSE/UNKNOWN 负控、金额去重、审核门 |
| T5 | FY/CG/SW 三族专业规则与用户可见认定依据卡 | 各有正/反/临界/例外；V2 发票门不变 |
| T6 | LawDocument/Version/Provision/Change/Release Schema + V2 LawObject adapter | 历史/时间边界/条号/来源证据可复算 |
| T7 | 首批至少 3 个官方 adapter 的发现/抓取/差异原型 | 真实来源可访问实测、限流/故障降级；禁止自发发布 |
| T8 | 变更审核队列、影响分析、不可变法规包及 GH PR 流程 | 无审核绝不发布，旧版可回放 |
| T9 | 集成 Skill+ A/B 报告、完整 Holdout、独立审查、发布门 | 达到 §7 所有硬门才申请合并与发布 |

建议 T0/T1 先完成并停在一次**设计 Gate**：先审核 schema 和旧版兼容合同，再编码大规模采集。ZCode 可以自主处理常规 RED→GREEN、小批次提交和 review，但不能放宽任意安全/验收门。

## 7. 独立验收与停发门（非宣传性测试）

### 7.1 Baseline 与不可改写历史

- 保留发布 `v2.2.4` 的原始正式 26-case oracle、旧 352 pytest 与原始 raw/manifest；实际迁移时用当前仓库完整测试新跑验证。**不能靠改 expected 追绿**。
- Issue #9 记录的 holdout 14/26、若干 Schema 字段失败及 h07/h08/h16 语义偏差必须先做根因分类；剩余 12 条真实执行，保留 first-valid 和历史失败，不允许更名为已完成。
- 如设计实施需冻结新的 Gate D，定义一次候选 SHA、Schema、scorer、案例、模型及调用参数；只在所有预审缺陷修复后开始正式新一轮运行。

### 7.2 新增验收矩阵

| Gate | 指标 | 阻断条件 |
| --- | --- | --- |
| A Schema | 所有对象 Schema/引用完整性通过；非法键、丢 ID、错误时间格式拒绝 | 数据不可复算/自授权 |
| B 来源 | 每个正式事实引用证据原字节+解析快照+精确 locator，回查 100% | 虚构页码/引文/来源 hash 不一致 |
| C 语义 | FY/CG/SW 每类不少于 12 个新增正反临界变形测试；预注册独立 holdout ≥ 36 例 | 否定/假设当肯定，缺材料推未履行 |
| D 安全 | 虚开、串通、挪用、损失、责任等**无据严重定性 0 例** | 任一未经授权严重结论 |
| E 冲突 | 日期、主体、事件、资金与原始资料冲突检出且阻断错误正式结论 | 静默忽略重要反证 |
| F 金额 | Source Record 唯一覆盖、凭证金额去重/Decimal 精确核算 | 任一重复计金额或非空漏项 |
| G 法规 | 官网/条款/版本/官方哈希/六维适用核验齐；不同施行日期边界通过 | 旧法套新事、现行法倒推历史、非官方直接依据 |
| H 更新 | 新增/修订/废止/失效、标题同名、条号迁移、PDF OCR、网页中断等测试 | 无审核发布、旧版本被覆盖、异常当废止 |
| I 兼容 | 26 历史案例回归、原 V2 专业裁定、报告 A/B、原 gate/CI 全部通过 | 一处旧正确行为受损 |
| J 真实运行 | 真实安装树无 eval 泄漏；自然语言 A/B 各完成至少 2 套不同素材的脱敏端到端报告 | 仅 deterministic fixtures 绿而真实使用失败 |
| K 独立复核 | 新鲜上下文非实现 reviewer 对代码、法源、证据、规则、发布 manifest 审查 0 Critical / 0 Important | 任意 Critical/Important 未关闭 |
| L 可追溯 | 每次正式决策/法规引用可重放并指到同一固定 SHA，失败证据归档 | 原始 output 丢失或无法重现 |

对没有真实来源许可或持续接口的 adapter，只能标记 `experimental`；**不能拿模拟数据通过代替实网验证**。若高风险场景在独立 holdout 有一例 FAIL → `BLOCKED`，保留完整错误与下一版本修复方案，不可在同一冻结候选上偷改 scorer、oracle 或重抽样。

### 7.3 用户可核查交付

至少交付：
1. 合成/脱敏的 PDF/Excel/Word 输入，各 1 套带原始引用定位。
2. 一份证据→事实→规则→法规→Finding 的完整 `DecisionTrace` 与可读依据卡。
3. 法规版本更新差异与人工批准记录；不可变 `LawRelease` manifest 与回滚证明。
4. Mode A / B 完整中文审计报告、问题数量/金额重算表、缺证事项清单。
5. 自动测试报告、变异/对抗报告、独立 reviewer 结果及完整 first-valid runtime 运行证据。
6. 使用说明、已知边界、故障恢复说明和专业 CPA 最终复核声明。

## 8. 风险登记与设计决策

| 编号 | 风险 | 控制 |
| --- | --- | --- |
| R01 | OCR 错字被当成事实 | 解析置信度只标识文本质量；原图定位，低质量人工复核 |
| R02 | 转述、反证、否定语义反转 | polarity/modality/scope + 专业语义检查 + 固定负控 |
| R03 | 单证据与多证据冲突 | evidence graph，冲突 UNKNOWN，不能以多数表决覆盖 |
| R04 | 法规网站失效、反爬/条款调整 | adapter 失效隔离、缓存保持旧已审核版、不得无来源自动更新 |
| R05 | 官网引用旧版本或过渡条款 | 版本证据、条款级效力、有效日期分离、人工审批 |
| R06 | GitHub 公共仓库泄漏 | 只上传合成/脱敏案例和公开允许数据；本地私有 raw |
| R07 | 法规版权/使用政策 | 官方授权、请求频率、镜像范围审查；只存合法可用文本 |
| R08 | 误称合规或已通过验收 | manifest/独立 gate/issue checkpoint 强制真实状态 |
| R09 | 复杂度扩张致旧版回归 | 影子运行、最小适配、旧门不变、可回滚 |
| R10 | 审计人员过度依赖模型 | 高风险人工签署、结果和来源可见、不得 AI 自动签署 |

## 9. 公开来源与参考（设计输入，非稳定 API 保证）

- 国家法律法规数据库：https://flk.npc.gov.cn/
- 司法部国家行政法规库：https://xzfg.moj.gov.cn/（历史修订版本与沿革）
- 财政部：https://www.mof.gov.cn/
- 中国政府采购网：https://www.ccgp.gov.cn/zcfg/
- 国家税务总局政策法规库：https://fgk.chinatax.gov.cn/
- 河南省人民政府：https://www.henan.gov.cn/
- 河南省政府采购网：https://zfcg.henan.gov.cn/
- 候选外部代码参考：https://github.com/ZongziForu/cn-law-hub；使用前验证当前许可证/来源和接口稳定性。

## 10. 本规范的验收定义（与代码发布验收区分）

设计进入“APPROVED”须满足：①数据模型字段/ID/定位/日期边界可直接转为 Schema；②三值与专业授权决策表无歧义；③至少 3 个首批真实来源的接入/降级方案、法律许可检查清单明确；④完整兼容矩阵；⑤测试 oracle 与独立 reviewer 安排明确；⑥专业 reviewer 核查实际适用法律，不把示例规则当法律结论；⑦所有未确定事项标明阻断或试验条件。

**当前状态是 DRAFT；经 review 之前，ZCode 不能把此文档当成已批准的产品实现，也不能据此直接发布 V3.0。**

## 11. V3.0 开源能力复用矩阵（本设计的规范性组成部分）

详情：[`2026-11-19-v3-open-source-capability-matrix.md`](./2026-11-19-v3-open-source-capability-matrix.md)。**该文档与本技术规范具有同等设计约束效力**；不允许只在计划中提到、实际开发时遗漏。

**本轮必须纳入并经独立审查的设计能力：**
- OS-01 官方法规智能检索：参考 `cn-law-hub`，规范 `LawSearchProvider`、精确/全文检索及“检索候选不等于正式适用”边界。
- OS-02 法规自动更新：参考 `Law-Crawler-RPA-RAG-MCP`、`china-laws`，规范 source adapter、差异审核、不可变版本、GitHub PR 和发布回滚。
- OS-03 PDF/Word/Excel/扫描件原文定位：对 `Docling` 与 `MinerU` 进行统一合成样本选型比较，规范 `DocumentParserAdapter`、parser_run 快照、字符/页/行/单元格引用与 fail-closed；**不能只设计数据表而不定义真实解析接口和选型验证**。
- OS-04 审计证据链底稿：参考 `cpa-skills`、`accounting-ai-skills`，规范 `AuditWorkingPaper` 视图、证据回跳、事实/反证、版本法规、复核状态和 MD/DOCX 导出；禁止模型冒充人工签署。

**本轮仅预留接口、不得扩张实现范围：** OS-05 审计抽样与异常凭证识别、OS-06 银行流水核对/金额勾稽、OS-07 XBRL 财报分析。未来它们生成的候选也必须通过通用 Evidence/Fact/Rule 门，不能凭异常算法或财报模型输出直接发射正式 Finding。

**设计 Gate 新增四项：** 前四项分别提供输入输出契约、第三方许可证/隐私与接口可行性调查、失败降级策略、可独立验收样本；必须在 `docs/validation/v30-third-party-evaluation.md` 给出 `adopt|wrap|reference_only|reject|pending_review` 的结论。未实际核验的开源项目不得写“已集成”。
