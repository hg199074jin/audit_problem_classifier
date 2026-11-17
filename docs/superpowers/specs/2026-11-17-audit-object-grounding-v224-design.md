# V2.2.4 Audit Object Grounding — 审计认定对象可验证化设计

> 日期：2026-11-17  
> 状态：Owner delegated / Goal 执行设计基线（执行前可做有证据的设计勘误，必须留记录）  
> 仓库：hg199074jin/audit_problem_classifier  
> 起点：feature/v2.2.3-preflight @ 0ec55b8243e14e1de5b59a8571e524e7da04453b  
> 旧发布：v2.2.0 @ 9cadeebf873182d2a598e0eabc9ad7ace1d341b3（保持不可变）

## 1. 为什么做、做到什么程度

V2.2.3 进行了三轮独立的正式 Gate D（V2.2.1 23/26，V2.2.2 22/26，V2.2.3 25/26），最后一轮唯一失败 case-10 `p2-invoice-irregularity-not-false-invoicing`：模型将“报销发票购买方信息不一致，交易真实，无虚开证据，请定性”吸收到 FY 报销资料不规范，漏掉独立 SW 的 `invoice_information_irregularity`。上一轮同案例曾通过，表明 `independent_invoice_object` / `false_invoicing_dispute` 等事实布尔仍由 LLM 自主猜测，现有确定性 `invoice_split_gate` 的**输入权威**未受控。

**目标**：保留中国 CPA 审计报告化能力，并把“证据 → 审计对象 → Finding → 类别 → 条件性结论 → 中文报告”变成可复核、可拒绝、不可被模型隐式绕过的运行链路。不以追某一个 case 的 26/26 替代可信度证明。

成功的可观察表现：

1. 同一事实换一种说法不会在 FY/SW 之间无依据翻转；所有高风险独立对象都有源引文、对象边界与授权理由。
2. 纯报销费用且仅有附带发票瑕疵，仍归 FY，不机械额外生成 SW；只有已独立提出发票合规认定对象的场景才生成 SW。
3. “没有虚开发票证据”只是严重定性的**否定证据**，既不等于“有人提出虚开争议”，也不等于“不允许对发票本身进行定性”。不得将该否定句当作独立 SW 的唯一授权。
4. 有发票信息不一致且请求直接对该发票事项定性时（case-10 结构），发票本身可以是直接认定对象；报销是背景，不自动吞并 SW。
5. 事实不清时输出可核查的 `needs_review` / HARD-GATE，不用虚构事实取得绿灯；不因为单个歧义把其他已证实的 Finding 全部删除。
6. 机器输出和中文报告保持一致；用户自然语言提供问题清单即可使用，不要求手工准备 eval JSON。
7. 新旧测试、独立真实 runtime、法源适用、金额去重、两种报告模式均被验证，全部原始证据及版本冻结可复现。

## 2. 边界、原则与不可做的事

- 这是架构性缺陷修复，不是扩展法规、搭建 SaaS、前端 UI、跨客户端平台迁移或重写整套审计 Skill。
- 不动已发布 `v2.2.0` tag，不 force-push，不改历史 raw、评分器来追绿、不用以前的 25/26 raw 当新验收。
- 所有源材料、单元测试及案例公开前去标识化；**不上传真实审计底稿、客户合同、保密材料、个人身份信息或本地私密凭据**到公开仓库。
- 法规库 32 个 Law Objects 的 schema PASS 不能宣传为 32 部法规已经逐一官方核实；法规效力和适用必须依既有六层 Gate。
- 仍然坚持 HARD-GATE、证据强度、12 类主分类、Source Record 去重、Mode A / B、人民币两位小数与 firm profile。
- 发现正式 Gate D 语义 FAIL，不得重跑同一 frozen candidate、换评分器或删除问题；形成 BLOCKED 证据，评估全新版本的根因修复。这次用户授权自主执行正常开发步骤，但**不授权假阳性发布**。
- ZCode / Superpowers 可充分使用模型、tokens、独立代理、测试资源；不把“省 token”当成决策标准。异步运行由用户 Mac 的 ZCode 发起，这份文档不是 GitHub Actions 启动器。

## 3. 备选架构与选择

| 方案 | 取舍 | 结论 |
| --- | --- | --- |
| A. 继续增加 prompt 和关键词 | 成本低；多轮真实 Gate D 已证明 LLM 可给出不同布尔 | 拒绝作为根治 |
| B. 把所有中文审计文本做成关键字分类器 | 确定，但不能稳定理解语境、否定、咨询对象和合法例外 | 仅可作为佐证/安全拦截 |
| C. 受约束的审计对象提取 + 引文验证 + 可执行确定性门 + 全链路拒绝交付 | 增加结构化 schema 与运行整合；可追溯、可测试、能够保留 LLM 的中文理解能力 | **采用** |

原则：LLM **提出候选**，机器 **核验证据映射与触发条件**，无授权不得发射；对不能由机器确认的语义，显式 `needs_review` 或独立审计人员裁定。

## 4. 数据契约：不可直接相信 bool

### 4.1 新对象的最低字段（接口草案）

为每一个想独立认定的审计对象提供一个带来源的 `AuditObjectCandidate`。字段名字与嵌入现有 schema 的方式由实现者在第一项任务中冻结并做兼容审查，不能不经记录就改变语义。

```json
{
  "object_id": "AO-1",
  "source_record_id": "SR-1",
  "object_kind": "invoice_compliance",
  "directness": "primary",
  "assertions": [
    {
      "assertion_kind": "invoice_buyer_mismatch",
      "polarity": "affirmative",
      "source_id": "prompt",
      "start": 0,
      "end": 0,
      "quote": "<此处为源输入的逐字子串>"
    }
  ],
  "decision": "candidate",
  "review_reason": null
}
```

实际调用应从**不可变源输入**（原始 prompt 与独立原始 context 字段，且有稳定 UTF-8 原文快照/hash）验证引用。采用 Unicode 字符偏移或字节偏移必须显式说明并测试 CJK、引号、空格、表格；`source_id` 只能指真实的、允许访问的源片段。一个 quote 恰好出现在输入内并不自动证明其**语义**；需验证字段类别、否定/假设极性、说话者范围与对象角色。对跨字段拼接、截断偷换、注入的字符串应 FAIL。

推荐分离：

- `FactClaim`：描述具体事项（invoice_buyer_mismatch、issuer_payee_mismatch、noncompliant_invoice_obtained、true_transaction、false_invoicing_evidence_absent、expense_document_missing、explicit_invoice_legality_question 等），带支持引文和极性。
- `AuditObjectCandidate`：要认定的业务/法定义务对象，至少 `expense_reimbursement | invoice_compliance | tax_obligation`，用于现有 FY/SW 分流，不扩大全部 12 类 ontology。
- `AuthorizationDecision`：`allowed | incidental | needs_review | rejected` + 来源、事实 ID、reason codes、可重现的 gate 输入输出。
- `Finding`：仅引用被授权对象/原始 Source Record；每个 Finding 唯一主类，跨对象拆分时不重复计算原始凭证金额。

对于同一 Source Record 可既有费用报销问题又有独立发票问题的情况，机器需要能表达两个独立 `Finding`，而不是把 `category` 单值变成多值或破坏历史合同；普通单 Finding 的现有 machine-result contract 向后兼容。

### 4.2 不能由简单词表推导的专业问题

独立审计对象的判断需要综合：

1. **任务问的是什么**：单独要求“该发票问题如何定性”，与多项目报销凭证分类里的“发票抬头不一致”不等价；
2. **是否有可独立检查的规范义务**：发票信息/合法性问题必须有事实依据，不能只因为法规可引用就新建 Finding；
3. **事实与整改对象能否独立**：必须满足现行“对象独立 + 事实独立 + 整改/结论独立”合取条件；
4. **是否只是反证或未达到严重定性**：“交易真实/尚无虚开证据”不是“证明虚开发票”也不单独证明存在审计对象；
5. **单位主体/地区/资金/业务日期/法规作用域**必须经 Law Applicability 独立处理。

建议将候选上下文划分为三类：`focus_evidence`、`defect_evidence`、`negative_evidence`，保留 evidence type 与极性，不要把“未见虚开证据”降格为无来源布尔。`independent_invoice_object` 与 `false_invoicing_dispute` 不得允许裸 bool 作为权威输入。

### 4.3 门控与拒绝交付

- 保留 `scripts/classification_emission.py::invoice_split_gate` 的向后兼容接口（如必要加 wrapper），但实际 Skill 入口需调用**证据约束**入口，裸布尔只允许明确标记的 legacy/internal 路径；不得在正式结果输出前绕过新门。
- 新的机器门必须拿到不可变 `source_text`、具体 `assertions` 引文及相应对象，将 `AuditObjectCandidate` 变成 `AuthorizationDecision`。
- 审计对象未授权，则不得发射对应 `finding_type` 或在中文正文把相同事项当成“已认定违规”；核对机器结构化输出与报告文本一致性。
- 若对象证据歧义，不准默认 `False` 然后被 FY 吸收；应返回 `needs_review`，说明需确认的具体事实，而不是给出看似已确定的分类。对于可以独立证明的费用事实可继续输出其限定结论。
- 门控执行失败/缺少输入/source drift/未知 enum/不合法 schema → 整体拒绝该未经验证结果，不静默修正代码和互斥字段。
- 严格区分事实层、归类层、法规适用层、报告显示层；不要让答复措辞反向修改验证事实。

## 5. 核心专业矩阵（先裁定，再写测试）

| 场景 | 期待专业行为 | 禁止 |
| --- | --- | --- |
| case-10：唯一事项为发票购买方信息不一致，交易真实，无虚开证据，要求“请定性” | 发票独立认定对象、`invoice_information_irregularity`；不得认定虚开 | 一概被“报销”背景吞入 FY |
| expense-boundary：多种费用报销，附带“抬头不一致/开票方与收款方不一致” | FY + 附件不齐/不规范；不机械拆 SW | 对每种瑕疵拆 SW |
| mode-a/b-integrated：明确“取得不符合规定的发票”，有直接法规候选与背景 | SW、法规适用与 target 成对、模式 A/B 对称 | 单报销背景阻断 SW |
| 无虚开证据但未明确发票问题/请求对象 | 不能单凭否定句生成 SW | “没有虚开证据”自动当作已触发独立发票争议 |
| 仅“费用发票抬头不一致，请整理报销资料” | FY | 无依据新增独立 SW |
| 明确询问“能否认定虚开发票”，但仅有抬头不一致 | 虚开不可认定，发票合规问题可待进一步核实 | 认定虚开、提供处罚结论 |
| 引文存在但属于被否定事实、引用错误 Source Record 或合成多个位置 | FAIL/needs_review，拒绝正式结论 | 通过字符串存在性混入错误证据 |
| 审核手续完整/资料附件缺失 | 不把附件缺失当审核人员失职 | 额外发射 `reimbursement_review_insufficient` |
| 领用清单明确缺失 / 仅“明细不全” | 分别授权具体 `distribution_list_missing` / 泛化 `expense_supporting_documents_incomplete` | 二者无差别替换 |
| 仅待补材料 / 真有需委托人决策事项 | 分别列补证清单 / 触发 HARD-GATE | “有待核实”一概 `decision_required_pending_items` |
| 过去时点的已废止法规 / 地区单位不适用 | 排除或 needs_review，追溯依据需有效期 | 现行法规倒用历史 |
| 同一凭证两 Finding | `record_count=1`、凭证金额只汇总一次 | 重复统计金额 |

首先记录专业裁定：在 case-10 中“请定性”以该笔发票事实为唯一审计对象，而非仅凭“无虚开证据”来触发 SW；这不是依据已见输出修改 expected，而是澄清现行分类规则怎样解释自然语言问法。若独立专业审查对此不同意，必须在冻结前说明有根据的冲突并提出可审计的规则变更，不能悄悄改 oracle。

## 6. 对现有仓库最小侵入

主要触点：

- `scripts/classification_emission.py`：保留现有发票门，新增可验证的审计对象门或调用 `scripts/audit_object_grounding.py`；结构边界清晰。
- `scripts/audit_object_grounding.py`（拟新增）：解析/验证引文、对象、极性、来源身份、门控结论，提供 CLI 与 Python API；无副作用、无网络调用。
- `schemas/` 与 `evals/result.schema.json`：增加必要的审计对象/证据契约（若机器结果需要暴露）；新字段的必填条件和 scope 清楚。
- `rules/classification.md`、`rules/result-contract.md`、`SKILL.md`：让用户真实 Skill 路径必须执行，而非仅评分器存在。
- `evals/score.py`：全局核查结构化审计对象授权与输出一致性，不依赖 expected 才检查；未知值、漂移、无证据的结论 fail-closed。
- `tests/test_audit_object_grounding_v224.py`、`tests/test_invoice_gate_v224.py` 与对应 eval：覆盖正反、变形、对抗与报告通路。
- `docs/`：迁移、操作、已知局限、验证报告、Release notes。

尽量保持既有 `project-context`/`source-record`/`finding` 法规 schema 稳定，避免无理由大重构。

## 7. 可信验收：不再把“测试通过”当“产品可用”

### 7.1 证据分层

- **L1**：代码级 RED→GREEN，正反、schema、注入、极性和映射测试；关键测试 mutation 必须真的能使其失败。
- **L2**：完整 pytest、32 法规对象结构验证、26 deterministic fixture、negative-control fixture 必须失败，所有变更后 CI 绿。
- **L2.5**：用户自然语言完整 Skill 路径独立 E2E；证明工具真的调用审计对象门，不是 evaluator 在事后做装饰。
- **L3 Holdout**：与历史 26 例**不重合**的新正反/改写/上下文变化集，由独立 reviewer 在看到生成答案前冻结 expected，或由专业审计规则先裁定；不得将其答案注入模型。
- **Gate D**：最后冻结版本上对原 26 个案例进行 **26 次 fresh independent runtime**。每例独立 context、输入仅 prompt/context，正确隔离 fixtures、expected、scorer；每例 first valid output，逐批 archive raw；所有有效语义用原始 output 评分。合同/格式/高风险事实/法源与金额安全约束 100% 通过，26/26 专业案例通过。
- **稳定性复测**：Gate D 完成之后另外运行已冻结的独立改写/逆向 holdout 和多次 fresh 生成（固定声明模型、配置和 prompts）；两次之间不拿先前输出调参。把通过率、方差、最差类别、审计重大错误逐项给出。对任何安全关键失败不发布；其余需审计决策有明示边界。
- **Gate E**：在**最终冻结代码和打包 Skill**上由非实现者、新上下文、只读独立复核：数据/法规/分类/结论、输入污染、模型行为、安装、报告可用性、隐私、统计/金额、发布标签同源。0 Critical + 0 Important，Gate D 必须先 PASS。
- **UAT**：至少一份完整 Mode A 和 Mode B 脱敏实际工作风格案例，用户通过自然语言输入即可得到完整中文报告和证据索引；人类 CPA 最终复核边界清楚。若尚无人类实际签收，只能写“技术 UAT 完成，使用者验收待确认”，不得捏造本人验收。

### 7.2 冻结纪律与泄漏隔离

冻结前锁定 exact tree/commit、contract_version、cases/scorer/result.schema、skill install bundle、模型名称/参数、26+holdout 输入和 expected 文件 hash；首次有效回答写只读证据包，不重试语义 FAIL。runtime **绝不可**读取 `evals/`、`tests/`、`fixtures/`、期望答案、历史 raw、评分器、历史报告。Gate D 不能依据需要调整 expected、门控值或后处理模型结果。scorer 不得清洗未知字段；编排仅机械传递允许的 ID/版本。

最终证据包：Git SHA / tree SHA / manifest / CI run+jobs / reviewers / inputs (脱敏) / 26 raw machine+markdown / per-case scorer / schema+format logs / holdout 原始输出 / law validation / release equivalence / 用户操作说明，公开仓库仅放可公开部分，其余为私有路径 + SHA256 + 保存位置清单。

## 8. 发布规则

目标版本 `v2.2.4`，确需破坏结果契约则依据语义版本政策升次版本，且说明迁移。必须同时满足 L1/L2/L2.5、Gate D 26/26、holdout 安全约束、Gate E 0C/0I、实际安装 E2E、主分支 CI、tag/tree/manifest 同源。合并走 PR，先完成 review 再 merge，merge 不得改变冻结 tree；不修改旧标签。

任何关键 Gate FAIL → `BLOCKED`，保留候选分支、raw、矩阵、根因和最小修复路径；不得把 CI/fixture 绿叫作 Release。用户授权自主执行常规开发/测试/PR，但**不授权违规 release**。

## 9. 执行者注意事项

开工前读：`SKILL.md`、`rules/classification.md`、`rules/result-contract.md`、`scripts/classification_emission.py`、`scripts/conclusion_grounding.py`、`evals/score.py`、旧设计和 Issue #8 中 `[ZCODE-R3-FINAL]`。先用可复现最小 E2E 重现 case-10 失效的**门输入来源**；该问题不是单纯的“虚开没证据是否构成争议”，不能只把更多中文词加到布尔判断里。

事实→对象授权可信度必须在实现和**真实 runtime 包**中证明。单纯“加了函数 + 测试调用函数”不足以达到设计目标。
