# Audit Problem Classifier V2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有审计问题报告化 Skill 升级为具备 Project Context、Source Record、Finding、结构化法规、法规适用性过滤、HARD-GATE V2 和可回归评测能力的 Audit Finding Engine V2.0。

**Architecture:** 保留现有 V1 用户行为和模式A/模式B输出，在其外建立结构化数据模型和法规知识层；`SKILL.md` 收敛为编排入口，规则拆入 `rules/`，法规拆入 `references/laws/`，稳定事务所习惯进入 `profiles/`。Evals 使用“结构化案例 + 候选输出评分”的方式与具体 Agent 执行器解耦：仓库负责可重复评分，ZCode/其他 Agent 负责生成候选输出。

**Tech Stack:** Markdown Agent Skill、JSON Schema Draft 2020-12、YAML、Python 3.11+、pytest、PyYAML、jsonschema。

**Spec:** `docs/superpowers/specs/2026-09-30-audit-problem-classifier-v2-design.md`

## Global Constraints

- 基线为 `main@4fb9f9e`；V2 实施必须从批准后的 V2 分支开始，不直接在 `main` 上试错。
- “先问清，后动手”继续为最高行为原则，不得在重构中弱化。
- 每条原始记录原则上只有一个主分类；一个 Source Record 可拆多个独立 Finding。
- 拆分 Finding 后，原始记录数和 `voucher_amount` 不得重复汇总。
- 证据不足时不得升级为“串通投标、截留挪用、造成损失、虚开发票、倒签合同”等重定性。
- 模式A、模式B必须继续可用；现有格式硬规则继续执行。
- 现行法规对象必须带效力状态、适用范围、官方来源和核验日期；不确定法规不得伪装成已核验直接依据。
- V2.0 不追求全国法规全覆盖；优先实现 P0 安全修复、适用性机制和可回归验证。
- 新增依赖仅用于开发期校验和 eval，不把本 Skill 变成需要后台服务才能运行的应用。
- 所有真实项目案例进入 eval/case 前必须匿名化。

## Review Focus

- **历史业务 + 现行法规冲突：** 2025 年事项不能被 2026 年后生效政策覆盖；历史法规只能在其有效期内参与候选。
- **河南采购层级差异：** 开封市级采购不得套用省级/郑州市本级 100 万元阈值。
- **一条凭证多 Finding：** 拆分后分类可以多个，但原始记录数与凭证金额只能统计一次。
- **法规角色混用：** `liability_basis` 不得在普通“法规依据”输出中自动混入 `direct_basis`。
- **HARD-GATE 过度或不足：** 重大判断必须阻断；日期、金额、引号等已配置格式不得重复询问。

---

## File Structure

### New directories

- `rules/`：领域判断规则，只描述“如何判断”，不放项目案例。
- `schemas/`：V2 数据对象的 JSON Schema。
- `profiles/`：事务所稳定格式与报告习惯。
- `references/laws/`：结构化法规库，按地域/状态分区。
- `references/cases/`：匿名化边界案例。
- `references/report-templates/`：模式A/B模板。
- `evals/cases/`：行为回归案例。
- `evals/fixtures/`：评分器使用的候选输出样本。
- `scripts/`：只放数据校验和 eval 评分工具。
- `tests/`：数据结构、适用性与评分器测试。

### Existing files to refactor

- `SKILL.md`：收敛为 V2 编排入口。
- `README.md`：更新 V2 架构与使用方式。
- `references/laws.md`：迁移后改为兼容索引/弃用说明，不继续作为唯一法规源。
- `references/audit-problem-examples.md`：通用规则迁出，只保留案例并逐步拆到 `references/cases/`。
- `references/management-suggestions.md`：迁入目录化结构但保持内容兼容。
- `references/report-structure.md`：迁入 `references/report-templates/`。
- `test-prompts.json`：迁移为 eval cases 后保留兼容说明或删除，按最终兼容策略执行。

---

### Task 1: 建立 V2 Eval Contract，并先记录 RED 基线

**Files:**
- Create: `evals/case.schema.json`
- Create: `evals/cases/classification.jsonl`
- Create: `evals/cases/law-applicability.jsonl`
- Create: `evals/cases/evidence-wording.jsonl`
- Create: `evals/cases/amount-coverage.jsonl`
- Create: `evals/cases/report-format.jsonl`
- Create: `evals/README.md`
- Create: `tests/test_eval_cases.py`
- Modify: `test-prompts.json` only if adding a deprecation pointer is needed; do not delete it in this task.

**Interfaces:**
- Consumes: current V1 behavior and the six existing cases from `test-prompts.json`.
- Produces: stable eval case format consumed by later scoring tasks.

- [ ] **Step 1: Write failing tests for eval case structure**

Create tests asserting every JSONL row has:

```python
required = {
    "id",
    "domain",
    "prompt",
    "context",
    "expected",
    "forbidden",
}
```

Assert IDs are unique across all files and every `expected` object contains at least one machine-checkable assertion.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
pytest tests/test_eval_cases.py -q
```

Expected: FAIL because the V2 eval files do not yet exist.

- [ ] **Step 3: Create the eval schema and migrate the six existing cases**

Use fields:

```text
id
domain
prompt
context
expected
forbidden
notes
source
```

`expected` may include `contains`, `not_contains`, `category`, `law_ids`, `record_count`, `finding_count`, `voucher_total`.

- [ ] **Step 4: Add mandatory P0 regression cases**

At minimum add cases for:

1. 开封市级事业单位 80 万元服务采购；
2. 2025 年事项不得引用 2026 年后生效政策；
3. 普通事业单位职工不得自动套“干部”专属条款；
4. 企业职工教育经费制度不得直接套事业单位；
5. 发票报销凭证条款必须指向现行条款对象；
6. 旧公务用车办法不得作为当前年度现行依据；
7. “报价异常+关联”不得输出“构成串通投标”；
8. 一张凭证拆三个 Finding 时 `voucher_amount` 只汇总一次。

- [ ] **Step 5: Run tests and verify GREEN**

Run:

```bash
pytest tests/test_eval_cases.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add evals tests/test_eval_cases.py test-prompts.json
git commit -m "test: establish v2 audit regression cases"
```

---

### Task 2: 建立 Project Context / Source Record / Finding / Law 数据模型

**Files:**
- Create: `schemas/project-context.schema.json`
- Create: `schemas/source-record.schema.json`
- Create: `schemas/finding.schema.json`
- Create: `schemas/law.schema.json`
- Create: `scripts/validate_v2_data.py`
- Create: `requirements-dev.txt`
- Create: `tests/test_schemas.py`
- Create: `tests/fixtures/valid-project-context.yaml`
- Create: `tests/fixtures/valid-source-record.yaml`
- Create: `tests/fixtures/valid-finding.yaml`
- Create: `tests/fixtures/valid-law.yaml`

**Interfaces:**
- Consumes: field semantics fixed in the approved V2 spec.
- Produces: reusable schemas and `validate_file(path, schema_name)` validation interface.

- [ ] **Step 1: Write schema validation tests first**

Tests must assert:

- valid fixtures pass;
- Law without `status`, `verified_at`, `source` fails;
- Finding without `source_record_id` fails;
- Finding amounts permit separate `voucher_amount`, `issue_amount`, `confirmed_difference`, `pending_amount`;
- Project Context requires jurisdiction, organization, audit period.

- [ ] **Step 2: Run tests and verify RED**

```bash
pytest tests/test_schemas.py -q
```

Expected: FAIL because schemas/validator are absent.

- [ ] **Step 3: Add minimal dev dependencies**

`requirements-dev.txt`:

```text
pytest
PyYAML
jsonschema
```

Do not add application/runtime dependencies.

- [ ] **Step 4: Implement schemas using JSON Schema Draft 2020-12**

Pin enumerations needed by V2:

- organization level;
- organization type;
- law status;
- law role;
- decision status;
- evidence status.

Avoid over-enumerating business categories that are still evolving; use arrays of strings for expandable scopes.

- [ ] **Step 5: Implement `scripts/validate_v2_data.py`**

Required interface:

```python
def load_data(path: Path) -> dict: ...
def load_schema(name: str) -> dict: ...
def validate_file(path: Path, schema_name: str) -> None: ...
```

CLI:

```bash
python scripts/validate_v2_data.py --schema law path/to/file.yaml
```

- [ ] **Step 6: Run tests and verify GREEN**

```bash
pytest tests/test_schemas.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add schemas scripts requirements-dev.txt tests
git commit -m "feat: add v2 audit data schemas"
```

---

### Task 3: 固化法规适用性规则与可测试判定接口

**Files:**
- Create: `rules/law-applicability.md`
- Create: `scripts/law_applicability.py`
- Create: `tests/test_law_applicability.py`

**Interfaces:**
- Consumes: validated Project Context + Law Object.
- Produces:

```python
def evaluate_applicability(context: dict, law: dict, event_date: date | None = None) -> ApplicabilityResult
```

Where:

```python
ApplicabilityResult(
    status="applicable" | "not_applicable" | "needs_review",
    reasons=[...],
)
```

- [ ] **Step 1: Write failing tests for the six filtering dimensions**

Tests must cover:

- effective date;
- jurisdiction;
- subject scope;
- business scope;
- funding scope when declared;
- missing fact → `needs_review`, not `applicable`.

- [ ] **Step 2: Add 河南采购层级边界 tests**

At minimum:

- province/zhengzhou threshold rule matches their own contexts;
- Kaifeng municipal does not inherit province/zhengzhou-only threshold;
- county-level rule does not apply to municipal context.

Use synthetic Law Objects in tests so tests do not depend on later migrated law files.

- [ ] **Step 3: Run RED**

```bash
pytest tests/test_law_applicability.py -q
```

Expected: FAIL because implementation is absent.

- [ ] **Step 4: Implement filter order exactly as Spec**

Order:

```text
effective period
→ jurisdiction
→ subject
→ business
→ funding
→ required facts/evidence
```

Do not rank or select “best law” in this task; only determine applicability.

- [ ] **Step 5: Document the same semantics in `rules/law-applicability.md`**

The Markdown rule must use the same three-state terminology as code:

- applicable
- not_applicable
- needs_review

- [ ] **Step 6: Run GREEN**

```bash
pytest tests/test_law_applicability.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add rules/law-applicability.md scripts/law_applicability.py tests/test_law_applicability.py
git commit -m "feat: add law applicability gate"
```

---

### Task 4: 拆分 V1 领域规则并建立 firm profile

**Files:**
- Create: `rules/decision-gate.md`
- Create: `rules/classification.md`
- Create: `rules/evidence-and-wording.md`
- Create: `rules/coverage-and-amount.md`
- Create: `profiles/firm-default.yaml`
- Create: `tests/test_rule_contracts.py`
- Modify: `SKILL.md`

**Interfaces:**
- Consumes: approved V1 rules currently embedded in `SKILL.md`.
- Produces: focused rule modules + slim orchestrator references.

- [ ] **Step 1: Write failing contract tests**

Tests should assert:

- `SKILL.md` contains the workflow stages in order;
- `SKILL.md` references all four new rule files plus `law-applicability.md`;
- `decision-gate.md` distinguishes blocking decisions from profile defaults;
- `classification.md` preserves all 12 main categories;
- `evidence-and-wording.md` contains high-risk wording boundaries;
- `coverage-and-amount.md` explicitly forbids duplicated voucher totals.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_rule_contracts.py -q
```

Expected: FAIL.

- [ ] **Step 3: Move stable format choices into `profiles/firm-default.yaml`**

Include at least:

```yaml
date_format: YYYY/MM
amount_format: "#,##0.00元"
quote_style: chinese_curly
voucher_reference: "{number}号凭证"
ordinary_expense_grouping: by_issue_nature
report_modes:
  - classification_report
  - special_audit_report
```

Do not move professional judgment rules into profile.

- [ ] **Step 4: Extract rules from `SKILL.md` without changing meaning**

Use recipe-style rules rather than repeating long prohibition lists where possible.

Keep in `SKILL.md` only:

- trigger/description;
- workflow;
- module loading order;
- output mode selection;
- final self-check sequence.

- [ ] **Step 5: Run GREEN**

```bash
pytest tests/test_rule_contracts.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add SKILL.md rules profiles tests/test_rule_contracts.py
git commit -m "refactor: split audit skill rules from orchestration"
```

---

### Task 5: 迁移首批结构化法规并完成 P0 安全修复

**Files:**
- Create: `references/laws/README.md`
- Create: `references/laws/national/*.yaml`
- Create: `references/laws/henan/*.yaml`
- Create: `references/laws/historical/*.yaml`
- Create: `references/laws/watchlist/*.yaml` only when needed
- Create: `tests/test_law_library.py`
- Modify: `references/laws.md`

**Interfaces:**
- Consumes: Law schema + applicability rules.
- Produces: validated initial law library.

- [ ] **Step 1: Write failing law-library tests**

Assert every YAML law file:

- validates against `law.schema.json`;
- contains an official source URL or official source identifier;
- contains `verified_at`;
- has valid status;
- historical items are not marked effective;
- no duplicate provision IDs exist.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_law_library.py -q
```

Expected: FAIL because library is not migrated.

- [ ] **Step 3: Re-verify P0 laws against official sources before writing**

For each P0 item, record:

- official title;
- issuer;
- document number if applicable;
- effective date;
- superseded/repealed status;
- provision text or exact key content;
- scope;
- source URL;
- `verified_at`.

Do not copy an existing V1 row without official re-verification.

- [ ] **Step 4: Migrate the nine mandatory P0 groups**

Must cover:

1. current invoice regulation provision replacing the stale reimbursement article reference;
2. Henan government procurement thresholds with province/Zhengzhou/other municipal/county distinctions;
3. current official-vehicle rule + historical retired rule;
4. current appraisal/commendation rule + historical trial rule;
5. current integrity/discipline basis + retired old clean-government guideline;
6. current government accounting basis + historical old administrative/public-institution accounting rules;
7. current basic construction finance rule + historical 2002 rule;
8. Government Purchase of Services Measures, MOF Order No.102, as main “disguised employment” basis where applicable;
9. current Civil Servant Reward Regulations.

- [ ] **Step 5: Preserve V1 compatibility in `references/laws.md`**

Replace the file’s role from “primary database” to:

- migration notice;
- high-level index;
- pointer to structured library;
- explicit warning that structured objects are authoritative for V2.

Do not silently leave stale rows as if still authoritative.

- [ ] **Step 6: Run validation and applicability tests**

```bash
pytest tests/test_law_library.py tests/test_law_applicability.py -q
python scripts/validate_v2_data.py --schema law references/laws/national/<one-file>.yaml
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add references/laws references/laws.md tests/test_law_library.py
git commit -m "feat: migrate verified v2 law library"
```

---

### Task 6: 重构案例、管理建议和报告模板，消除规则重复

**Files:**
- Create: `references/cases/README.md`
- Create: `references/cases/core-boundaries.md`
- Create: `references/cases/2026-09-retirement-center-anonymized.md`
- Create: `references/management-suggestions/index.md`
- Create: `references/report-templates/classification-report.md`
- Create: `references/report-templates/special-audit-report.md`
- Modify: `references/audit-problem-examples.md`
- Modify: `references/management-suggestions.md`
- Modify: `references/report-structure.md`
- Create: `tests/test_reference_boundaries.py`

**Interfaces:**
- Consumes: new rule modules.
- Produces: example/template/reference layer that cannot override rules.

- [ ] **Step 1: Write failing tests for reference boundaries**

Tests assert reference files declare:

- rules are authoritative on conflicts;
- examples do not redefine main categories;
- report template files reference firm profile formatting;
- project-specific examples are explicitly marked anonymized and non-normative.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_reference_boundaries.py -q
```

Expected: FAIL.

- [ ] **Step 3: Move universal boundary examples into `core-boundaries.md`**

Keep examples such as:

- FY/KJ/SW;
- suspicious quote vs bid-rigging finding;
- occupied vs misappropriated;
- late signature vs backdating.

Do not duplicate their normative rule text; link to the relevant rule module.

- [ ] **Step 4: Anonymize and isolate the retirement-center calibration case**

Preserve the learning value but remove names/identifiers unnecessary for the boundary.

- [ ] **Step 5: Split the two report modes into explicit templates**

Mode A → `classification-report.md`  
Mode B → `special-audit-report.md`

- [ ] **Step 6: Run GREEN**

```bash
pytest tests/test_reference_boundaries.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add references tests/test_reference_boundaries.py
git commit -m "refactor: separate audit rules cases and report templates"
```

---

### Task 7: 实现可重复的 Eval Scorer

**Files:**
- Create: `evals/score.py`
- Create: `evals/fixtures/passing-results.jsonl`
- Create: `evals/fixtures/failing-results.jsonl`
- Create: `tests/test_eval_scorer.py`

**Interfaces:**
- Consumes:
  - case JSONL;
  - candidate result JSONL with `id`, `text`, and optional structured fields.
- Produces:
  - per-case pass/fail;
  - domain totals;
  - non-zero exit on failure.

Required CLI:

```bash
python evals/score.py \
  --cases evals/cases \
  --results path/to/results.jsonl
```

- [ ] **Step 1: Write failing scorer tests**

Cover:

- required substring;
- forbidden substring;
- expected category;
- expected law ID;
- record/finding counts;
- voucher total;
- missing result ID;
- duplicate result ID.

- [ ] **Step 2: Run RED**

```bash
pytest tests/test_eval_scorer.py -q
```

Expected: FAIL.

- [ ] **Step 3: Implement deterministic scorer**

No model/API calls inside scorer.

A failing case must report exactly which assertion failed.

- [ ] **Step 4: Add passing and deliberately failing fixtures**

Verify:

```bash
python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl
```

returns exit 0, and failing fixture returns non-zero.

- [ ] **Step 5: Run GREEN**

```bash
pytest tests/test_eval_scorer.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add evals tests/test_eval_scorer.py
git commit -m "feat: add deterministic audit eval scorer"
```

---

### Task 8: 端到端兼容验收与 README 发布准备

**Files:**
- Modify: `README.md`
- Modify: `agents/openai.yaml`
- Modify: `SKILL.md` only for defects found by end-to-end verification
- Modify: `test-prompts.json` to final compatibility state
- Create: `docs/v2-migration.md`
- Create: `docs/v2-verification-report.md`

**Interfaces:**
- Consumes: all prior V2 tasks.
- Produces: release-ready V2 branch, migration guidance, evidence-backed verification report.

- [ ] **Step 1: Run the complete static/data test suite**

```bash
pytest -q
```

Expected: all tests PASS.

- [ ] **Step 2: Validate all structured laws**

Run validator across every `references/laws/**/*.yaml` file.

Expected: zero schema failures.

- [ ] **Step 3: Execute the original six scenarios through the actual Skill runtime**

For each scenario, save candidate outputs to a V2 result JSONL.

The actual Agent executor may be ZCode or another connected Skill runtime; scoring remains repository-local.

- [ ] **Step 4: Execute the new P0 regression scenarios**

Required result: no stale law article, no wrong Henan threshold inheritance, no obsolete law used as current, no prohibited wording escalation.

- [ ] **Step 5: Score all candidate results**

```bash
python evals/score.py --cases evals/cases --results <v2-results.jsonl>
```

Expected: 100% of mandatory V2.0 cases PASS.

- [ ] **Step 6: Manually inspect Mode A and Mode B full outputs**

Check:

- HARD-GATE behavior;
- classification;
- Finding split;
- amount deduplication;
- law applicability;
- wording;
- format hard rules.

- [ ] **Step 7: Write `docs/v2-verification-report.md`**

Report must include:

- commit under test;
- commands run;
- test counts;
- eval counts;
- any known limitations;
- confirmation that no uncertain law was emitted as verified direct basis.

- [ ] **Step 8: Update README and Agent metadata**

README must explain:

- V2 architecture;
- how to add a law safely;
- how to add a regression case;
- difference between current/historical/watchlist;
- how Human Gate and firm profile interact.

- [ ] **Step 9: Final full verification**

```bash
pytest -q
python evals/score.py --cases evals/cases --results <v2-results.jsonl>
git status --short
```

Expected:

- tests PASS;
- evals PASS;
- working tree clean after final commit.

- [ ] **Step 10: Commit**

```bash
git add README.md agents SKILL.md test-prompts.json docs
git commit -m "docs: finalize audit finding engine v2 migration"
```

---

## Implementation Order and Human Gates

Implementation order is fixed:

```text
Task 1 RED eval baseline
→ Task 2 schemas
→ Task 3 applicability
→ Task 4 rule split/profile
→ Task 5 P0 law migration
→ Task 6 reference cleanup
→ Task 7 scorer
→ Task 8 end-to-end verification
```

Recommended review gates:

- **Gate A — after Task 3:** confirm schemas + applicability semantics before moving large content.
- **Gate B — after Task 5:** professional review of P0 law objects before they become the V2 legal baseline.
- **Gate C — after Task 8:** final design/behavior acceptance before merge to `main`.

No task after a failed gate should proceed by assumption.

## Completion Definition

V2.0 is complete only when all of the following are true:

- approved Spec requirements map to implemented files;
- P0 law corrections are source-verified;
- `pytest -q` passes;
- mandatory eval pack passes;
- Mode A and Mode B each have one reviewed full output;
- historical laws cannot appear as current by default;
- Project Context controls jurisdiction/time/subject applicability;
- one Source Record can produce multiple Findings without duplicated voucher totals;
- HARD-GATE blocks unresolved professional judgments but profile settings do not trigger repetitive questions;
- branch is clean and ready for independent code/skill review.
