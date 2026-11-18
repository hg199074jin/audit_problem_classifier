# 审计问题分类规则

## 12 个主分类

| 编码 | 类别 | 直接审计认定对象 |
| --- | --- | --- |
| ZD | 重大政策落实类 | 重大政策执行、违规收费、改革任务落实 |
| YS | 预算决算类 | 预算编制、执行、调整、结转结余、决算 |
| ZJ | 资金管理类 | 专项资金、现金、公务卡、银行账户、非税收入缴库 |
| ZC | 资产管理类 | 配置、登记、盘点、出租出借、调拨处置、产权、资产收益 |
| CG | 政府采购类 | 采购需求、方式、询价比价、供应商、合同、验收、采购档案 |
| XM | 项目管理类 | 立项、概算、建设变更、验收、竣工决算、转固、产权办理 |
| FY | 费用支出类 | 支出范围标准、费用承担、报销附件、支付对象 |
| SJ | 审计监督类 | 整改责任、整改闭环、重复问题、所属单位监督 |
| KJ | 会计基础类 | 科目、确认计量、账务处理、账账账实账表、会计档案 |
| NK | 内部控制类 | 授权审批、岗位分离、重大事项决策、合同台账、往来清理 |
| SW | 税务票据类 | 纳税扣缴、税种税率、发票法定效力、异常涉税票据 |
| QT | 其他问题类 | 小金库、乱收费、事企混同、礼品礼金及其他财经纪律问题 |

## 唯一主类

每个原始问题原则上只进入**一个主类**。先判断“审计要认定的主要错误是什么”，再判断附件、发票、核算等关联瑕疵。一个 Source Record 中存在多个独立违规动作时可以拆成多个 Finding，但每个 Finding 仍只有一个主类。

## FY、KJ、SW 边界

- **FY**：核心是费用是否应发生、是否由本单位承担、是否超范围标准、附件能否证明支出、支付对象是否合理。缺名单、明细、验收、配送等真实性附件通常归 FY。

### FY 与 SW：审计认定对象证据授权（V2.2.4）

**按直接审计认定对象分类，不按"报销/发票"表面关键词机械分类**（用户 2026-11-18 裁定，见 `docs/decisions/v224-invoice-audit-object-adjudication.md`）。runtime **不得以裸布尔**（`independent_invoice_object` / `false_invoicing_dispute` 等）作为 FY/SW 分流依据——该输入权威自 V2.2.4 起失效。必须执行：

1. **提出类型化审计对象**：从源输入提取带逐字引文的 `audit_objects` 断言（`assertion_kind`/`polarity`/`source_id`/`quote`，引文须在 prompt+context 原文中逐字存在且支持所声明事实）。缺陷类断言（购买方不符/开收不一致/不合规发票/发票信息异常）须 affirmative；焦点类断言（对该发票事项的定性要求/单独合法性发问）须 affirmative；限制类断言（交易真实、无虚开证据）只封堵虚开定性结论，**永不授权、也永不吸灭审计对象**。
2. **机器授权**：运行 `python3 scripts/classification_emission.py invoice-object --input <facts.json>`（facts：`audit_objects` + `sources`），按输出 `decision` 执行：
   - `sw_independent`：SW + `invoice_information_irregularity`；`authorized_sw` 对象写入机器结果 `audit_objects`；`restrictions.no_false_invoicing_finding` 转化为措辞限制（**不认定虚开**，区分"现有证据不足以认定虚开"与"已证明不存在虚开"）；
   - `fy_incidental`：发票瑕疵为费用凭证附带瑕疵，FY 内归入 `expense_supporting_documents_nonstandard`，**不拆 SW**；
   - `needs_review`：不得默认 FY，列明待确认事实（如仅否定证据+定性请求而无具体缺陷事实）；
   - `no_invoice_finding`：无有效发票对象，门 abstain；
   - 门内断言引文不可验证时 fail-closed 降级，不得交付未经授权的 SW。
3. **专业性收口**：唯一独立问题为发票信息异常且用户要求定性 → 发票是直接认定对象（报销是背景）；多事项报销附带瑕疵且无独立发票认定请求 → FY；单独发问某发票合规性且缺陷事实成立 → 独立 SW Finding（金额不重复计算）；归入 SW ≠ 认定违反发票管理法规。

KJ/SW 归属不变：直接认定对象是会计科目/确认计量/账务处理 → KJ；纳税扣缴义务/税种税率/发票法定效力 → SW。

## 其他交叉边界

- 询价、比价、供应商关联、采购方式、采购需求、成交资料 → 优先 CG；
- 资产登记、盘点、调拨、处置、出租出借、产权、资产收益 → 优先 ZC，仅会计分录错误才归 KJ；
- 预算编制执行 → YS；专项资金用途、现金、公务卡、账户、缴库 → ZJ；
- 往来款长期未清、合同台账、闭环控制 → NK；
- 虚列支出形成账外资金或“小金库” → QT。

## Finding 粒度规范化

- **最具体稳定代码优先**：同一问题点同时命中具体代码（如 `distribution_list_missing`）与其上位泛化代码（如 `expense_supporting_documents_incomplete`）时，只发射最具体代码，不得并存。
- **附件维度 finding 类型的事实授权（V2.2.3，机器门可判）**：`distribution_list_missing` 只能在源输入存在逐字引文、且引文指明具体清单对象（发放清单 / 领用清单 / 分配名册）时发射；"缺少明细 / 附件缺失"等泛化事实只授权 `expense_supporting_documents_incomplete`。发射前调用 `python3 scripts/classification_emission.py expense-documents --input <facts.json>` 判定（facts：`source_text`、`specific_distribution_list_citation`、`generic_supporting_incomplete`、`documents_nonstandard`），按其 `finding_types` 输出发射，不得绕过。
- **独立 Finding 三条件必须同时成立**（合取，非择一）：直接认定对象独立 **且** 输入事实独立 **且** 整改/结论对象独立。三者同时成立才拆成独立 Finding。
- **"存在另一条可引用法规"本身不构成独立 Finding**；同一报销事项中的发票属性瑕疵若仍服务于费用凭证规范性判断，保持 FY 单 Finding。
- **同一 source record 可以多 Finding，但不得由概念联想机械膨胀**。
- **格式改写/报告化任务不膨胀粒度**：以改写或格式规范化为主要任务的案例，按原始问题的最具体稳定代码发射，不因改写过程新增分析维度。
- **粒度必须稳定**：同一事实模式在不同任务形态（独立定性、报告化、格式改写）下应收敛到同一最具体代码。

## 标题归并

普通水费、维修费、伙食费、通讯费、办公费等，不按项目名称机械设标题；按“原始凭证不齐全 / 原始凭证不规范 / 支出依据不充分”等问题性质归并。政府采购问题使用最具体的二级类型，不得把串通报价嫌疑、未询价、报价资料瑕疵全部写成“采购资料不规范”。
