# Machine Result Contract（V2.1.1）

本规则仅在调用方**明确要求机器可评测结果**时启用。普通审计报告仍按正常中文报告输出，不强制暴露内部评测字段。

Gate D / 自动化测试等场景要求机器结果时，runtime 应同时返回人类可读 `text` 与下列结构化字段。所有 machine result 必须先通过 `evals/result.schema.json` 的类型/枚举校验，再进入语义评分。编排器可以机械添加 `id` 和 `contract_version`，但不得替模型补专业语义字段。

## Contract version

`contract_version = "2.1.1"`

## 字段

- `gate_status`: `proceed | blocked | needs_review`
- `category`: 单一主分类代码，如 `FY`、`CG`
- `finding_types`: 稳定问题类型代码数组
- `conclusion_codes`: 稳定专业结论代码数组
- `applicability_target`: **本次 `applicability_status` 明确指向的唯一目标标识**。这是全局不变量（result.schema `dependentRequired` + scorer 全局校验强制，不依赖 expected 是否钉定）：输出 `applicability_status` 必须同时输出本字段，反之亦然；status 的语义 = 该目标的状态。目标标识取值二选一：
  1. **结构化 Law ID**：此时受成员绑定约束——`applicable` ⇒ 目标必须已被选入 `law_ids`；`not_applicable` ⇒ 目标必须列入 `excluded_law_ids`；`needs_review` ⇒ 目标不得作为正式 `law_ids` 输出；
  2. **用户候选口径的稳定标识**（`candidate_rule:<slug>`）：候选对象不是结构化法规时使用，且该标识必须已在 input context 中声明（`candidate_rule_id` 字段，仅表示被判断对象身份，不属于答案泄漏）；不得要求 runtime 猜测只存在于 expected 的私有标签。
  被否定的错误口径与正向适用法规必须分别表达：结构化被排除对象进入 `excluded_law_ids`，正向适用法规进入 `law_ids` 并作为 `applicability_target`；非结构化口径的否定结论体现在正文与结论码中。
- `applicability_status`: `applicable | not_applicable | needs_review`。**必须与 `applicability_target` 成对输出**，且只表示 `applicability_target` 所指目标的状态；不得把整体法规库状态、替代法规状态或多个对象混合进该字段。
- `law_ids`: 可作为当前候选/依据的结构化法规 ID
- `excluded_law_ids`: 明确被时效、主体、地域或其他适用条件排除的**实际候选法规 ID**。只记录本案确实被纳入判断的候选，不得把整个法规库中所有不匹配对象批量枚举进来。
- `record_count`
- `finding_count`
- `voucher_total`
- `law_roles`: **law_id → role 对象映射**。只要 `law_ids` 非空，就必须为每一个选中的 Law ID 提供且仅提供一个角色；角色必须与对应结构化 Law Object 的 `rule_role` 一致。value 只允许 `direct_basis | supporting_basis | liability_basis`。不得输出角色字符串数组；没有 `law_ids` 时省略或输出空对象 `{}`。
- `report_mode`: `classification_report | special_audit_report`
- `report_sections`: **仅在输入 context 明确带有 `report_mode` 时输出**，并且只能使用下面的稳定章节代码，不得输出中文标题、编号前缀、封面/目录页等展示文本：
  - Mode A：`mode_a_overview_coverage`、`mode_a_classification_summary`、`mode_a_classification_details`、`mode_a_management_recommendations`、`mode_a_followup_materials`
  - Mode B：`mode_b_engagement_purpose`、`mode_b_entity_overview`、`mode_b_major_findings`、`mode_b_opinions_recommendations`、`mode_b_report_use_scope`

字段按任务需要输出；未发生的语义不要为了“填满字段”而编造。

## 编排器保真规则

Gate D / 自动化测试中，编排器**只允许机械新增 `id` 和 `contract_version`**。

对 runtime 原始 JSON：

- 不得过滤、删除、重命名或修复 runtime 原始顶层键；
- 不得把错误字段移动到“正确”位置；
- 不得把 dict/list/string 互相转换；
- 未知顶层键必须原样保留进入 scorer，由 scorer 判定 FAIL；
- 如果 runtime 原始 JSON 不是对象或无法解析，应直接记为机器结果格式失败。

这样可以防止非法 machine output 被编排层“清洗”后假绿。

### `law_roles` canonical shape

```json
{
  "law_ids": ["CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE"],
  "law_roles": {
    "CN-OFFICIAL-VEHICLE-2017-PUBLIC-INSTITUTION-PRINCIPLE": "supporting_basis"
  }
}
```

禁止输出：

```json
{"law_roles": ["supporting_basis"]}
```

当存在多个 `law_ids` 时，mapping 直接表达每个法规对应的角色，避免数组位置歧义。

### Domain emission profiles

为了防止“测试金额却顺带定性”“只改格式却顺带引用法规”造成假绿：

- `amount-coverage`：只输出覆盖统计相关字段（`record_count / finding_count / voucher_total`，以及必要的 `gate_status`）；不得发射分类、Finding 类型、专业结论、法规或报告章节字段。
- `report-format`：可输出 `finding_types` 以确认被改写事项类型，但不得发射 `conclusion_codes / applicability_status / law_ids / excluded_law_ids / law_roles / report_mode / report_sections`。
- 其他 domain 按任务需要输出，但继续受全局不变量和以下发射纪律约束。

### 发射纪律

- `report_sections` 只在 `context.report_mode` 明确存在时发射。
- `unverified_law_requires_review` 是保守型 review 提示：当 runtime 在本案分析路径中**实际遇到并考虑了** secondary/unverified 候选时可以发射，不要求该候选必须预先写入 input context；但不能仅因为仓库中存在未核验资料就全局追加。
- `excluded_law_ids` 只列本案**实际候选集合**（先显式形成候选集）中确实被 Gate 排除的结构化 Law ID，不做全库扫描式罗列；作为替代现行依据被选中的对象进入 `law_ids`，不得塞进 `excluded_law_ids`。
- `law_roles` 仅描述本次实际输出的 `law_ids`；所有 key 必须属于 `law_ids`，且 `law_ids` 的每个元素都必须有对应 role；role 必须与 Law Object 的 `rule_role` 一致。
- `liability_basis` 只有在 `context.user_requested_liability_analysis=true` 时才允许发射；普通分类/法规依据任务不得默认泄漏责任依据。
- `gate_status=blocked` 时不要输出 `applicability_status`。
- `gate_status=needs_review` 只限制尚未确认的正式法规依据和最终化判断；**needs_review 不得吞掉已经独立成立的证据层结论**。例如正文已经形成“现有证据不能认定构成串通投标”的判断时，仍应同步输出 `collusive_bidding_not_established`。

### 结论码发射决策（Conclusion emission policy）

### Safe/Negative conclusion trigger gate（未升级定性结论的触发门）

对以下"未达到更严重定性"类结论码：

`invoice_irregularity_not_false_invoicing_established`、`collusive_bidding_not_established`、`misappropriation_not_established`、`post_execution_signing_not_backdating_established`、`recoverable_undercollection_not_loss_established`

原则：**只有当输入事实或用户请求实际触发对应严重定性争议时才发射**，不得因相关领域事实存在就自动附带安全结论（决策表：`scripts/classification_emission.py::safe_negative_conclusion_gate`，runtime 推导 controversy_triggered 与 fact_preconditions 后必须过门）。例如：

- 发票抬头不一致 ≠ 自动触发"未构成虚开发票"；只有 prompt/context 实际涉及"虚开/交易真实性/是否构成虚开"争议时才允许 `invoice_irregularity_not_false_invoicing_established`；
- `collusive_bidding_not_established` 仅在报价异常/供应商关联等串通争议被列入本案认定范围时发射。

### `reimbursement_review_insufficient` 必要条件（V2.1.1 强化）

必须同时满足：①输入明确存在审核程序缺陷、必要附件缺失、审批/复核责任事实（至少其一）；②当前 Finding 确实是审核控制问题。**不得由发票抬头不一致、开票方/收款方不一致、一般凭证不规范单独推出**（决策表：`scripts/classification_emission.py::reimbursement_review_insufficient_gate`）。

### `decision_required_*` 诊断码触发门

`decision_required_pending_items` 只有在输入存在真实未决事实时允许发射：空白记录、纳入/排除取舍、"待落实/是否有文件/无法确认"等事项。**不得因"问题清单很复杂""存在多个事项"而防御性发射**（决策表：`scripts/classification_emission.py::decision_required_pending_items_gate`）。

每个**实质性专业结论码**（区别于 `decision_required_*` 等诊断型代码）发射前必须同时满足：

1. **事实前提成立**：本案输入事实足以独立支撑该结论，不得由相邻概念隐式推导（例如“发票信息异常”不得隐式推导出发射 `reimbursement_review_insufficient`——审核程序缺陷、必要附件缺失、审批责任事实缺一不可）；
2. **属于当前任务范围**：用户请求的任务维度内（分类、定性、法规适用、金额、报告化），超出范围的概念即使“知道安全边界”也不发射；
3. **对应明确的 Finding 或咨询对象**：不与 Finding 粒度重复表达；
4. **不是防御性装饰**：不得为了“显得保守”而追加与本案事实无关的安全结论；
5. **与正文认定一致**：正文已形成的判断必须同步发射（不得吞掉），正文未形成的判断不得提前发射。

## 当前稳定 finding_types

- `procurement_quote_collusion_suspected`
- `procurement_inquiry_missing`
- `procurement_quotation_material_nonstandard`
- `procurement_award_material_nonstandard`
- `procurement_economic_analysis_insufficient`
- `expense_supporting_documents_incomplete`
- `expense_supporting_documents_nonstandard`
- `accounting_issue`
- `tax_issue`
- `distribution_list_missing`
- `receivable_undercollection`
- `contract_signed_after_performance`
- `invoice_information_irregularity`

## 结论码语义边界

- `travel_subsidy_pending_review`：用于“是否可以领取该项差旅/交通补助”本身仍需要补充主办方保障安排、制度适用或其他事实后才能判断的情形。
- `reimbursement_review_insufficient`：只有在已有证据能够确认报销审核程序或必要附件存在缺陷时，才表示已经可以认定“报销审核不充分/不严”。
- 二者**不构成蕴含关系**：出现 `travel_subsidy_pending_review` 时，不要求同时输出 `reimbursement_review_insufficient`；只有两个事实条件分别成立时，二者才可以同时出现。

## 当前稳定 conclusion_codes

- `collusive_bidding_not_established`
- `funds_not_fully_remitted`
- `funds_occupied`
- `misappropriation_not_established`
- `reimbursement_review_insufficient`
- `travel_subsidy_pending_review`
- `decision_required_record_inclusion`
- `decision_required_blank_record`
- `decision_required_pending_items`
- `kaifeng_municipal_threshold_applies`
- `future_law_not_direct_basis`
- `cadre_only_rule_not_applicable_to_ordinary_employee`
- `enterprise_training_rule_not_applicable_to_public_institution`
- `current_invoice_art20_direct_basis`
- `obsolete_official_vehicle_rule_not_current`
- `government_purchase_service_reference_applies`
- `official_vehicle_public_institution_principle_applies`
- `unverified_law_requires_review`
- `government_procurement_scope_not_met`
- `liability_basis_not_default`
- `recoverable_undercollection_not_loss_established`
- `post_execution_signing_not_backdating_established`
- `invoice_irregularity_not_false_invoicing_established`

## HARD-GATE 结果不变量

- `gate_status=blocked` 时，不得同时输出正式 `category/finding_types/law_ids/law_roles/report_mode/report_sections`，记录数、Finding 数和金额只能为空或 0。`law_roles` 为空时使用 `{}` 或省略。
- `gate_status=needs_review` 时，不得输出正式 `law_ids/law_roles`；`law_roles` 为空时使用 `{}` 或省略。
- `law_ids` 与 `excluded_law_ids` 不得交集。

## 空值 pin 语义

当 expected 对 object/list 字段显式写入空值时，**空值 pin 断言空性**，而不是要求 runtime 必须字面发射该空容器。

- 对 `law_roles: {}`：runtime 缺省与显式 `{}` 都表示“本案没有任何法规角色”，均满足空性断言；
- 若 runtime 发出任何非空 role mapping，则空 pin 必须 FAIL；
- 对非空 `law_roles` expected，仍要求精确 law_id → role mapping，不得宽松匹配；
- 该规则不改变未知顶层键、伪 Law ID、role key 必须属于 `law_ids` 等安全约束。

## 评分原则

专业语义由结构化字段评分。V2.0.9 不再对所有数组“一刀切 exact”：

- case 在 `expected` 中声明的数组默认表示“这些值必须出现”；
- 只有 case 把字段列入 `expected.exact_fields` 时才要求精确集合；
- 不在 `expected` 中的字段不等于“必须为空”，但仍受全局不变量、result schema、已知代码表、Law ID 合法性与发射纪律约束；
- `conclusion_codes` 中未被 expected 要求的**实质性专业结论**默认视为危险额外项并 FAIL；当前仅 `unverified_law_requires_review` 作为诊断型 review 提示允许额外发射；
- unknown conclusion/finding code、伪 Law ID、互斥结论、法规角色与 Law Object 不一致、HARD-GATE 跨字段冲突仍然直接 FAIL。

不得依靠正文固定短语判断专业结论。正文 literal 检查只用于真正的格式硬规则。
