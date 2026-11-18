# V2.2.4 审计认定对象（FY/SW）专业裁定书

> 日期：2026-11-18
> 状态：**APPROVED**（用户裁定 + 两轮独立 fresh-context 裁定对照，2:1 支持用户裁定）
> 效力：本裁定书冻结 `object_kind / assertion_kind / polarity / directness` 语义与发票门授权决策表；Task 2-4 按此实现。冻结后变更须新版本 + 重新验收。

## 1. 用户裁定（权威输入，2026-11-18 APPROVED 全文要点）

核心原则：**按直接审计认定对象分类，不按"报销/发票"表面关键词机械分类**。唯一独立问题是发票记载信息异常且明确要求对该发票问题定性时 → 发票信息准确性/合规性是直接审计对象 → SW；多事项报销中发票瑕疵只是附带瑕疵且无独立发票认定对象 → FY。**归入 SW ≠ 认定违反发票管理法规，更 ≠ 认定虚开**。

case-10 正式裁定：**SW，`invoice_information_irregularity`**——"报销属于背景，发票信息异常是直接认定对象"；建议表述区分"现有证据不足以认定虚开"与"已证明绝不存在虚开"。

SW 授权四条件（§二）：①具体发票异常事实（源材料可确认）②用户直接要求对该发票事项定性 ③发票本身是直接审计对象 ④事实与请求焦点可回查、可经证据授权程序验证。

## 2. 独立裁定对照（两轮 fresh-context，未接触任何 runtime 输出/oracle）

| 场景 | 裁定员1（12场景） | 裁定员2（10场景乱序） | 用户裁定 | 采用 |
|---|---|---|---|---|
| case-10（唯一发票事项+请定性+无虚开证据） | **FY**，无独立 Finding（异议） | **SW** + 独立 Finding | SW | **SW**（2:1） |
| 同案去掉否定句 | needs_review 倾向 SW | SW + 独立 Finding | SW（§二四条件全满足） | **SW** |
| mode-a/b 形态（取得不符合规定的发票+完整报告） | FY，无独立 Finding（异议） | **SW** + 独立 Finding | （冻结 oracle=SW） | **SW**（2:1） |
| expense-boundary（多费用+附带抬头/开收不一致） | FY | FY | FY | **FY**（3:0） |
| 单笔清单附带抬头不一致（整理报销问题） | FY | FY | FY | **FY**（3:0） |
| 多事项+单独发问发票合规性 | 独立 Finding | FY+SW 拆分独立 Finding | 独立条件成立时 SW | **SW Finding**（3:0） |
| 只有"暂无虚开证据"，无具体异常事实 | needs_review | （未单列） | 不自动授权 SW | **needs_review**（不得默认 FY） |
| 真实代购+定性该发票问题 | FY（异议） | SW + 独立 Finding（违法性质待核实） | §五：客观不一致可记录、违法性质待核实 | **SW Finding + 不认定虚开**（2:1） |
| 同一凭证费用违规+独立发票问题 | FY+SW 分立 | FY+SW 分立、金额只计一次 | 分立 | **FY+SW 分立**（3:0） |
| 咨询"能否作为报销凭证"（有不一致事实） | SW 答复，不生成 Finding | SW + Finding | 咨询性 | **SW 认定事项**（答复即认定意见） |
| 假设性问题（假如虚开如何定性） | 无事实不生成 Finding | — | — | **不生成 Finding** |

**关键分歧与裁定**：裁定员1认为虚开证据被排除后，第二十条"不符合规定的发票不得作为财务报销凭证"属 FY 凭证瑕疵；裁定员2 与用户裁定认为**该第二十条问题本身就是发票法定效力问题（SW）**。裁定采纳用户规则的定义：SW/SW Finding 的判据是**认定对象**（发票信息准确性/合规性是否为直接审计对象），不是违法严重性——"归入 SW ≠ 认定虚开"。否定性证据（交易真实/无虚开证据）的机器语义：**只封堵虚开定性结论，永不授权或否灭审计对象本身**（既不能触发 SW，也不能把已有对象吸收入 FY）。

独立性备注（如实记录）：裁定员1 未接触本机技能材料（外部核验法条）；裁定员2 加载了本机技能的 `references/laws.md` 法规参考（产品自有法规层，非评测数据），两者均确认未接触任何模型输出/评分标准/expected。

## 3. 冻结的类型定义（Task 2/3 实现契约）

```text
object_kind:        expense_reimbursement | invoice_compliance | tax_obligation
assertion_kind:     发票缺陷类（defect_evidence，polarity 须 affirmative）：
                      invoice_buyer_mismatch            购买方/抬头与实际不符
                      issuer_payee_mismatch             开票单位与收款单位不一致
                      noncompliant_invoice_obtained     取得不符合规定的发票（本身即认定对象，兼具 focus 效力）
                      invoice_information_irregular_fact 发票记载信息异常（兜底具体事实）
                    焦点类（focus_evidence，polarity 须 affirmative）：
                      explicit_invoice_characterization_request 用户要求对该发票事项定性/认定
                      explicit_invoice_legality_question   用户单独发问发票合规性/能否作为报销凭证
                    限制类（negative_evidence，只封堵虚开定性结论，永不授权对象）：
                      true_transaction                  交易真实（affirmative）
                      false_invoicing_evidence_absent   无虚开证据（negative）
polarity:           affirmative | negative | hypothetical
directness:         primary | incidental
decision:           authorized_sw | incidental_fy | needs_review | no_invoice_finding | rejected
```

极性/假设语义：`negative`/`hypothetical` 断言不得作为 defect 或 focus 授权事实；`false_invoicing_evidence_absent` 仅进入结论限制（不得发射虚开认定），不参与对象授权。

## 4. 发票对象门授权决策表（`invoice_object_gate` 冻结语义）

前置：所有断言的 `quote` 必须在不可变源输入（prompt+context 原文）中逐字存在且通过极性检查，否则该断言无效；关键断言无效 → 降级处理。

| 条件组合 | decision | 行为 |
|---|---|---|
| defect≥1（含 noncompliant_obtained 或 具体异常事实）∧ focus≥1 ∧ directness=primary | `authorized_sw` | SW + `invoice_information_irregularity`；negative_evidence 转为结论限制（不认定虚开） |
| defect 含 `noncompliant_invoice_obtained`（affirmative）∧ directness=primary（无 focus 亦可：法规违反本身即被呈现为认定对象） | `authorized_sw` | 同上 |
| defect≥1 ∧ focus=0 ∧ noncompliant 不是呈现对象 | `incidental_fy` | FY 吸收为 `expense_supporting_documents_nonstandard`，不拆 SW |
| focus≥1 ∧ defect=0（有效） | `needs_review` | 不得默认 FY，列明待核实事实 |
| 仅 negative_evidence（无 defect 无 focus） | `no_invoice_finding` | 不得凭否定句生成 SW，也不得生成 FY 发票瑕疵 |
| directness=primary 但 focus=0 且 noncompliant 非对象 | `needs_review` | primary 主张无焦点证据支撑，fail-closed |
| 断言引文不在源输入/极性不符/对象引用错源 | 无效断言按上表降级；关键断言全部无效 → `rejected` | 拒绝交付该对象，附 reason_codes |

`directness=primary` 的机器可验条件：focus_evidence 存在，或 `noncompliant_invoice_obtained` 作为呈现问题；多事项清单中的附带瑕疵只能 `incidental`。

## 5. 对冻结 oracle 的影响声明

26 例既有 oracle **零改动**（case-10 expected 本就不含 category，仅要求 `invoice_information_irregularity` + 安全结论码，与本裁定一致）。本裁定是对"现行分类规则如何解释自然语言问法"的澄清，非因模型失败改 expected。裁定员1 的 FY 异议存档如上，若后续人工复核推翻本裁定，须走新版本 + 全量重验。
