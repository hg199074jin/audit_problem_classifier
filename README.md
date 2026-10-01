# 审计问题认定与报告化助手 V2

> **Audit Finding Engine**：把零散审计发现转换为可复核的 Source Record / Finding，并在正式成文前完成 HARD-GATE、证据强度、法规适用性和金额去重检查。

本项目面向中小会计师事务所的财务收支审计、合规审计、专项审核和整改问题整理。V2 不再只是“把问题写得像审计报告”，而是把**事实 → Finding → 证据 → 法规适用 → 定性 → 报告**做成可追溯、可回归验证的工作流。

## V2 核心原则

1. **HARD-GATE：先问清，后动手。** 会改变分类、重大定性、金额或法规适用的未决事项，必须先进入《待决策事项清单》；用户未答复时保持“待核实”。
2. **一个 Source Record 可以拆多个 Finding，但不能重复统计原始记录和凭证金额。**
3. **法规内容正确 ≠ 当前项目适用。** 先通过 Law Object 的时效、地域、主体、事项、资金和事实/证据过滤。
4. **证据不足不升级重定性。** 嫌疑不写认定、占用不写挪用、少收不写损失、补签不写倒签。
5. **规则、法规、案例和报告模板分层。** 案例不能反向覆盖规则，legacy 法规不能自动成为现行依据。
6. **真实返工先变成失败 eval，再修改规则。**

## 四个核心对象

### Project Context

记录当前项目的：

- 地区；
- 单位层级；
- 单位性质；
- 审计期间；
- 资金性质；
- 报告模式；
- profile。

它决定哪些法规候选有资格进入后续判断。

### Source Record

原始问题、凭证、合同、清单行等唯一覆盖单元。原始记录数和 `voucher_amount` 按唯一 `source_record_id` 统计。

### Finding

独立审计认定单元。一个 Source Record 可拆多个 Finding，每个 Finding 原则上只有一个主分类和一个核心违规动作。

### Law Object

结构化法规条款，保存：

- 法规名称、文号、条款；
- 生效/失效时间；
- 地域；
- 主体；
- 业务范围；
- 资金范围；
- `direct_basis / supporting_basis / liability_basis`；
- 官方来源；
- 最近核验日期；
- 替代/废止关系。

Schema：`schemas/law.schema.json`。

## 固定工作流

```text
读取材料
→ 建立 Project Context
→ 待决策事项
→ HARD-GATE
→ Source Records
→ Findings
→ 分类
→ 证据等级
→ law applicability
→ 定性措辞
→ 模式 A / B 报告化
→ 覆盖/金额/法规/格式自检
```

详细入口见 `SKILL.md`。

## 12 类主分类

- `ZD` 重大政策落实类
- `YS` 预算决算类
- `ZJ` 资金管理类
- `ZC` 资产管理类
- `CG` 政府采购类
- `XM` 项目管理类
- `FY` 费用支出类
- `SJ` 审计监督类
- `KJ` 会计基础类
- `NK` 内部控制类
- `SW` 税务票据类
- `QT` 其他问题类

具体边界以 `rules/classification.md` 为准。

## 法规知识层

### 当前有效法规

- 全国：`references/laws/national/`
- 河南：`references/laws/henan/`

### historical

`references/laws/historical/` 保存已废止或被替代、但可能适用于历史业务期间的法规。**historical 默认不能作为当前年度现行法规候选。**

### watchlist

`references/laws/watchlist/` 用于已发布未生效、修订中、来源/效力仍需确认的规则。watchlist 对象不能伪装成已核验直接依据。

### V1 legacy 法规

V1 原法规候选库完整保存在：

- `references/laws-legacy-v1.md`

它只用于历史检索和迁移参考。正式引用前必须重新核验并迁移成 Law Object。

## 河南政府采购的重要修正

V2 已取消“河南统一按100万元/400万元判断”的粗略规则。

河南 Law Object 已区分：

- 省级；
- 郑州市本级；
- 其他市级；
- 县级；
- 货物/服务；
- 工程。

现行文件文号已复核并锁定为 **豫财购〔2020〕4号**。工程公开招标数额标准另按工程招标规定判断，不直接套用货物/服务 400万元/200万元标准。

## HARD-GATE 与 firm profile

重大专业判断由 `rules/decision-gate.md` 控制，不能配置化绕过。

稳定格式习惯放在：

- `profiles/firm-default.yaml`

当前包括：

- 日期：`YYYY/MM`
- 金额：千分位 + 两位小数 + 元
- 中文弯引号
- `X号凭证`
- 普通费用按问题性质归并
- 模式 A / 模式 B

这样可以做到：**重大判断必须问，稳定习惯不重复问。**

## 证据与措辞

见：

- `rules/evidence-and-wording.md`

核心边界包括：

- 串通报价嫌疑 ≠ 构成串通投标；
- 应缴资金被占用 ≠ 截留、挪用；
- 少收仍可追收款项 ≠ 已造成损失；
- 发票信息不准确 ≠ 虚开发票；
- 事后补签 ≠ 倒签合同。

## 报告模式

### 模式 A：分类整理报告

模板：

- `references/report-templates/classification-report.md`

### 模式 B：专项审核报告

模板：

- `references/report-templates/special-audit-report.md`

两种模式都必须服从 HARD-GATE、分类规则、证据措辞、法规适用性和 firm profile。

## Eval 与回归测试

正式 V2 行为案例：

- `evals/cases/classification.jsonl`
- `evals/cases/law-applicability.jsonl`
- `evals/cases/evidence-wording.jsonl`
- `evals/cases/amount-coverage.jsonl`
- `evals/cases/report-format.jsonl`

确定性评分器：

- `evals/score.py`

评分器不会调用模型/API。分类、法规 ID、原始记录数、Finding 数和金额必须通过结构化字段评分；正文字符串仅用于措辞和禁止词检查。

运行：

```bash
python -m pip install -r requirements-dev.txt
pytest -q
python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl
```

## 如何新增一条法规

1. 从官方来源核验全文、版本和效力；
2. 确定 `effective_from / effective_to / status`；
3. 确定地域、单位/人员主体、业务和资金范围；
4. 区分 `direct_basis / supporting_basis / liability_basis`；
5. 写入对应 `references/laws/**.yaml`；
6. 运行：

```bash
python scripts/validate_v2_data.py --schema law <law-file.yaml>
pytest tests/test_law_library.py tests/test_law_applicability.py -q
```

如果来源、版本或效力尚未确认，应进入 watchlist 或保持 `needs_review`，不得自信补造。

## 如何新增一个回归案例

真实项目发生返工时：

1. 匿名化案例；
2. 先新增一个失败的 `evals/cases/*.jsonl` 案例；
3. 确认旧行为 FAIL；
4. 最小修改规则；
5. 确认新行为 PASS；
6. 跑完整测试和 Eval。

这就是本项目的 Skill-TDD 维护方式。

## 目录结构

```text
audit_problem_classifier/
├── SKILL.md
├── README.md
├── agents/
├── rules/
├── schemas/
├── scripts/
├── profiles/
├── references/
│   ├── laws/
│   │   ├── national/
│   │   ├── henan/
│   │   ├── historical/
│   │   └── watchlist/
│   ├── cases/
│   ├── management-suggestions/
│   └── report-templates/
├── evals/
│   ├── cases/
│   ├── fixtures/
│   └── score.py
├── tests/
└── docs/
```

## V1 → V2 迁移与验证

- 迁移说明：`docs/v2-migration.md`
- 验证报告：`docs/v2-verification-report.md`
- 架构设计：`docs/superpowers/specs/2026-09-30-audit-problem-classifier-v2-design.md`
- 实施计划：`docs/superpowers/plans/2026-09-30-audit-problem-classifier-v2-implementation.md`

## 安装

将整个仓库作为 Skill 安装到所用 Agent runtime 的用户级技能目录，并重新加载 runtime。不同 runtime 的具体目录以其官方文档为准。

## 专业边界

本项目辅助审计人员整理和校准 Finding，不替代：

- 审计取证；
- 法律效力最终判断；
- 责任追究；
- 处罚处分决定；
- 注册会计师/审计人员最终专业复核。

V2 的首要质量目标不是“法规越多越好”，而是：**不知道时知道自己不知道，不在法规不适用时自信引用。**
