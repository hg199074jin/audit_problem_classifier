# Audit Problem Classifier V2 架构设计

**日期：** 2026-09-30  
**状态：** Design Approved / Awaiting Written Spec Review  
**基线：** `main@4fb9f9e`  
**目标版本：** V2.0  
**仓库：** `hg199074jin/audit_problem_classifier`

## 1. 设计目标

V2 的目标不是继续扩充一个更大的 `laws.md`，而是把当前“审计问题报告化 Skill + Markdown 法规清单”升级为一个可复核、可追溯、可持续维护的 **Audit Finding Engine（审计问题认定引擎）**。

V2 必须同时解决以下问题：

1. 法规条文本身是否准确、现行、可追溯；
2. 法规是否适用于当前地区、单位层级、单位性质、业务类型、资金性质和业务发生年度；
3. 原始问题如何拆成独立 Finding，并保证原始记录数、凭证金额不重复统计；
4. 证据强度与定性措辞如何匹配，避免“嫌疑写成认定”“占用写成挪用”“少收写成损失”等升级错误；
5. 修改 Skill、法规或案例后，如何用自动化回归测试证明没有退化；
6. 如何保留“先问清、后动手”的 HARD-GATE，同时避免对稳定格式和既有事务所口径反复提问。

## 2. 非目标

V2.0 不追求一次性收录全国全部审计法规，不建设通用法律数据库，不自动替代审计人员作最终责任认定，也不以联网搜索替代本地稳定法规库。

V2.0 优先保证：**少量高质量法规 + 正确适用机制 + 明确的未知状态 + 可回归验证。**

## 3. V1 已确认的主要结构性问题

### 3.1 法规“准确”与“适用”混在一起

当前三级库主要按可信程度区分：

- 第一级：已人工采用；
- 第二级：AI 辅助检索；
- 第三级：分类清单。

该结构能反映“来源可信度”，但无法表达：

- 该法规是否仍有效；
- 何时生效、何时失效；
- 河南省级、郑州市级、其他市级、县级是否适用不同标准；
- 行政单位、事业单位、企业、干部、普通职工是否属于适用对象；
- 是否仅适用于政府采购、政府购买服务、培训、差旅等特定业务；
- 某条是否为直接义务依据、原则性依据或责任处理依据。

V2 必须把 **可信度** 与 **适用性** 拆成两个独立维度。

### 3.2 Markdown 法规清单不是法规数据模型

当前 `references/laws.md` 无法稳定表达版本、地域、效力、适用条件、排除条件、替代关系和来源核验信息。

V2 需要结构化 Law Object，Markdown 仅作为人类可读展示层。

### 3.3 SKILL.md 职责过多

当前 `SKILL.md` 同时承担：

- 决策门；
- 分类体系；
- 证据与定性；
- 法规检索规则；
- 金额与覆盖；
- 报告格式；
- 输出模板。

V2 将其收敛为“编排与决策工作流”，领域规则移入独立模块。

### 3.4 案例库与规则库边界不清

真实项目案例具有高价值，但不应反向成为通用规则本身。V2 中：

- 规则定义“必须怎样判断”；
- 案例只用于说明边界和回归测试；
- 项目特有经验不得无条件提升为全局规则。

### 3.5 test-prompts.json 不是完整的回归评测

当前测试可读但不可系统判断退化。V2 需要按失败类型拆分 eval，并至少覆盖：

- 分类；
- 法规适用；
- 时效；
- 地域；
- 主体；
- 证据—措辞；
- 金额去重；
- 报告格式。

## 4. 总体架构

```text
audit_problem_classifier/
│
├── SKILL.md
├── README.md
├── agents/
│   └── openai.yaml
│
├── rules/
│   ├── decision-gate.md
│   ├── classification.md
│   ├── evidence-and-wording.md
│   ├── law-applicability.md
│   └── coverage-and-amount.md
│
├── schemas/
│   ├── project-context.schema.json
│   ├── source-record.schema.json
│   ├── finding.schema.json
│   └── law.schema.json
│
├── references/
│   ├── laws/
│   │   ├── national/
│   │   ├── henan/
│   │   ├── kaifeng/
│   │   ├── historical/
│   │   └── watchlist/
│   ├── cases/
│   ├── management-suggestions/
│   └── report-templates/
│
├── profiles/
│   └── firm-default.yaml
│
└── evals/
    ├── classification.jsonl
    ├── law-applicability.jsonl
    ├── evidence-wording.jsonl
    ├── amount-coverage.jsonl
    └── report-format.jsonl
```

## 5. 核心对象

### 5.1 Project Context

每个项目在正式分类前建立一次项目上下文，用于后续法规适用判断。

最小字段：

```yaml
jurisdiction:
  country: CN
  province: Henan
  city: Kaifeng

organization:
  level: municipal
  type: public_institution

audit_period:
  start: 2025-01-01
  end: 2025-12-31

funding:
  - fiscal_funds
  - own_funds

report_mode: special_audit_report
profile: firm-default
```

原则：

- 已知稳定事实不重复问；
- 缺失且会改变定性或法规适用的字段进入 HARD-GATE；
- 纯格式事项优先从 profile 读取，不进入 HARD-GATE。

### 5.2 Source Record

Source Record 表示原始问题、凭证或记录本身，是覆盖和金额统计的基准。

必须保持唯一 `source_record_id`，不得因为拆分 Finding 而复制原始记录统计口径。

### 5.3 Finding

Finding 是独立审计认定单元。

一个 Source Record 可以产生多个 Finding，例如：

```text
Source Record #17
├─ Finding A：绩效工资管理问题
├─ Finding B：账外资金问题
└─ Finding C：个人所得税扣缴问题
```

每个 Finding 至少包括：

- `finding_id`
- `source_record_id`
- `primary_category`
- `secondary_type`
- `facts`
- `evidence_status`
- `amounts`
- `decision_status`
- `law_candidates`
- `final_wording`

金额字段必须区分：

- `voucher_amount`
- `issue_amount`
- `confirmed_difference`
- `pending_amount`

### 5.4 Law Object

法规条款必须作为结构化对象保存。示例：

```yaml
id: CN-INVOICE-2023-ART20

title: 中华人民共和国发票管理办法
article: 第二十条
issuer: 国务院
legal_level: administrative_regulation

status: effective
effective_from: 2023-07-20
effective_to: null

jurisdiction:
  - CN

subject_scope:
  - all_units
  - individuals

business_scope:
  - invoice
  - reimbursement

rule_role: direct_basis

text: 不符合规定的发票，不得作为财务报销凭证，任何单位和个人有权拒收。

applies_if:
  - invoice_noncompliant == true

excludes_if:
  - issue_only_concerns_supporting_documents == true

source:
  type: official
  authority: State Council / Tax Authority
  verified: true
  verified_at: 2026-09-30

supersedes:
  - CN-INVOICE-OLD-ART21
```

## 6. 法规适用性判断

法规选择必须先过滤，再排序，禁止只按关键词匹配。

### 6.1 前置过滤顺序

1. **时效**：业务发生日是否落在法规有效期；
2. **地域**：国家、省、市、县适用范围是否匹配；
3. **主体**：行政单位、事业单位、企业、干部、普通职工等是否匹配；
4. **事项**：是否属于政府采购、政府购买服务、差旅、培训、资产处置等；
5. **资金**：财政资金、非财政资金、工会经费、专项资金等是否影响适用；
6. **证据**：现有证据是否达到该条款所要求的事实前提。

任一关键条件未知且会改变结果时，不得自动选定正式依据，应转入 HARD-GATE 或“法规依据待核验”。

### 6.2 法规角色

每条法规候选在 Finding 中必须标记角色：

- `direct_basis`：直接规定应当/不得如何；
- `supporting_basis`：原则性、真实性、内部控制等补充依据；
- `liability_basis`：处理、处罚、处分、追责依据。

默认输出顺序：

```text
direct_basis → supporting_basis
```

`liability_basis` 不得因为问题看起来严重而自动加入，只有用户明确需要处理处罚或责任分析，且事实前提满足时才进入输出。

## 7. HARD-GATE V2

“先问清，后动手”继续作为最高原则，但分为两类。

### 7.1 必须阻断的重大事项

以下事项未解决前不得形成正式认定：

- 原始记录是否纳入；
- 是否拆成多个独立 Finding；
- 主分类存在实质冲突；
- 凭证金额、问题金额、差额金额口径冲突；
- 重大定性升级；
- 法规适用范围取决于未知地区、单位层级、人员身份、年度或资金性质；
- 正式问题与待核实事项之间的取舍。

### 7.2 不再反复询问的配置事项

以下事项进入 `profiles/firm-default.yaml`：

- 日期格式；
- 金额格式；
- 中文引号；
- 凭证引用格式；
- 普通费用标题归并习惯；
- 报告编号和章节风格；
- 已稳定的事务所写作习惯。

原则：**重大判断人工决策，稳定习惯配置化。**

## 8. 证据与措辞

继续保留 V1 已验证有效的定性梯度：

```text
管理不规范/不到位
→ 内部控制缺陷
→ 违反财经纪律
→ 涉嫌违法违规
```

V2 将其独立为 `rules/evidence-and-wording.md`，并要求每个高风险词绑定最低证据条件。

典型反向约束：

- 关联、报价异常 → “存在串通报价嫌疑”，不得直接写“串通投标”；
- 应缴款大于可用资金 → “未及时足额上缴/部分被占用”，不得直接写“截留、挪用”；
- 尚可追收 → “少收应收款项”，不得直接写“造成损失”；
- 发票信息异常 → “记载信息不准确/未如实开具”，不得仅凭异常写“虚开发票”；
- 合同晚签 → “先履行后签订书面合同/事后补签”，不得自动写“倒签合同”。

## 9. SKILL.md V2 职责

V2 的 `SKILL.md` 只保留工作流和调用顺序：

```text
读取材料
→ 建立 Project Context
→ 生成待决策事项
→ HARD-GATE
→ 构建 Source Records
→ 拆分 Findings
→ 分类
→ 证据等级
→ 法规适用过滤
→ 定性措辞
→ 报告化输出
→ 覆盖/金额/法规/格式自检
```

分类细则、法规细则、报告模板不得继续在 SKILL.md 大量重复。

## 10. 法规目录策略

法规按地域和状态拆分：

### national/
保存全国现行上位法、行政法规、财政部规章、国家统一会计制度等。

### henan/
保存河南现行政策，并允许进一步表达省级、郑州市、其他市级、县级差异。

### kaifeng/
仅保存开封地方制度和确有长期复用价值的市级政策。

### historical/
保存已废止、被替代但仍可能适用于历史业务期间的法规，不参与“当前有效法规”默认搜索。

### watchlist/
保存已公布但尚未生效、疑似修订、来源未完全核验、需要定期复核的规则。

## 11. V2.0 首批法规修复范围

V2.0 不追求一次性全面扩库，但必须先解决已确认的 P0 风险：

1. 现行《中华人民共和国发票管理办法》条款号更新；
2. 河南政府采购限额按单位层级和采购类型条件化；
3. 已废止公务用车旧办法移入 historical；
4. 已废止评比达标表彰试行办法替换为现行办法；
5. 已废止廉洁从政旧准则移入 historical；
6. 行政单位会计制度、事业单位会计准则等旧会计制度移入 historical；
7. 原《基本建设财务管理规定》移入 historical；
8. 政府购买服务“变相用工”主依据升级为财政部令第102号；
9. 公务员奖励依据更新为现行《公务员奖励规定》。

这些修复属于 V2 迁移的最低安全基线。

## 12. Evals 设计

V2 使用行为回归而不是只检查文本存在。

### classification.jsonl

验证 FY/KJ/SW、CG/NK、ZC/KJ 等边界。

### law-applicability.jsonl

必须包含至少以下反向测试：

- 河南开封市级事业单位 80 万元服务采购，不得因为“低于100万元”直接排除政府采购适用；
- 2025 年事项不得调用 2026 年以后才生效的政策；
- 事业单位普通职工不得自动适用仅针对干部的条款；
- 企业职工教育经费规定不得作为事业单位普通职工直接依据；
- 历史法规只有业务发生日在其有效期内才可调用。

### evidence-wording.jsonl

验证“嫌疑/认定”“占用/挪用”“少收/损失”“补签/倒签”等。

### amount-coverage.jsonl

验证：

- 一个 Source Record 拆多个 Finding；
- 原始记录数只计一次；
- voucher_amount 不重复汇总；
- issue_amount 与 confirmed_difference 分离。

### report-format.jsonl

验证日期、金额、中文引号、凭证格式、表格规则、法规段规则。

## 13. Skill-TDD 维护规则

以后每一次真实项目返工按以下流程进入 V2：

1. 把返工案例匿名化；
2. 先写成一个失败 eval；
3. 确认旧版本确实失败；
4. 修改最小规则；
5. 验证新版本通过；
6. 跑完整回归集；
7. 再合并。

禁止先修改规则，再补测试为修改结果背书。

## 14. V2 实施分期

### V2.0-A：安全修复

修复已确认 P0 法规错误，建立 historical/watchlist 概念。

### V2.0-B：数据模型

建立 Project Context、Source Record、Finding、Law schema。

### V2.0-C：规则拆分

将 `SKILL.md` 中分类、证据、法规、金额规则迁移到独立 rules 文件。

### V2.0-D：法规迁移

将核心高频法规从 `laws.md` 迁移为结构化 Law Objects，并保留可读索引。

### V2.0-E：自动化 Evals

把现有 `test-prompts.json` 迁移为分领域 jsonl 回归集。

### V2.0-F：兼容与发布

保证 V1 的模式A、模式B输出能力保留，README、Agent 配置、示例同步更新。

后续：

- V2.1：补齐国家高频法规包；
- V2.2：补齐河南法规包；
- V2.3：按真实项目补开封与专项法规；
- V2.4：增加“缺失或高时效法规”的联网核验路径。

## 15. 兼容性要求

V2 不改变用户已经认可的以下核心行为：

- “先问清，后动手”；
- 每条原始问题原则上只有一个主分类；
- 可拆多个独立 Finding；
- 证据不足不升级重定性；
- 模式A与模式B继续保留；
- 正式稿继续执行现有格式硬规则；
- 审计人员保留最终复核权。

## 16. 验收标准

V2.0 达到可发布状态必须同时满足：

1. 已确认 P0 法规错误全部修复；
2. 所有现行法规对象均带效力状态和核验信息；
3. 关键河南规则能按省级/郑州/其他市级/县级正确过滤；
4. historical 法规不会进入当前年度默认候选；
5. Finding 拆分后覆盖数量和金额无重复；
6. 高风险措辞有负向 eval；
7. 原有 6 个测试场景全部迁移并继续通过；
8. 新增时效、地域、主体、证据边界测试；
9. 模式A、模式B至少各有一个完整回归案例；
10. 不存在“法规不确定但仍输出为已核验直接依据”的路径。

## 17. 关键设计决策

- 采用 **Hybrid V2**：本地结构化法规库为主，联网只处理缺失、高时效和待核验事项；
- 不采用“所有问题实时联网查法规”，避免速度慢、结果不可重复、政府网站抓取不稳定；
- 不追求一次性收录全部法规；
- 先建设正确的适用性机制，再扩充法规数量；
- 重大判断保留 Human Gate，格式习惯配置化；
- 规则、案例、法规、报告模板、Evals 分离，避免互相污染；
- V2 首要质量指标是“不会在不适用时自信引用”，其次才是法规覆盖率。

## 18. V2 成功后的系统定位

V1 的核心能力是：

> 把零散审计发现整理成像专业审计人员写出的正式问题。

V2 的核心能力升级为：

> 对每个审计问题明确事实、证据、分类、适用法规、定性强度和报告表达，并能解释为什么适用、依据哪个版本，同时通过回归测试证明规则修改没有破坏既有能力。

因此，V2 的长期定位不再只是 `audit_problem_classifier`，而是一个可持续演化的 **Audit Finding Engine**。
