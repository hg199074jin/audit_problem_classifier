# 模式 A：审计问题分类整理报告

格式统一读取 `profiles/firm-default.yaml`；模板不得覆盖分类、证据或法规规则。

## 一、基本情况及覆盖校验
共纳入 X 条 Source Record，拆分后形成 Y 个 Finding；原始凭证金额按 Source Record 去重汇总。凭证金额不等同于违规金额或应调整金额。

## 二、问题分类汇总表
| 主分类 | 原始记录数 | Finding 数 | 去重凭证金额 | 主要问题 |
| --- | ---: | ---: | ---: | --- |

## 三、分类问题详述
### （一）[CG] 政府采购类
#### 1. 具体定性结论式标题
| 问题编号 | 原序号 | 制单日期 | 凭证号 | 摘要 | 凭证金额 | 二级类型 | 审计重述 |
| --- | ---: | --- | --- | --- | ---: | --- | --- |

【问题认定】……

【主要依据】优先列 direct_basis；必要时再列 supporting_basis。法规适用状态为 `needs_review` 的不得当作正式依据。

## 四、管理建议
## 五、后续核查资料清单

**报告编制说明：** AI 可辅助整理，最终事实、证据、金额、法规和处理口径由专业审计人员复核。


## Machine result section codes

仅在机器可评测输出且 `context.report_mode=classification_report` 时，`report_sections` 使用以下稳定代码；正文仍保留正常中文标题：

- `mode_a_overview_coverage` → 基本情况及覆盖校验
- `mode_a_classification_summary` → 问题分类汇总表
- `mode_a_classification_details` → 分类问题详述
- `mode_a_management_recommendations` → 管理建议
- `mode_a_followup_materials` → 后续核查资料清单

不得把“问题分类汇总表”等中文标题直接写入机器字段，也不得带章节编号。
