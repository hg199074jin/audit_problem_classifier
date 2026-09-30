# Audit Problem Classifier V2 Verification Report

**分支：** `feature/v2-audit-finding-engine`  
**设计基线：** `docs/v2-architecture@942f942671a2659b408b1b7fe28da1068f85388a`  
**已验证实现 Head：** `3d65df2ec838da2eb2257e5b54a9e952defd4a60`  
**报告日期：** 2026-10-01  
**Gate C 状态：** **PASS（仓库级实现与回归验证）**

> 本报告区分“仓库级确定性验证”和“独立 Agent Skill runtime 实测”。前者已经通过；后者尚未执行，不得把基准 fixture 的 PASS 解释为模型真实运行结果。

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
- 河南省政府采购目录及标准的正确文号锁定为 **豫财办〔2020〕4号**，不再沿用原库中的“豫财购〔2020〕4号”。
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

## 8. 尚未执行的独立 Skill Runtime 验收

**独立、干净的 Agent Skill runtime 端到端实测尚未执行。**

当前 GitHub Actions 能证明：

- 数据结构正确；
- 规则契约正确；
- 法规对象可校验；
- applicability engine 正常；
- deterministic scorer 正常；
- 回归 fixtures 满足契约。

但它不能证明某个实际 Agent runtime 加载本 Skill 后，对 14 个 prompt 的生成结果全部达到预期。

因此：

- `evals/fixtures/passing-results.jsonl` 只是评分器的已知良好 fixture；
- 不得把它表述为 ChatGPT/ZCode/其他模型的真实生成结果；
- 正式大规模投入使用前，可以在 ZCode 或其他可加载本分支 Skill 的独立 runtime 中生成 candidate results，再交给 `evals/score.py` 评分。

这一项是**运行时验收项**，不是当前仓库级 Gate C 的伪装完成项。

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
- ⚠️ 独立 Agent Skill runtime E2E 尚未执行
- ⚠️ 无独立 reviewer/subagent，本次 whole-branch review 为作者 self-review

**Gate C（仓库级）结论：PASS。**

本报告属于最后的文档更新；该报告提交后，PR head 仍应由同一 `V2 Verification` workflow 再执行一次成功检查，方可进入合并决策。
