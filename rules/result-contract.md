# Machine Result Contract（V2.0.1）

本规则仅在调用方**明确要求机器可评测结果**时启用。普通审计报告仍按正常中文报告输出，不强制暴露内部评测字段。

Gate D / 自动化测试等场景要求机器结果时，runtime 应同时返回人类可读 `text` 与下列结构化字段。编排器可以机械添加 `id` 和 `contract_version`，但不得替模型补专业语义字段。

## Contract version

`contract_version = "2.0.1"`

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

## 评分原则

专业语义由结构化字段评分；不得依靠正文里是否出现某个固定中文短语判断专业结论。正文 literal 检查只用于真正的格式硬规则。
