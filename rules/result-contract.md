# Machine Result Contract（V2.0.3）

本规则仅在调用方**明确要求机器可评测结果**时启用。普通审计报告仍按正常中文报告输出，不强制暴露内部评测字段。

Gate D / 自动化测试等场景要求机器结果时，runtime 应同时返回人类可读 `text` 与下列结构化字段。编排器可以机械添加 `id` 和 `contract_version`，但不得替模型补专业语义字段。

## Contract version

`contract_version = "2.0.3"`

## 字段

- `gate_status`: `proceed | blocked | needs_review`
- `category`: 单一主分类代码，如 `FY`、`CG`
- `finding_types`: 稳定问题类型代码数组
- `conclusion_codes`: 稳定专业结论代码数组
- `applicability_status`: `applicable | not_applicable | needs_review`
- `law_ids`: 可作为当前候选/依据的结构化法规 ID
- `excluded_law_ids`: 明确被时效、主体、地域或其他适用条件排除的法规 ID
- `record_count`
- `finding_count`
- `voucher_total`
- `law_roles`: 实际输出法规角色，只允许 `direct_basis | supporting_basis | liability_basis`
- `report_mode`: `classification_report | special_audit_report`
- `report_sections`: 实际生成的主要报告章节数组

字段按任务需要输出；未发生的语义不要为了“填满字段”而编造。

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

专业语义由结构化字段评分；安全关键数组采用精确集合语义，额外输出与缺失输出同样视为失败。不得依靠正文固定短语判断专业结论。正文 literal 检查只用于真正的格式硬规则。
