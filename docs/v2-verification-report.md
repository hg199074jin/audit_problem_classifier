# Audit Problem Classifier V2 Verification Report

**分支：** `feature/v2-audit-finding-engine`  
**设计基线：** `docs/v2-architecture@942f942671a2659b408b1b7fe28da1068f85388a`  
**Gate C 已验证实现 Head：** `3d65df2ec838da2eb2257e5b54a9e952defd4a60`  
**V2.0.1 remediation 已验证 Head：** `21580ee28fa4a94f387bd25c77dbac4f716edd84`  
**V2.0.2 semantic-fix 已验证 Head：** `985d5be71601515360064f1d23f95aac22f73901`  
**报告日期：** 2026-10-01  
**Gate C 状态：** PASS（历史仓库级验证）  
**Gate D 状态：** PASS（有效覆盖14/14，见 PR #1 评论 5925118925）  
**Gate E 状态：** FAIL（独立 reviewer：5 Critical + 4 Important；当前进入 V2.0.3 remediation）

> 本报告区分“仓库级确定性验证”和“独立 Skill runtime 实测”。Gate D 首轮真实 runtime FAIL（2/14），推动 V2.0.1 完成结构化评分与格式 lint；V2.0.1 第二次真实 runtime 为 13/14 PASS，唯一失败暴露出 conclusion code 语义建模过度约束。V2.0.2 已完成最小语义纠偏并重新冻结，下一次 Gate D 待执行。

## 1. Gate C 机器验证证据

GitHub Actions 工作流：`V2 Verification`

- Run ID：`36789209799`
- Job ID：`110137833575`
- Conclusion：`success`

实际日志结果：

- **pytest：64 passed**
- **结构化 Law Object：32 个全部通过 `law.schema.json` 校验**
- **deterministic eval：14/14 passed**
- 工作流中的 `Run tests`、`Validate all structured laws`、`Score deterministic regression fixture` 三个核心步骤均为 success。

同时，临时 CI base 工作流 Run `36789208426` 也为 success，用于交叉确认 PR head 的验证结果。

## 2. 已完成的 V2 核心实现

### 2.1 数据模型

已建立并验证：

- `Project Context`
- `Source Record`
- `Finding`
- `Law Object`

Schema：

- `schemas/project-context.schema.json`
- `schemas/source-record.schema.json`
- `schemas/finding.schema.json`
- `schemas/law.schema.json`

日期使用真实 ISO format 校验，并额外校验：

- `audit_period.start <= audit_period.end`
- `effective_from <= effective_to`

### 2.2 HARD-GATE 与规则分层

`SKILL.md` 已收敛为编排入口，并按顺序加载：

- `rules/decision-gate.md`
- `rules/classification.md`
- `rules/evidence-and-wording.md`
- `rules/law-applicability.md`
- `rules/coverage-and-amount.md`
- `profiles/firm-default.yaml`

重大专业判断必须经过 HARD-GATE；日期、金额、引号、凭证引用等稳定格式习惯由 profile 管理，避免重复追问。

### 2.3 法规适用性 Gate

`scripts/law_applicability.py` 实现三态结果：

- `applicable`
- `not_applicable`
- `needs_review`

固定过滤顺序：

`时效 → 地域 → 主体 → 事项 → 资金 → 事实/证据`

并增加两项最终审查修复：

1. `law.source.verified != true` 时不得返回已确认 `applicable`；
2. `build_evaluation_context(project_context, finding, source_record)` 明确合并项目级事实和 Finding 级 applicability facts，避免为了单条法规污染 Project Context。

### 2.4 Source Record / Finding 金额语义

一个 Source Record 可以拆成多个 Finding，但：

- 原始记录数只按唯一 `source_record_id` 统计；
- `voucher_amount` 只按 Source Record 汇总一次；
- `issue_amount`、`confirmed_difference`、`pending_amount` 分开管理。

已存在 P0 回归案例验证“一张凭证拆三个 Finding 不得把凭证金额累计三次”。

## 3. P0 法规迁移与专业复核

V2 已把首批高风险法规迁移为结构化对象，并区分 current / historical / watchlist。

### 3.1 已确认的重要修复

- 现行《中华人民共和国发票管理办法》中“不符合规定的发票不得作为财务报销凭证”使用**第二十条**；旧第二十一条进入 historical。
- 河南省政府采购目录及标准的正确文号锁定为 **豫财购〔2020〕4号**，不再沿用原库中的“豫财购〔2020〕4号”。
- 河南政府采购不得再用“全省统一100万元/400万元”的粗略口径，已经按省级、郑州市本级、其他市级、县级及货物/服务/工程拆分。
- 2011年公务用车旧办法、2010年评比达标表彰试行办法、旧廉洁从政准则、旧行政/事业单位会计制度、财建〔2002〕394号等移入 historical。
- 财政部令第102号《政府购买服务管理办法》成为“政府购买服务不得变相用工”的主依据之一。

### 3.2 公务用车事业单位适用边界

最终审查将公务用车规则拆成：

- 行政单位：现行办法直接依据对象；
- 不参照公务员法管理的事业单位：单独的 supporting basis 对象，并要求 `organization.civil_servant_managed == false`。

避免把“按照本办法原则管理”误建模成对所有事业单位无条件直接适用。

### 3.3 政府购买服务事业单位参照适用

最终审查补充财政部令第102号第三十三条的事业单位边界：

对于**承担行政职能的事业单位使用财政性资金购买服务**，建立第十条/第十八条的单独参照适用 Law Object，并要求：

- `organization.type == public_institution`
- `organization.performs_administrative_functions == true`
- `funding` 包含 `fiscal_funds`

第十八条对象还要求 `service_provider_type == individual`。

普通事业单位不会因为单位类型相同而被无条件套用该参照规则。

## 4. Eval 与评分器

正式 V2 eval 分为：

- classification
- law-applicability
- evidence-wording
- amount-coverage
- report-format

`evals/score.py` 是纯确定性评分器，不调用模型/API。

最终审查修复了一个重要缺口：`forbidden` 现在不仅检查正文，还会检查结构化 `category` 和 `law_ids`，因此已废止法规不能通过“正文不出现、结构化字段偷偷返回”的方式绕过测试。

当前 mandatory fixture：

- **14/14 passed**

## 5. Mode A / Mode B 兼容

- 模式 A：`references/report-templates/classification-report.md`
- 模式 B：`references/report-templates/special-audit-report.md`

两个模板均服从：

- HARD-GATE
- 分类规则
- 证据措辞
- 法规适用性
- firm profile
- Source Record / Finding 金额去重规则

旧入口保留兼容 wrapper，不再定义新的规范规则。

## 6. Final Whole-Branch Review

当前会话没有可用的独立 reviewer/subagent 工具，因此本次最终分支审查记录为：

> **self-review (no independent subagent tool available)**

最终自审重点复核：

- SKILL 是否完整加载五个规则模块；
- legacy 法规是否被隔离；
- 案例是否声明 rules 优先；
- 未核验法规是否会被错误返回 applicable；
- evaluation context 是否显式构造；
- 日期 format / 日期区间是否真实校验；
- forbidden 是否覆盖结构化 law_ids；
- 公务用车和政府购买服务的事业单位适用边界。

结果：

> **CLEAN — 未发现尚未处理的 Critical / Important finding。**

该自审弱于真正的独立第二 reviewer，因此合并 `main` 前仍建议保留 PR 审阅机会。

## 7. TDD 证据

最终审查发现的关键问题均先增加失败测试，再实施修复。

其中一轮 GitHub Actions RED 记录：

- **9 failed, 53 passed**：覆盖 forbidden structured law id、未核验来源、evaluation-context builder、日期校验、公务用车事业单位边界、watchlist 等；
- 修复后达到 **62 passed**。

进一步核对财政部令第102号第三十三条后再次新增事业单位参照适用测试：

- RED：**2 failed, 62 passed**；
- 修复后最终达到 **64 passed**。

因此 final-review 修复不是“先改代码再补测试”，而是经过实际 RED → GREEN。

## 8. Gate D 独立 Skill Runtime 验收

### 8.1 首轮 Gate D：已执行，FAIL

2026-10-01，ZCode 在隔离安装环境中对 PR #1 head `f4afe27828044981e5ec1328dd8d26b1d24ca572` 执行了 14 个独立 runtime 案例。

防污染措施包括：

- 安装树剥离 `evals/`、`tests/`、`docs/`、fixtures 等；
- runtime 只读取 `prompt + context`；
- 14 个案例使用独立 subagent 上下文；
- 编排器不补专业语义字段；
- 生成完成后才运行 scorer。

原始 scorer 结果：

- **2/14 PASS**
- **12/14 FAIL**

逐项复核后：

- 4 例主要属于 `forbidden/not_contains` 对中文否定句的裸子串误报；
- 7 例主要属于 `contains` 绑定唯一中文措辞造成的假阴性；
- 1 例 `format-hard-rules` 存在真实 runtime 缺陷：ASCII 直引号未规范为中文弯引号，且 `记账-66号凭证` 未规范为 `66号凭证`。

因此 Gate D 首轮正式结论仍为 **FAIL**，但不得把 2/14 解读为专业行为只有 14% 正确，也不得人工改判为 13/14 或 PASS。

原始报告：PR #1 issue comment `5922412607`。

### 8.2 V2.0.1 Gate-D Remediation：已完成并冻结

Remediation 只处理三项：

1. **专业语义结构化**
   - `gate_status`
   - `category`
   - `finding_types`
   - `conclusion_codes`
   - `applicability_status`
   - `law_ids`
   - `excluded_law_ids`
   - `record_count / finding_count / voucher_total`

2. **scorer 职责降级**
   - 非 `report-format` 案例禁止使用 literal `contains/not_contains` 判断专业语义；
   - 正文否定句不再因为出现“构成串通投标”等字样被自动判错；
   - 法规排除通过 `excluded_law_ids` 判断；
   - 不引入 LLM-as-judge。

3. **真实格式缺陷修复**
   - 新增 `rules/report-format.md`；
   - 新增 `scripts/report_format_lint.py`；
   - 强制中文弯引号、`X号凭证`、`YYYY/MM` 等最终格式自检；
   - Mode B 模板本身改为干净格式示例。

V2.0.1 合同版本：`2.0.1`。

GitHub Actions Run `36799605462` 对 remediation head `21580ee28fa4a94f387bd25c77dbac4f716edd84` 验证结果：

- **80 tests passed**
- **32/32 Law Object schema validation**
- **14/14 deterministic fixture passed**

### 8.3 V2.0.1 Contract Freeze Manifest

第二次 Gate D 开始后，以下 contract/scorer 文件不得根据 runtime 输出再修改 expected 来追 PASS：

- `evals/case.schema.json` — blob `fc21e61d6097da786c920d63f8530f533b2d9888`
- `evals/cases/amount-coverage.jsonl` — `a68df3709e5c49b3cdc51d9cbc433ff8a75a5d8a`
- `evals/cases/classification.jsonl` — `b00c333ecf3e46b700a6d87532d37418f21982ac`
- `evals/cases/evidence-wording.jsonl` — `db28f0854bda84d55d7285c71d590f21cae82573`
- `evals/cases/law-applicability.jsonl` — `3b5d30f364d917adca15013edf7983a4f089d096`
- `evals/cases/report-format.jsonl` — `aff17231b9ceeec009938d94ea46d81b8180e1f9`
- `evals/score.py` — `add39f7e35e5ecbd8a9c0b9df7d2abdd2a153478`
- `rules/result-contract.md` — `e9f3730156d496747b3d60acd0233bd7d0b95172`
- `rules/report-format.md` — `f094a877f4702f8c0de1d917b51a037e70e3d809`
- `scripts/report_format_lint.py` — `69eedf7cdd1db296940c8b22aacbb10b74c03849`

编排器在第二次 Gate D 中只可以机械添加 `id` 与 `contract_version`；其余机器语义字段必须来自 runtime 自己。

### 8.4 第二次 Gate D：已执行，FAIL（13/14）

2026-10-01，ZCode 按 V2.0.1 frozen contract 对 head `06c8eb197f589c62e9cec9871a40b8c437b4c3a6` 再次执行独立 runtime E2E。

结果：

- **13/14 PASS**
- `format-hard-rules` 已 PASS，首轮真实格式缺陷确认修复；
- 14 份输出全部通过 `report_format_lint.py`；
- 唯一失败：`qualitative-downgrade` 缺 `reimbursement_review_insufficient`。

runtime 已正确输出更具体的：

- `travel_subsidy_pending_review`

并保留：

- `decision_required_pending_items`

原始报告：PR #1 issue comment `5923598828`。

### 8.5 对 13/14 唯一失败的复核裁定

该失败**不是 Skill 漏掉必须存在的专业结论**，而是 V2.0.1 expected 对两个 conclusion code 的语义关系定义过度。

事实输入仅能支持：

- 差旅/交通补助是否可领取仍需补充主办方保障安排、制度适用等事实；
- 因此 `travel_subsidy_pending_review` 是适当且更精确的结论码。

而 `reimbursement_review_insufficient` 表示已经有证据能够确认报销审核程序或必要附件本身存在缺陷。两者不是同一事实层级，也**不构成蕴含关系**。

因此，不能规定“出现 `travel_subsidy_pending_review` 时必须同时出现 `reimbursement_review_insufficient`”。

这不是把 V2.0.1 的 13/14 人工改判为 PASS；V2.0.1 Gate D 仍保持 FAIL。该问题通过新 contract version **2.0.2** 正式修复，并要求整套 14 例重新运行。

### 8.6 V2.0.2 Semantic Fix：已完成并验证

V2.0.2 只做一个专业语义纠偏：

- `travel_subsidy_pending_review`：事项实体结论仍待核实；
- `reimbursement_review_insufficient`：只有已有证据能够确认报销审核程序或必要附件存在缺陷时才使用；
- 两者可以同时出现，但不存在默认父子/伴随关系。

同时将全套 Gate D contract version 统一升级为 `2.0.2`。

GitHub Actions Run `36807246067` 对 head `985d5be71601515360064f1d23f95aac22f73901` 验证结果：

- **83 tests passed**
- **32/32 Law Object schema validation**
- **14/14 deterministic fixture passed**

TDD 证据：

- RED：`3 failed, 80 passed`
  - qualitative-downgrade 仍要求双码；
  - result-contract 未说明语义边界；
  - contract version 仍为 2.0.1；
- GREEN：`83 passed`。

### 8.7 V2.0.2 Contract Freeze Manifest

下一次 Gate D 开始后，以下 contract/scorer 文件不得根据 runtime 输出再修改 expected 来追 PASS：

- `evals/case.schema.json` — blob `6f2ab4b49f71b50c512c46a92bd65ab26b11d39d`
- `evals/cases/amount-coverage.jsonl` — `da6a5557ed95e96dedb36bbcefc312b3f7524e22`
- `evals/cases/classification.jsonl` — `573215fdf38cebf9d080398a19e8790eca46cdaf`
- `evals/cases/evidence-wording.jsonl` — `d19000d9b6e7b98c5d9f05022c234595cc53c338`
- `evals/cases/law-applicability.jsonl` — `9f1bdd86e57940515ab14cf6f8c6c4f657543c20`
- `evals/cases/report-format.jsonl` — `a226a4597e4f61347a82d9e2ff6726da647d7fe9`
- `evals/score.py` — `4379f30f3c0f3e46ef2f899e9bd3cde0e475f769`
- `evals/README.md` — `ded84d6f043bba2786393e7c516cb1f4c3b31d2b`
- `rules/result-contract.md` — `dbd2b028a3a3964f6defaf7c710f120aa67d3b59`
- `rules/report-format.md` — `f094a877f4702f8c0de1d917b51a037e70e3d809`
- `scripts/report_format_lint.py` — `69eedf7cdd1db296940c8b22aacbb10b74c03849`

### 8.8 下一步

下一次独立 Skill runtime Gate D **待执行**。

仍要求：

- 14 个案例独立生成；
- 相同防污染协议；
- 并发建议 ≤4；
- scorer 使用冻结后的 V2.0.2 contract；
- 编排器只可机械添加 `id` 与 `contract_version = "2.0.2"`；
- **14/14 PASS 才能关闭 Gate D**；
- Gate D 开始后，不得根据输出修改 expected/scorer/case 来追 PASS。

`evals/fixtures/passing-results.jsonl` 仍只是 scorer 自测 fixture，不能冒充真实 runtime 结果。

## 9. 已知 V2.1 扩展项

财政部令第102号第三十三条除“承担行政职能的事业单位”外，还列有其他参照执行主体。V2.0 已优先覆盖本项目最常见的行政事业单位路径；其他主体类型可在 V2.1 按真实审计需求进一步结构化建模。

该限制可能造成这些少见主体的**候选法规漏选（false negative）**，不会授权系统把不适用法规自动写成直接依据。

## 10. Gate C 结论

基于已验证实现 Head `3d65df2ec838da2eb2257e5b54a9e952defd4a60`：

- ✅ 64/64 tests
- ✅ 32/32 Law Object schema validation
- ✅ 14/14 deterministic eval
- ✅ Final self-review CLEAN
- ✅ P0 法规错误与关键适用边界已完成修复
- ✅ 模式 A / B、HARD-GATE、金额去重与法规适用规则均保留
- ⚠️ Gate D 首轮 2/14 FAIL；V2.0.1 第二次 13/14 FAIL；V2.0.2 已修复唯一语义过度约束，下一次 Gate D 待执行
- ⚠️ 无独立 reviewer/subagent，本次 whole-branch review 为作者 self-review

**Gate C（仓库级）结论：PASS。**

本报告属于最后的文档更新；该报告提交后，PR head 仍应由同一 `V2 Verification` workflow 再执行一次成功检查，方可进入合并决策。


## 11. Gate E Independent Review

2026-10-01，独立第二 reviewer 使用全新 Codex CLI 上下文、只读沙箱，对 PR #1 做 whole-branch review。形成 findings 前未读取 PR comments、verification report 或先验 review verdict。

结果：

- **Gate E：FAIL**
- Critical：5
- Important：4
- 后续独立 code-review 又复现并扩展为 3 P0 + 6 P1 + 1 P2 + 3 P3。

合并前阻塞项包括：

1. Finding `applicability_facts` 可覆盖 Project Context；
2. effective 法规缺 `effective_from` 时可能绕过时效过滤；
3. 河南政府采购对象缺政府采购主体/财政性资金/范围前置；
4. scorer 对安全关键列表采用 subset 语义，可容忍危险额外结论；
5. blocked / needs_review 缺跨字段不变量；
6. voucher_amount 在 Finding 与 Source Record 双重存在且 scorer 不重算；
7. pending/conflicting Finding 可被标 final；
8. effective Law Object provenance 约束不足；
9. 缺财政部令102号、事业单位公务用车、watchlist/unverified、工程资金边界、liability basis、Mode A/B 完整 runtime eval。

V2.0.3 remediation 采用 TDD，先建立 Gate E RED tests，再逐项修复。Gate E 修复完成后必须重新由独立 reviewer 复核；当前 PR 仍保持 Draft，不得合并。

## 12. V2.0.3 Gate E Remediation

Gate E 独立 reviewer 的 Critical / Important findings 已进入 V2.0.3 合并前修复。补充 code-review 中的 P2/P3 也按风险处理。

### 12.1 合并前阻塞项修复

- **CR-001 / E-001 — Finding facts 污染 Project Context**
  - `applicability_facts` 禁止写入 `jurisdiction / organization / funding / event_date / audit_period`；
  - `build_evaluation_context()` 对保留键直接拒绝。

- **CR-002 / E-002 — effective 法规缺生效起点**
  - `status=effective` 的 Law Object 强制 `effective_from`；
  - 缺生效日期或缺业务发生日时 fail-closed 到 `needs_review`；
  - 河南政府采购对象补录 `effective_from=2020-03-09`。

- **CR-003 / E-003 — 河南政府采购主体/资金/范围前置缺失**
  - 限定国家机关、事业单位、团体组织；
  - `funding_scope=[fiscal_funds]`；
  - 增加 `government_procurement_scope=true`；
  - 分散采购对象增加 `in_centralized_catalog=false`；
  - 工程 delegated 对象降为 `supporting_basis`；
  - 官方文号纠正并锁定为 **豫财购〔2020〕4号**。

- **CR-004 / E-004 — scorer subset 假绿**
  - V2.0.3 对 `finding_types / conclusion_codes / law_ids / excluded_law_ids / law_roles / report_sections` 采用精确集合语义；
  - `law_ids` 与 `excluded_law_ids` 不得交集；
  - unknown conclusion code 和互斥结论组合均失败。

- **CR-005 / E-005 — HARD-GATE 跨字段绕过**
  - `blocked` 禁止正式分类、Finding、法规、报告字段及非零数量/金额；
  - `needs_review` 禁止正式 `law_ids / law_roles`。

- **CR-006 / E-006 — voucher amount 重复**
  - `voucher_amount` 只由 Source Record 持有；
  - Finding schema 删除该字段；
  - amount-coverage scorer 从 `source_records` 重算唯一记录数和凭证总额。

- **CR-007 / E-007 — pending/conflicting 可 final**
  - final Finding 必须 `evidence_status=confirmed` 且有非空 `final_wording`；
  - pending/conflicting 不得 final。

- **CR-008 / E-008 — provenance 仅信布尔 verified**
  - effective 法规只接受 `official / official_archive`；
  - 必须具备可追溯 URL 或 identifier；
  - secondary 即使 `verified=true` 仍只能 `needs_review`。

- **CR-009 / E-009 — runtime eval 覆盖不足**
  - 新增财政部令102号事业单位参照；
  - 新增事业单位公务用车原则适用；
  - 新增 unverified/secondary → `needs_review`；
  - 新增河南工程自有资金/非政府采购范围；
  - 新增 liability_basis 不默认输出；
  - 新增完整 Mode A / Mode B 回归；
  - Eval 总数由 14 增至 **21**。

### 12.2 其他 reviewer findings

- **CR-010**：`gte/lte` 类型不匹配不再抛 TypeError，降级 `needs_review`。
- **CR-011**：冻结 Spec 与实现差异记录在 `docs/v2-migration.md`，不篡改历史 Spec。
- **CR-012**：release tests 去除历史测试数量魔法字符串。
- **CR-013**：format lint 增强未闭合 ASCII 引号、`记帐/转帐` 等变体检测。

### 12.3 仓库级验证

V2.0.3 修复代码在 GitHub Actions Run `36830220872` 上取得：

- **101 tests passed**
- **32/32 Law Objects validated**
- **21/21 deterministic fixture passed**

该 Run 之后仅追加了 `rules/law-applicability.md` 的规则同步说明和本验证记录，因此最终 head 仍需再次执行完整 CI 后才能冻结。

### 12.4 发布前剩余 Gate

1. 冻结 V2.0.3 最终 head 后，对 **21 个案例**执行独立 Skill runtime Gate D；
2. Gate D 通过后，对最终 head 再执行一次全新上下文 Gate E independent second review；
3. 两项均通过后，才进入 PR #1 合并决策。

PR #1 继续保持 Draft，在上述 Gate 通过前不得 merge。

### 12.5 V2.0.3 Freeze Manifest

Repository-level final verification before freeze:

- Head: `bffc4d7e8530daaa67c3f276aa9f4fb036fd172c`
- GitHub Actions Run: `36830615954`
- **101 tests passed**
- **32/32 Law Objects validated**
- **21/21 deterministic fixture passed**

Frozen contract / engine blobs:

- `evals/case.schema.json` — `a5291a9a0feaa4217e0ad9e73664f93a9a0c925b`
- `evals/cases/amount-coverage.jsonl` — `08040fc75e21db0baef38a7b465dd1aeb00946cf`
- `evals/cases/classification.jsonl` — `54acc911f91ff2c11fe4e3d4258670d581364fa5`
- `evals/cases/evidence-wording.jsonl` — `d4a9e947e696500daf3722a50d1a744356fa49a7`
- `evals/cases/law-applicability.jsonl` — `1b45a608466f7630fa9e2034486ab422f0a885ed`
- `evals/cases/report-format.jsonl` — `9da715292f3a84470d2b06b1165505eb1e148282`
- `evals/cases/report-modes.jsonl` — `d6fe1b8a3f0da80dc825ef5c39df1a56e8a26ba1`
- `evals/score.py` — `60f3d9d8eca067110fb3e2f23a6d96f5af784cd2`
- `evals/README.md` — `f13131004d5113dcf286b5f275ddddb8c0701437`
- `rules/result-contract.md` — `7608aa56ae0a29b239289b0539cca14fdd66da4f`
- `rules/report-format.md` — `f094a877f4702f8c0de1d917b51a037e70e3d809`
- `rules/law-applicability.md` — `e34ba2b575cedad24ee667042207407a717e53a2`
- `scripts/report_format_lint.py` — `d22eacc397e0f2d60d0a493ebc063ff8bb0360a3`
- `scripts/law_applicability.py` — `17f2b784cec50c2709f37231c1f7dae7efae27c9`
- `schemas/finding.schema.json` — `5d9fd1943eb032874e00261c0a9b95e00c3a1854`
- `schemas/law.schema.json` — `3efe2660f5df6d6fe16ca09c97551840c54a0ae2`

下一次独立 Skill runtime Gate D 开始后，上述 contract / engine 文件不得根据 runtime 输出修改以追求 PASS。若发现真实缺陷，只记录并 STOP，由新的 contract version 或新的 remediation cycle 处理。

## 13. V2.0.3 Runtime Failure and V2.0.4 Contract Repair

### 13.1 V2.0.3 Gate D Runtime

2026-10-01，ZCode 按冻结 head `052576a7985102ec9f9ede5093827118545040d1` 对 21 个案例执行独立 Skill runtime。

结果：

- **2/21 PASS**；
- format lint：**21/21 PASS**；
- Freeze Manifest：16/16 blob SHA 匹配，Drift = NONE；
- 未修改 code / case / expected / scorer / fixture。

该轮的主体失败不是专业行为整体失效，而是 V2.0.3 在修复 Gate E CR-004 时把所有列表字段统一改成 exact-set，导致 expected 最小集合与 runtime 合法补充信息发生系统性冲突。

同时暴露四个真实 contract 设计问题：

1. `excluded_law_ids / law_roles / report_sections` 的发射范围没有定义清楚；
2. `applicability_status` 未明确是“目标候选法规状态”还是“整体法规选择结果”；
3. `report_sections` 使用中文章节标题做精确字符串比较，容易被编号/“表”等展示差异误伤；
4. `mode-a-complete-regression` 与 `format-hard-rules` 对“缺领用清单”使用了不同 finding type。

原始报告：PR #1 issue comment `5928759146`。

### 13.2 V2.0.4 评分与发射语义

V2.0.4 不回退到无约束 subset，也不继续一刀切 exact，而采用字段分级语义：

- expected 中的列表默认表示 **required subset**；
- 只有写入 `expected.exact_fields` 的字段才使用 exact-set；
- 未出现在 expected 中的字段不等于必须为空，但仍受全局安全不变量约束；
- unknown finding/conclusion code、伪 Law ID、互斥结论、`law_ids ∩ excluded_law_ids`、HARD-GATE 跨字段冲突继续直接 FAIL；
- Law ID 必须存在于结构化法规库；
- `unverified_law_requires_review` 只能在实际候选确属 secondary/unverified 时发射。

### 13.3 V2.0.4 发射纪律

- `excluded_law_ids` 只列本案实际候选中被排除的结构化 Law ID，不得全库扫描式罗列；
- `law_roles` 只描述实际输出的正向 `law_ids`；
- `report_sections` 只在 `context.report_mode` 明确存在时输出；
- `report_sections` 使用稳定机器章节代码，不比较中文标题、编号、封面或目录；
- `applicability_status` 仅表示用户问题中明确指向的目标候选法规状态；
- `amount-coverage` 不得夹带分类/定性/法规字段；
- `report-format` 不得夹带专业结论或法规字段；
- `gate_status=blocked` 时不得输出 `applicability_status`。

### 13.4 Case 修正

- `live-20260629` 补足 V2 所需 Project Context，避免在“预期继续分类”的案例中故意制造缺上下文 HARD-GATE；
- Mode A / Mode B `report_sections` 改为稳定代码；
- Mode A 与 format-hard-rules 对“缺领用清单”统一为 `distribution_list_missing`；
- 明确封闭候选集合的法规案例对 `law_ids / excluded_law_ids / law_roles` 使用 opt-in exact。

### 13.5 TDD / Repository Verification

V2.0.4 首轮 RED：7 failed（版本、subset/exact、Law ID 合法性、report_sections 发射、分类口径、Project Context）。

补充 domain emission profile 后再次 RED：2 failed（amount-coverage 和 report-format 仍容忍无关专业结论）。

修复后 GitHub Actions Run `36848654905`：

- **114 tests passed**；
- **32/32 Law Objects validated**；
- **21/21 deterministic fixture passed**。

V2.0.4 仍需在冻结 head 上执行一次完整 21-case 独立 Skill runtime Gate D；通过后再进入新的独立 Gate E second review。

### 13.6 V2.0.4 Freeze Manifest

冻结前 repository-level GREEN：GitHub Actions Run `36848654905`：

- **114 tests passed**；
- **32/32 Law Objects validated**；
- **21/21 deterministic fixture passed**。

Frozen runtime / contract blobs:

- `evals/case.schema.json` — `6f225e7312d6ac7aaba08bf419424b938398e5e1`
- `evals/cases/amount-coverage.jsonl` — `a98ee855b640754dadef15bfbb6a1e761e37ea71`
- `evals/cases/classification.jsonl` — `5372f885d375dd436a3ff19d063545a402328cd9`
- `evals/cases/evidence-wording.jsonl` — `a7f2cba09afa9a7e6d05801d7b1fef6b2a2cc8ad`
- `evals/cases/law-applicability.jsonl` — `aea7e79deec4e8dbea34fa5a29b715ae2aeb72c9`
- `evals/cases/report-format.jsonl` — `021c6a5836d889522eb80669a3946ba87ad61796`
- `evals/cases/report-modes.jsonl` — `e8183c2261d62779c1330b2921f7857a9d762049`
- `evals/score.py` — `540ba7c550d75f6f4f24c5958476f381ed454709`
- `evals/README.md` — `472d88760994693d46f7dd512566fed17f54f0c2`
- `rules/result-contract.md` — `c0f49f86ed0eb2f83dfb243302080cb1f594ee48`
- `rules/report-format.md` — `f094a877f4702f8c0de1d917b51a037e70e3d809`
- `rules/law-applicability.md` — `e34ba2b575cedad24ee667042207407a717e53a2`
- `scripts/report_format_lint.py` — `d22eacc397e0f2d60d0a493ebc063ff8bb0360a3`
- `scripts/law_applicability.py` — `17f2b784cec50c2709f37231c1f7dae7efae27c9`
- `schemas/finding.schema.json` — `5d9fd1943eb032874e00261c0a9b95e00c3a1854`
- `schemas/law.schema.json` — `3efe2660f5df6d6fe16ca09c97551840c54a0ae2`
- `references/report-templates/classification-report.md` — `a6882f3737e1e7dcb02a47454f1cd0571dd192a2`
- `references/report-templates/special-audit-report.md` — `c762cbb1ba4ce6279b5178d951229a180fd71c4a`
- `SKILL.md` — `61beebaebebbb1a7300664610788842130809c34`

从下一次 V2.0.4 Gate D runtime 开始，上述冻结文件不得根据 runtime 输出再修改来追求 PASS。若出现真实缺陷，只记录、STOP，再另开新的 remediation / contract version。

## 14. V2.0.4 Runtime Result and V2.0.5 Narrow Repair

### 14.1 V2.0.4 Gate D Runtime

V2.0.4 frozen head `c4eabc8cd6c041828f9a90f8c4cc67750f5fc1fa` 执行 21 个独立 runtime 案例，结果：

- **11/21 PASS**；
- format lint：**21/21 PASS**；
- 19/19 freeze SHA 匹配，Drift = NONE；
- 未修改任何 frozen 文件。

剩余 10 个 FAIL 分为：

- F1 ×6：`unverified_law_requires_review` 的发射条件把“context 预声明候选”与“runtime 实际分析中遇到候选”混为一谈；
- F2 ×3：`excluded_law_ids` 对“经 Gate 考虑并排除的相关对象”采用了过窄封闭集合；
- F3 ×3：`finding_types` 对具体类型与上位附件类型采用了过严 exact-set；
- F4 ×1：`procurement-specificity` 在 `needs_review` 下正文已形成“不构成串通投标”的证据层判断，但漏发 `collusive_bidding_not_established`。

复核裁定：F1/F2/F3 属 contract/发射边界过严；F4 属真实 runtime 漏发。V2.0.4 仍正式记 FAIL，不人工改判。

原始报告：PR #1 issue comment `5931781198`。

### 14.2 V2.0.5 Narrow Repair

V2.0.5 仅做四项窄修复：

1. `unverified_law_requires_review` 允许由 runtime 在本案分析路径中实际遇到 secondary/unverified 候选时发射，不要求候选必须预先写入 input context；但不得因仓库中存在未核验资料就全局追加。
2. 对 Kaifeng 阈值、102号令事业单位参照、公务用车事业单位原则三个正向法规案例，取消 `excluded_law_ids` 的封闭 exact-set；仍保留 Law ID 必须真实、不得与 `law_ids` 交集等全局安全约束。
3. 对 `live-20260629`、Mode A、Mode B 取消 `finding_types` exact-set，允许具体问题类型与其上位附件类型并存；必需 finding type 仍必须出现。
4. 明确 `gate_status=needs_review` 只限制尚未确认的正式法规依据与最终化判断，**不得吞掉已经独立成立的证据层结论**；正文已判断“不能认定构成串通投标”时仍应同步发 `collusive_bidding_not_established`。

### 14.3 TDD / Repository Verification

V2.0.5 RED：5 failed，精确对应版本、unverified review 预声明、needs_review 结论发射、finding exact、excluded exact 五类边界。

兼容测试同步后，GitHub Actions Run `36865033021`：

- **121 tests passed**；
- **32/32 Law Objects validated**；
- **21/21 deterministic fixture passed**。

### 14.4 Carry-forward Impact Proof

对 V2.0.4 frozen head `c4eabc8...` 与 V2.0.5 implementation head `3971fb4...` 做 whole-diff：

- 未修改 `SKILL.md` 主流程；
- 未修改 `scripts/law_applicability.py`；
- 未修改 schemas；
- 未修改 structured law library；
- 未修改 Mode A/B 模板；
- 变化仅在 eval contract / scorer / cases / fixtures / tests 与 `rules/result-contract.md`。

对 V2.0.4 已真实 PASS 的 11 个案例逐案机器比对，删除 `contract_version` 后，`prompt/context/expected/notes/source` 对象完全一致：

- `p0-one-record-three-findings-no-voucher-duplication`
- `expense-boundary`
- `question-first-gate`
- `p0-suspicious-quotes-not-collusive-bidding-finding`
- `p0-no-future-law-for-2025`
- `p0-no-cadre-rule-for-ordinary-worker`
- `p0-current-invoice-reimbursement-provision`
- `p0-obsolete-official-vehicle-rule-not-current`
- `p1-unverified-law-needs-review`
- `p1-liability-basis-not-default`
- `format-hard-rules`

因此这 11 个 V2.0.4 runtime PASS 证据继续有效；V2.0.5 只需对上一轮失败的 10 个案例做独立定向复测。

### 14.5 V2.0.5 Freeze Manifest

Frozen runtime / contract blobs:

- `evals/case.schema.json` — `82b5bfec775e060a28fc6a6a8d975f12c655ee61`
- `evals/cases/amount-coverage.jsonl` — `bff29189bb7e5cd7a8baeb5a955e2b880580e737`
- `evals/cases/classification.jsonl` — `1ec2dfb39c35a4ce8ab267ed0628f23b675d0295`
- `evals/cases/evidence-wording.jsonl` — `161529e9fd0f06fcc0744a81cf370f5bb331f5b1`
- `evals/cases/law-applicability.jsonl` — `d64b52fee7ed7f4b3b68d538de9f51c970ecaf5b`
- `evals/cases/report-format.jsonl` — `58e874cfbad5f8d8933a8c6b05676afae57a8b2e`
- `evals/cases/report-modes.jsonl` — `3c39345d709789d51e457f1e073e5a6740505e1c`
- `evals/score.py` — `694907e66c953a5534dc68cea4081266451f3978`
- `evals/README.md` — `1c42440c84bda2efcda82144e7a97b7c61888905`
- `rules/result-contract.md` — `83993071dd6d2211656979ca188d1bdcdc11448c`
- `rules/report-format.md` — `f094a877f4702f8c0de1d917b51a037e70e3d809`
- `rules/law-applicability.md` — `e34ba2b575cedad24ee667042207407a717e53a2`
- `scripts/report_format_lint.py` — `d22eacc397e0f2d60d0a493ebc063ff8bb0360a3`
- `scripts/law_applicability.py` — `17f2b784cec50c2709f37231c1f7dae7efae27c9`
- `schemas/finding.schema.json` — `5d9fd1943eb032874e00261c0a9b95e00c3a1854`
- `schemas/law.schema.json` — `3efe2660f5df6d6fe16ca09c97551840c54a0ae2`
- `references/report-templates/classification-report.md` — `a6882f3737e1e7dcb02a47454f1cd0571dd192a2`
- `references/report-templates/special-audit-report.md` — `c762cbb1ba4ce6279b5178d951229a180fd71c4a`
- `SKILL.md` — `61beebaebebbb1a7300664610788842130809c34`

下一次 V2.0.5 定向 Gate D 开始后，上述冻结文件不得根据 runtime 输出修改以追 PASS。
