# 法规适用性规则

法规候选必须先做适用性过滤，再讨论引用优先级。关键词命中本身不能证明法规适用。

## 三态结果

- `applicable`：已知事实足以确认适用条件满足。
- `not_applicable`：存在明确冲突或未满足必要条件。
- `needs_review`：缺少会改变适用判断的关键事实，必须进入 HARD-GATE 或法规待核验状态。

`needs_review` 不得在报告中伪装成“已核验直接依据”。

## 固定过滤顺序

必须按以下顺序判断，并保留原因：

1. **时效**：业务发生日是否落在有效期；已废止法规只有历史业务落在其有效期内才可能适用。
2. **地域**：国家、省、市、县是否匹配；河南省级、郑州市、其他省辖市和县级规则不得互相继承阈值。
3. **主体**：单位性质、单位层级、人员身份是否属于适用对象。
4. **事项**：政府采购、政府购买服务、差旅、培训、发票等业务事项是否匹配。
5. **资金**：财政资金、单位自有资金、工会经费、专项资金等是否满足资金范围。
6. **事实/证据**：结构化 `applies_if` / `excludes_if` 条件是否满足。

任何前置条件明确不满足，返回 `not_applicable`；不存在明确冲突但缺少关键事实，最终返回 `needs_review`；全部通过才返回 `applicable`。

## 条件表达

禁止在法规对象中保存需要 `eval` 或自然语言推断的自由文本表达式。V2 使用结构化条件：

```yaml
applies_if:
  - field: invoice_noncompliant
    operator: eq
    value: true
```

支持 `eq`、`neq`、`in`、`not_in`、`exists`、`gte`、`lte`。字段可使用点号读取嵌套上下文。

## 边界

本模块只回答“该法规对象是否可能适用于当前事实”，不负责法规排序、最终法律解释或责任认定。`liability_basis` 的使用仍受证据强度和输出任务范围约束。


## Evaluation Context

`Project Context` 只保存项目级稳定事实；人员身份、业务类型、发票状态、服务提供者类型等 Finding 级事实放入 `finding.applicability_facts`。运行法规 Gate 前，由 `build_evaluation_context(project_context, finding, source_record)` 合并为一次性的 evaluation context。

不得为了某一条法规把 Finding 级事实永久写进项目级 Project Context。

## 来源核验

即使时效、地域和主体均匹配，只要 `law.source.verified != true`，结果也必须是 `needs_review`，不得返回 `applicable` 并作为正式直接依据。
