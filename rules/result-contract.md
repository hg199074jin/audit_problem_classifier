# Machine Result Contract（V2.0.4）

本规则仅在调用方**明确要求机器可评测结果**时启用。普通审计报告仍按正常中文报告输出，不强制暴露内部评测字段。

Gate D / 自动化测试等场景要求机器结果时，runtime 应同时返回人类可读 `text` 与下列结构化字段。编排器可以机械添加 `id` 和 `contract_version`，但不得替模型补专业语义字段。

## Contract version

`contract_version = "2.0.4"`

## 字段

- `gate_status`: `proceed | blocked | needs_review`
- `category`: 单一主分类代码，如 `FY`、`CG`
- `finding_types`: 稳定问题类型代码数组
- `conclusion_codes`: 稳定专业结论代码数组
- `applicability_status`: `applicable | not_applicable | needs_review`。仅表示**用户问题中明确指向的目标法规/候选规则**的适用状态；如果同时讨论替代现行依据，可另列入 `law_ids`，不得把整体法规库状态混进该字段。
- `law_ids`: 可作为当前候选/依据的结构化法规 ID
- `excluded_law_ids`: 明确被时效、主体、地域或其他适用条件排除的**实际候选法规 ID**。只记录本案确实被纳入判断的候选，不得把整个法规库中所有不匹配对象批量枚举进来。
- `record_count`
- `finding_count`
- `voucher_total`
- `law_roles`: 对应本次实际输出 `law_ids` 的法规角色，只允许 `direct_basis | supporting_basis | liability_basis`；没有 `law_ids` 时不要输出。
- `report_mode`: `classification_report | special_audit_report`
- `report_sections`: **仅在输入 context 明确带有 `report_mode` 时输出**，并且只能使用下面的稳定章节代码，不得输出中文标题、编号前缀、封面/目录页等展示文本：
  - Mode A：`mode_a_overview_coverage`、`mode_a_classification_summary`、`mode_a_classification_details`、`mode_a_management_recommendations`、`mode_a_followup_materials`
  - Mode B：`mode_b_engagement_purpose`、`mode_b_entity_overview`、`mode_b_major_findings`、`mode_b_opinions_recommendations`、`mode_b_report_use_scope`

字段按任务需要输出；未发生的语义不要为了“填满字段”而编造。

### Domain emission profiles

为了防止“测试金额却顺带定性”“只改格式却顺带引用法规”造成假绿：

- `amount-coverage`：只输出覆盖统计相关字段（`record_count / finding_count / voucher_total`，以及必要的 `gate_status`）；不得发射分类、Finding 类型、专业结论、法规或报告章节字段。
- `report-format`：可输出 `finding_types` 以确认被改写事项类型，但不得发射 `conclusion_codes / applicability_status / law_ids / excluded_law_ids / law_roles / report_mode / report_sections`。
- 其他 domain 按任务需要输出，但继续受全局不变量和以下发射纪律约束。

### 发射纪律

- `report_sections` 只在 `context.report_mode` 明确存在时发射。
- `unverified_law_requires_review` 只在本案**实际候选法规**确属 secondary/unverified 时发射；不能因为仓库里存在 legacy 文档或其他未核验资料就全局追加该码。
- `excluded_law_ids` 只列本案实际候选中被排除的结构化 Law ID，不做全库扫描式罗列。
- `law_roles` 仅描述本次实际输出的 `law_ids`；无正向法规 ID 时省略。
- `gate_status=blocked` 时不要输出 `applicability_status`。

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

## HARD-GATE 结果不变量

- `gate_status=blocked` 时，不得同时输出正式 `category/finding_types/law_ids/law_roles/report_mode/report_sections`，记录数、Finding 数和金额只能为空或 0。
- `gate_status=needs_review` 时，不得输出正式 `law_ids/law_roles`。
- `law_ids` 与 `excluded_law_ids` 不得交集。

## 评分原则

专业语义由结构化字段评分。V2.0.4 不再对所有数组“一刀切 exact”：

- case 在 `expected` 中声明的数组默认表示“这些值必须出现”；
- 只有 case 把字段列入 `expected.exact_fields` 时才要求精确集合；
- 不在 `expected` 中的字段不等于“必须为空”，但仍受全局不变量、已知代码表、Law ID 合法性与发射纪律约束；
- unknown conclusion/finding code、伪 Law ID、互斥结论、HARD-GATE 跨字段冲突仍然直接 FAIL。

不得依靠正文固定短语判断专业结论。正文 literal 检查只用于真正的格式硬规则。
