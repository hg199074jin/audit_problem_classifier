# Audit Problem Classifier V1 → V2 Migration Guide

**V2 定位：** Audit Finding Engine（审计问题认定引擎）

V2 保留 V1 已经稳定的报告化能力，但把“分类规则、法规候选、案例和格式”从一份大 Markdown 中拆成可验证的规则层、数据层和法规知识层。

## 1. 不变的核心行为

- 继续执行 **HARD-GATE：先问清，后动手**；
- 每个 Finding 原则上只有一个主分类；
- 一个 Source Record 可以拆成多个 Finding；
- 拆分后原始记录数和 `voucher_amount` 只统计一次；
- 证据不足不升级重定性；
- 模式 A（分类整理报告）和模式 B（专项审核报告）继续保留；
- 最终事实、证据、法规和责任认定仍由专业审计人员复核。

## 2. V2 新增的数据对象

### Project Context
记录地区、单位层级、单位性质、审计期间、资金性质、报告模式等，用于法规适用性过滤。

### Source Record
表示原始问题、凭证、合同或清单行，是覆盖数量和原始凭证金额的唯一统计单元。

### Finding
表示独立审计认定单元。一个 Source Record 可产生多个 Finding，但不能因此重复累计原始记录和凭证金额。

### Law Object
把法规条款从自由文本升级为结构化对象，至少记录：版本、效力状态、地域、主体、业务范围、法规角色、官方来源和核验日期。

## 3. 法规迁移

V1 的原法规候选库已完整保留在：

- `references/laws-legacy-v1.md`

该文件仅供历史检索和迁移参考，**不得直接作为 V2 的已核验现行法规库使用**。

V2 正式入口：

- `references/laws/national/`
- `references/laws/henan/`
- `references/laws/historical/`
- `references/laws/watchlist/`（需要时使用）

法规引用前必须按：

`时效 → 地域 → 主体 → 事项 → 资金 → 事实/证据`

执行适用性过滤。

### historical
已经废止或被替代，但可能适用于历史业务期间。默认不能进入当前年度法规候选。

### watchlist
已发布未生效、修订中、效力或来源仍需确认的规则。不能伪装为已核验直接依据。

## 4. 河南政府采购迁移注意

V1 曾将河南采购标准概括为“100万元/400万元”，V2 已禁止这种全省统一套用。

结构化对象区分：

- 省级；
- 郑州市本级；
- 其他市级；
- 县级；
- 货物/服务；
- 工程。

同时已复核并锁定现行文件文号为 **豫财办〔2020〕4号**。工程公开招标数额标准不直接套用货物/服务的 400万元/200万元标准。

## 5. 规则与案例分层

V2 规则入口：

- `rules/decision-gate.md`
- `rules/classification.md`
- `rules/evidence-and-wording.md`
- `rules/law-applicability.md`
- `rules/coverage-and-amount.md`

案例入口：

- `references/cases/`

发生冲突时，规则优先，案例不得反向定义规则。

## 6. 稳定格式迁移到 Profile

事务所稳定习惯放在：

- `profiles/firm-default.yaml`

包括日期、金额、引号、凭证引用和报告模式等。专业判断不得放入 profile 规避 HARD-GATE。

## 7. V1 test-prompts.json 的兼容策略

`test-prompts.json` 保留原 6 个场景供旧调用方式阅读，并新增 `v2_eval_case` 字段指向 V2 结构化 eval。

V2 正式回归测试入口：

- `evals/cases/*.jsonl`
- `evals/score.py`

新增真实项目返工时，应先匿名化并新增失败 eval，再修改规则。

## 8. 开发与校验

安装开发依赖：

```bash
python -m pip install -r requirements-dev.txt
```

运行：

```bash
pytest -q
python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl
```

逐个结构化法规校验：

```bash
python scripts/validate_v2_data.py --schema law references/laws/national/<file>.yaml
```

## 9. 迁移原则

不要把 V1 legacy 法规“批量复制成 V2”。每个正式 Law Object 必须重新核验官方来源、版本、时效和适用范围。V2 的目标不是法规数量最大，而是**不在不适用时自信引用**。


## Implementation deviations from frozen spec

V2 Design Spec 保留为批准时的冻结输入，不回写历史以掩盖实现演进。当前实现存在以下已知、经批准的目录/模型差异：

- Spec 示例曾把 `jurisdiction` 表达为列表；实现采用结构化对象（country/province/city/county），以便做确定性地域过滤。
- Spec 目录树预留 `references/laws/kaifeng/`；V2.0 尚未建立该目录，因为当前没有完成结构化迁移并核验的开封地方 Law Object。后续有正式本地规则时再创建，不用空目录伪装覆盖。
- Spec 早期示意把 eval 放在 `evals/*.jsonl`；实现统一使用 `evals/cases/*.jsonl`，并由 `evals/score.py` 递归读取案例目录。
- Gate E 后续把 machine-result contract 演进为版本化契约；版本变化记录在验证报告，不修改已完成 Gate 的历史结论。
