---
name: audit-problem-classifier
description: 中小会计师事务所收支审计、合规审计问题报告化技能。Use when the user provides audit findings, issue lists,整改问题清单, income-and-expenditure or compliance audit findings and wants formal Chinese audit-report rewriting, issue classification, legal-basis candidates, management recommendations, or a complete issue report. Trigger on 审计问题分类、问题报告化、收支审计问题、合规审计问题、整改清单整理. 🔴 HARD RULE: before classifying or drafting, always resolve material decision items through the HARD-GATE; never decide ambiguous professional judgments unilaterally.
---

# 审计问题认定与报告化助手 V2

## 目标

把零散审计发现转换为可复核、可回查、可进入正式报告的 Finding，同时明确事实、证据、分类、金额、适用法规、定性强度和待核实事项。AI 不替代审计人员的最终专业判断。

## 规则加载顺序

执行前按顺序读取：

1. `rules/decision-gate.md` — 哪些事项必须先问清；
2. `rules/classification.md` — 12 类主分类及边界；
3. `rules/evidence-and-wording.md` — 证据与定性措辞；
4. `rules/law-applicability.md` — 法规时效/地域/主体/事项/资金/事实过滤；
5. `rules/coverage-and-amount.md` — 原始记录、Finding 与金额去重；
6. `rules/report-format.md` — 最终交付文字的格式硬规则与 lint；
7. `rules/result-contract.md` — 调用方明确要求机器可评测结果时使用的结构化字段；
8. `profiles/firm-default.yaml` — 已稳定的格式习惯。

规则冲突时：HARD-GATE > 本 Skill 编排 > rules 专业规则 > references 案例/模板。案例不得覆盖规则。

## 固定工作流

严格按以下顺序执行，不得跳步：

1. **读取材料**：读取全部原始问题、凭证/合同/表格字段和用户已给出的报告口径；非空问题必须进入覆盖检查。
2. **建立 Project Context**：确认地区、单位层级、单位性质、审计期间、资金性质、报告模式和 profile。已知稳定事实直接沿用。
3. **生成待决策事项**：依据 `rules/decision-gate.md` 汇总会改变分类、定性、金额或法规适用的未决事项。
4. **HARD-GATE**：重大事项未解决前不得形成正式认定；用户未答复的保持“待核实”。格式习惯从 profile 读取，不重复追问。
5. **构建 Source Records**：为每条原始记录建立唯一 `source_record_id`，保留主体、期间、凭证号、合同号、金额、审批、支付对象、证据缺失等回查信息。
6. **拆分 Findings**：一个 Source Record 可拆多个独立 Finding；每个 Finding 只回答一个核心问题，原始记录数和 `voucher_amount` 仍只统计一次。
7. **分类**：按 `rules/classification.md` 选择唯一主类和最具体二级类型，不让附件、发票或会计瑕疵覆盖主要审计认定对象。
8. **证据等级**：标记 confirmed / partially_confirmed / pending / conflicting；证据不足事项不得混入已确认结论。
9. **法规适用过滤**：先查结构化法规库；按 `rules/law-applicability.md` 的时效→地域→主体→事项→资金→事实/证据顺序过滤。`needs_review` 不得伪装为正式直接依据。
10. **定性措辞**：按 `rules/evidence-and-wording.md` 控制定性梯度，嫌疑不写认定、占用不写挪用、少收不写损失、补签不写倒签。
11. **报告化输出**：根据用户确认的模式选择分类整理报告或专项审核报告模板；同一小项集中列示直接依据，必要时再列支持性依据。
12. **覆盖/金额/法规/格式自检**：核对 Source Record 覆盖、Finding 数、金额去重、法规效力/适用性，并按 `rules/report-format.md` 做独立最终格式 lint 后再交付。调用方要求机器结果时，同时按 `rules/result-contract.md` 输出结构化字段。

## 法规使用原则

- V2 结构化法规库是法规对象的权威入口；`references/laws.md` 仅作为兼容索引。
- 法规条文本身正确，不代表当前项目适用；必须通过适用性 Gate。
- 优先 `direct_basis`，必要时补充 `supporting_basis`；`liability_basis` 只有在用户明确需要处理处罚/责任分析且事实条件满足时才输出。
- 法规名称、条款、版本、效力或适用范围不能确认时，标记“法规依据需人工核验”，不得补造。
- 后年度规则不得倒推以前年度；历史法规只有业务发生日在其有效期内才可进入候选。

## 报告模式

### 模式 A：分类整理报告

至少包括：基本情况及覆盖校验、问题分类汇总、分类问题详述、管理建议、后续核查资料清单。

### 模式 B：专项审核报告

按事务所受托内审格式组织：封面/目录/导语 + 委托目的、本单位概况、审核中发现的主要问题、意见和建议、报告使用范围 + 签字盖章页。问题小项使用“定性结论式标题 → 事实/表格 → 法规段”。

具体模板见 `references/report-templates/`；迁移完成前兼容读取 `references/report-structure.md`。

## 格式与写作

- 格式默认值从 `profiles/firm-default.yaml` 读取，并强制执行 `rules/report-format.md`：日期 `YYYY/MM`、金额千分位两位小数、中文弯引号、`X号凭证`。
- 使用正式、克制、可核验的审计语言；只写证据能够支撑的事实。
- 明细表已有日期、凭证号、摘要和金额时，审计重述不机械重复。
- 普通费用按问题性质归并标题；采购问题按最具体二级类型拆分。
- 管理建议必须对应问题性质和整改动作，不输出空泛口号。
- 涉及个人责任、违纪违法或移送处理时，证据不足不得直接提出责任结论。

## 最终自检

交付前逐项确认：

- HARD-GATE 未决事项是否仍被错误写成正式结论；
- 12 类分类边界是否正确，每个 Finding 是否只有一个主类；
- Source Record 拆分后记录数和凭证金额是否重复；
- 高风险措辞是否超过证据强度；
- 法规是否匹配年度、地域、主体、事项和资金性质；
- 模式 A / B、日期、金额、引号、凭证格式是否符合 profile，且最终格式 lint 无违规；
- 未核验法规是否明确标注待核验。
