# V2.2.4 Evidence-Grounded Audit Object — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix FY/SW cross-boundary classification instability by introducing evidence-grounded `audit_object` authorization, then complete independent runtime, holdout, security, and release acceptance without changing historical evidence.

**Architecture:** Keep V2.2.3 as the ancestor and preserve the 12-category Finding / Law Object pipeline. LLM proposes typed source-anchored claims and audit objects; a deterministic boundary verifies provenance, support, polarity and directness, and authorizes invoice split decisions; pre-final enforcement and scorer both check machine result and natural-language report consistency. Missing/contradictory evidence fails closed instead of allowing guessed bools.

**Tech Stack:** Python 3.11+, pytest, JSON Schema, YAML Law Objects, Git/GitHub Actions, ZCode Goal + Superpowers, no new external runtime service.

**Spec:** `docs/superpowers/specs/2026-11-17-audit-object-grounding-v224-design.md`

## Global Constraints

- BASE `0ec55b8243e14e1de5b59a8571e524e7da04453b`; develop on `feature/v2.2.4-audit-object-grounding`; never write directly to `main`.
- Historical `v2.2.0` tag and V2.2.1–V2.2.3 Gate D raw/evidence immutable. Do not rewrite prior results or claim 25/26 was a pass.
- Protected invariants: HARD-GATE, historical law applicability, 12 classes, FY/SW/KJ boundary, Source Record and amount dedupe, Mode A/B reporting, guarded conclusion grounding, no fabricated facts/penalties.
- Public repository: synthetic/anonymized fixtures only; no nonpublic client workpapers, PII, credentials, local absolute paths that disclose secrets.
- No case-ID branches, prompt-keyword blacklists masquerading as proof, no gold-answer leakage, no semantic retry after first valid runtime result.
- Version contracts, schemas, evals, fixtures, docs and Skill package must be consistent; breaking public shape requires version policy and migration notes.
- Every implementation task ends with RED→GREEN verification, a fresh review, and one focused commit. Subagents work in independent contexts/worktrees where available; commit ownership and protected paths coordinated centrally.
- Main model/runtime, settings, tools, source hash and run dates must be recorded. No claim of true external independent reviewer if only the implementation agent self-reviewed.
- The owner delegated ordinary execution decisions; use the full available token/model/reviewer budget as needed for quality, **not endless official retests**.

## Review Focus

Five high-risk inputs beyond nominal tests, with assigned owners:

1. **Negative and hypothetical invoice statements**: “无虚开证据/假如虚开” must not become a proven illegal fact → Task 3/4.
2. **Scope confusion**: mixed reimbursements with incidental invoice discrepancy vs invoice-only “请定性” → Task 4/7.
3. **Evidence source drift**: quote from another Source Record, repeated substring, malformed Unicode offsets, or context changed after extraction → Task 3/5.
4. **Runtime bypass**: model writes a confident SW/FY answer but never invokes the new authorization boundary, or machine output contradicts the Chinese report → Task 5/6.
5. **Oracle or evidence contamination**: runner leaks expected, replayed raw, or scorer post-processes result to green → Task 9/10.

---

## Task 0 — Baseline and execution ledger (no behavioral edits)

**Files:**
- Create: `docs/goals/v224-execution-ledger.md` (append-only milestone evidence)
- Read: `SKILL.md`, `rules/{classification,result-contract,decision-gate,law-applicability}.md`, `scripts/{classification_emission,conclusion_grounding,law_applicability}.py`, `evals/score.py`, `tests/test_preflight_v223.py`
- Read: Issue #8 final + v2.2.3 branch CI + original design/verification report.

**Interfaces:** Produces a verified baseline manifest used by Task 1-12.

- [ ] **Step 1:** Verify remote `feature/v2.2.4-audit-object-grounding` starts from V2.2.3 head via `git merge-base --is-ancestor 0ec55b8243e14e1de5b59a8571e524e7da04453b HEAD`; list all worktrees, check clean status.
- [ ] **Step 2:** Inspect any `AGENTS.md`/local rules; follow existing repo profile and contract. Record exact SHA, python/runtime/model versions, dependencies and current test commands.
- [ ] **Step 3:** Run baseline `python -m pip install -r requirements-dev.txt && pytest -q && python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl`; run negative fixture and verify **nonzero** exit. Collect stdout/stderr and actual counts (do not assume).
- [ ] **Step 4:** Record last final Gate D case-10 result from Issue #8, including raw log path/hash availability; do not substitute issue prose for raw when reproducing exact failure.
- [ ] **Step 5:** Commit ledger with baseline evidence; do not claim a fresh real runtime test unless performed.

## Task 1 — Independent professional adjudication / object ontology

**Files:**
- Create: `docs/decisions/v224-invoice-audit-object-adjudication.md`
- Modify only if adjudication reveals a genuine conflict: `docs/superpowers/specs/2026-11-17-audit-object-grounding-v224-design.md` (record deviation)

**Interfaces:** Produces signed-off (human or named independent reviewer) classification matrix and exactly defined `object_kind`, `assertion_kind`, `polarity`, `directness`; Task 2 consumes them.

- [ ] **Step 1:** Have an independent, fresh-context reviewer compare case-10, expense-boundary, mode-a/b integrated and at least six unseen variations **without seeing original runtime outputs**.
- [ ] **Step 2:** Explicitly adjudicate how “请定性” on an invoice-only statement differs from “报销附件整理”; separate **invoice-law object directness** from **false-invoicing controversy**.
- [ ] **Step 3:** Record counterfactuals: deleting “无虚开证据”, switching “请定性” to “请整理费用附件”, adding independent “发票合规吗” question, mixed water/repair expense list, invoice text explicitly quoted as hypothetical.
- [ ] **Step 4:** Publish decision table and reasons. Existing 26-case oracle does not change merely because a new model failed.
- [ ] **Step 5:** Commit adjudication; if genuine conflict between professional rules and frozen expected emerges, STOP formal acceptance and get a second independent judgment, do not patch expected silently.

## Task 2 — Define typed schema and backwards-compatible contract

**Files:**
- Create: `schemas/audit-object.schema.json` (or two focused schemas if needed)
- Modify: `evals/result.schema.json`, `rules/result-contract.md`
- Test: `tests/test_audit_object_schema_v224.py`

**Interfaces:**
- Input `AuditObjectCandidate` + immutable `SourceSnapshot` with source IDs/hash
- Output `AuthorizationDecision` with `authorized|incidental|needs_review|rejected`, reason codes, recognized fact IDs
- Machine result `audit_objects` field if applicable; compatibility behavior explicitly defined

- [ ] **Step 1:** Write schema RED tests: supported CJK quote/offset, single Source Record, multiple objects, unknown enums, absence of quote, invalid polarity, duplicated IDs and illegal `source_id`.
- [ ] **Step 2:** Run `pytest tests/test_audit_object_schema_v224.py -q`, save failure evidence.
- [ ] **Step 3:** Implement schemas with `additionalProperties: false` where safe, strict types and allowed enums; lock the accepted source offset convention; version contract.
- [ ] **Step 4:** Run focused tests GREEN and existing contract-related tests. Verify legacy result compatibility or document exact migration.
- [ ] **Step 5:** Commit. Reviewer checks schema cannot be satisfied by fabricated source IDs.

## Task 3 — Immutable evidence extraction and semantic support validation

**Files:**
- Create: `scripts/audit_object_grounding.py`
- Test: `tests/test_audit_object_grounding_v224.py`

**Interfaces (final signature may reflect Task 2):**
- `verify_audit_objects(objects: list[dict], sources: dict[str,str]) -> list[str]`
- `authorize_audit_objects(objects: list[dict], sources: dict[str,str]) -> dict`
- CLI: `python scripts/audit_object_grounding.py authorize --input <json> --source <source.json>`

- [ ] **Step 1:** RED tests: exact quote & source span match; quote from wrong record; same text repeated with wrong offset; context JSON reserialized differently; changed SHA; multi-source record crossed; negative, hypothetical, uncertain, affirmative examples; “无虚开证据” not an affirmative false-invoicing fact.
- [ ] **Step 2:** Run RED focused tests and retain output.
- [ ] **Step 3:** Implement deterministic source identity/span validation, support and polarity checks; no silent JSON/text repair; explicit `needs_review` for unresolvable language scope. Never equate a keyword match with a full professional fact if the clause contradicts it.
- [ ] **Step 4:** Run GREEN, then property/metamorphic tests (identical evidence with different IDs; whitespace/punctuation only; negation mutation flips outcome or needs_review).
- [ ] **Step 5:** Commit, independent reviewer attempts adversarial quote/source bypass.

## Task 4 — Replace naked FY/SW bool authority with object authorization

**Files:**
- Modify: `scripts/classification_emission.py`
- Test: `tests/test_invoice_gate_v224.py`
- Consult: `rules/classification.md`

**Interfaces:**
- Retain old `invoice_split_gate(...)` as internal backward-compatible entry if required.
- Add `invoice_object_gate(evidence: dict, sources: dict[str,str]) -> dict` or analogous explicit signature from Task 2.
- Return `decision`, `primary_class`, `finding_types`, `object_ids`, `evidence_ids`, `reason_codes` and `needs_review` reason; no free-form user-provided `independent_invoice_object=True` authority.

- [ ] **Step 1:** RED tests for **case-10 shape → SW** (single direct invoice object), **expense-boundary shape → FY** (incidental invoice defect), **mode A/B explicitly noncompliant invoice → SW**, **“无虚开证据” alone → no extra SW**, plus at least six unseen paraphrase pairs.
- [ ] **Step 2:** Add negative test: old four-bool input alone cannot cause production-path SW without authorized cited object; `invoice_split_gate` legacy API must not silently bypass.
- [ ] **Step 3:** Run RED. Implement mapping of authorized directness + business object + facts to existing gate, with a defined `needs_review` branch (not quietly FY).
- [ ] **Step 4:** Run GREEN, verify previously passed cases 02/03/04/05/23/24/26 behavior remains protected.
- [ ] **Step 5:** Commit, independent reviewer evaluates FY/SW professional reasoning.

## Task 5 — Mandatory runtime integration, not test-only gates

**Files:**
- Modify: `SKILL.md`, `rules/classification.md`, `rules/result-contract.md`
- Possibly add: `scripts/verify_skill_delivery.py` if required for pre-final invariant enforcement
- Test: `tests/test_skill_runtime_v224.py`

**Interfaces:** `source snapshot → candidate facts/objects → authorize CLI → Finding → report → pre-final check`

- [ ] **Step 1:** RED test/smoke proving an attempted production Skill run without calling the new gate is rejected, rather than simply not exercised by tests.
- [ ] **Step 2:** Define runtime-invokable CLI JSON in documentation, exact stdout/exit contract, source location, error/blocked behavior; avoid brittle “model should remember to call” without verification.
- [ ] **Step 3:** Integrate mandatory pre-final boundary with existing `conclusion_grounding.py`, FY/SW split, Law Object applicability and report format lint. Ensure tool invocation telemetry captured in real run.
- [ ] **Step 4:** Run natural-language Mode A and Mode B E2E **without eval/fixture files installed**. Examine invocation logs + outputs manually; if runtime lacks executable tool access, return BLOCKED instead of claiming integration.
- [ ] **Step 5:** Commit; reviewer checks that runtime can't deliver unverified SW despite passing scorer elsewhere.

## Task 6 — Scorer and report consistency (global, non-oracle dependent)

**Files:**
- Modify: `evals/score.py`, `evals/result.schema.json`
- Test: `tests/test_eval_contract_v224.py`

**Interfaces:** `score_case(case, result)` remains public. New global checks derive from source/object contract, not `expected` gates.

- [ ] **Step 1:** RED tests: SW finding without verified object → FAIL; FY with incidental invoice → PASS; SW object quoted from other Source Record → FAIL; contradictory machine/Chinese text statement → FAIL or explicit safe review; unknown evidence fields → FAIL.
- [ ] **Step 2:** Run RED and record. Implement score-side checks as an independent defense; model raw JSON remains unchanged by orchestration except IDs/version mechanically allowed.
- [ ] **Step 3:** Run GREEN, test negative fixture still FAIL. Explain how text consistency is checked for dangerous claims without fragile title matching.
- [ ] **Step 4:** Test scoring of `expected.exact_fields`, legacy domain emission and Law IDs/roles, amount/coverage and HARD-GATE not regressed.
- [ ] **Step 5:** Commit, independent reviewer verifies no case-ID or expected-based bypass.

## Task 7 — New professionally adjudicated holdout / mutation suite

**Files:**
- Create: `tests/test_audit_object_metamorphic_v224.py`
- Create: `docs/validation/v224-holdout-protocol.md`
- Freeze hidden holdout bundle in a **private** approved location if the public runtime is able to read repo; publish only sealed input/expected hashes before running.

**Interfaces:** Tests and holdout matrix with immutable source/case/expected/contract hashes; independent grader reads expected only after runtime.

- [ ] **Step 1:** Produce at least 24 new original professional cases, balanced across FY/SW, negative statements, explicit legal-object questions, multi-source records, possible alternative classifications, exception context, report A/B, and control/amount/law regression.
- [ ] **Step 2:** Independent adjudicator records expected + disputed cases + evidence; remove truly ambiguous cases **before** looking at model output (or explicitly expect needs_review).
- [ ] **Step 3:** Write RED→GREEN metamorphic tests with change-only-one-fact mutations and negative controls. Before running holdout, hash full inputs, expected, runner and model config.
- [ ] **Step 4:** Implement independent holdout harness and report template without leaking expected to runtime.
- [ ] **Step 5:** Commit public protocol/tests; archive private bundle hashes. Reviewer inspects leakage boundary.

## Task 8 — Security, law, amount, and failure-path regressions

**Files:**
- Test: `tests/test_v224_invariants.py`
- Modify minimal existing tests only with professional justification

- [ ] **Step 1:** RED tests for object mismatch not causing double-counted voucher total, legal citation from wrong year/region/subject not promoted, pending/confirmed split, unsafe conclusion not emitted from “no evidence,” blocked field invariants, malformed input and instruction-injection text.
- [ ] **Step 2:** Run RED, implement minimal fixes (if needed) without broadening law library.
- [ ] **Step 3:** Run GREEN and review existing 32 structured laws, 26 deterministic cases, old gate tests, source-record coverage.
- [ ] **Step 4:** Commit. Reviewer independently checks all regression classes.

## Task 9 — Full preflight, freeze, and independent read-only review

**Files:**
- Create: `docs/validation/v224-preflight.md`
- Create: `docs/validation/v224-freeze-manifest.json` or evidence packet reference to SHA/hash if large
- Update: `README.md`, `docs/v2-verification-report.md` and version fields **with accurate prospective status**

- [ ] **Step 1:** Run full `pytest -q`, `python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl`, negative fixture (nonzero required), all `references/laws/**/*.yaml` validation, file hygiene, pure Skill installation smoke.
- [ ] **Step 2:** Run independent, fresh-context **pre-review**; reconcile all Critical/Important before freezing. Record reviewer identity, accessible source manifest, severity decisions, and worktree.
- [ ] **Step 3:** Freeze exact SHA + tree + all code/case/scorer/schema/expected blobs + model+tool/runtime settings + 26 and holdout input hashes. Commit and push; verify remote clone and GitHub CI for **this SHA**. Important: if manifest file itself changes tree, freeze by an explicit documented final commit; no self-referential hash.
- [ ] **Step 4:** Run leakage scan of runtime Skill package (no evals/tests/docs/expected/fixtures/old raw). Record artifact hashes and code equivalence; no patch after freeze.
- [ ] **Step 5:** Commit final preflight docs and then lock candidate. Any change afterward creates a **new candidate/version and new acceptance**.

## Task 10 — ONE formal 26-case fresh independent Gate D on frozen SHA

**Files:** **No code, schema, scorer or case edits.** Evidence only in approved private path + safe summaries in `docs/validation/` / issue comments.

- [ ] **Step 1:** Prove runtime can be started with user-visible Skill only; confirm exact candidate, isolation, source prompt/context only; verify no oracle in tool context. Pre-flight canary uses **new unrelated synthetic material** and isn't counted as the official 26.
- [ ] **Step 2:** For each frozen 26-case input, run fresh independent model session/context; preserve first valid original JSON/markdown and invocation trace. Record attempts, model IDs, timestamps, source hash and per-batch SHA256 BEFORE scoring.
- [ ] **Step 3:** On infra failures, retry only documented objective infra errors, preserving originals; **never** retry semantic failures. No temperature/seed/runtime switching mid-run.
- [ ] **Step 4:** Score on frozen scorer AFTER raw archives are sealed. Require schema 26/26, professional semantic 26/26, lint 26/26, all safety invariants, no unknown fields or drift; produce per-case matrix with specific raw path/hash.
- [ ] **Step 5:** If any semantic FAIL: **Gate D = BLOCKED**. Preserve raw, STOP release, report first-valid errors. Do not silently rerun case 10 or relax expected. Do not proceed to Gate E.

## Task 11 — Frozen holdout / stability validation

**Files:** Evidence-only, private raw and safe public summary.

- [ ] **Step 1:** Only after Gate D PASS, execute the already sealed holdout suite in independent contexts with its own professional scorer, recording first-valid outputs.
- [ ] **Step 2:** Run planned paraphrase/negation and stable-model repeat probes, with run count and configuration declared before execution. Do not filter failures as "bad luck."
- [ ] **Step 3:** Require zero severe misclassification of professionally independent SW/FY objects, zero fabricated violations/law IDs, zero evidence drift, zero amount double-counting; explicitly list any residual noncritical instability.
- [ ] **Step 4:** If any critical safety violation or incomplete evidence: BLOCKED. Otherwise archive objective test matrix and model variance metrics.
- [ ] **Step 5:** No tuning on holdout after seeing output under the same acceptance candidate.

## Task 12 — Independent Gate E, real-world-style UAT, PR, release

**Files:** Final docs, Release notes, human quick start, PR and signed evidence packet.

- [ ] **Step 1:** Independent reviewer in fresh context, with frozen code and raw only, checks **all** gates, input/expected isolation, invoice/expense classification, source/object association, three decision codes, law/time/provenance, 12 classes, amount de-duplication, privacy and failure semantics. Require 0 Critical/0 Important.
- [ ] **Step 2:** Two user-natural-language, synthetic but realistic fully formatted Chinese reports (Mode A/B), using actual Skill installation. Show sources → Findings → category → amount → law applicable/needs review → report text. Record CPA review checklist; do not claim user's personal signoff if unavailable.
- [ ] **Step 3:** Create/complete PR with whole-branch review; compare head, frozen tree, CI and evidence. Merge only if no semantic drift and all gates PASS.
- [ ] **Step 4:** On main, verify fresh CI and tree equivalence before tagging; create new immutable `v2.2.4` release only if same verified tree and version/schema/README/package aligned. Do not move `v2.2.0`.
- [ ] **Step 5:** Report `[ZCODE-V224-FINAL] RELEASED|BLOCKED` on central GitHub Issue with exact SHAs, tag, CI, 26-case matrix, holdout matrix, independent Gate E reviewer record, report UAT and any limitations. BLOCKED means **no tag**.

---

## Execution coordination / Goal mode

- One owner controller in ZCode Goal; subagents may handle separate tasks/reviews using isolated contexts and worktrees, but do not run simultaneous writers against shared mutable files.
- No need to interrupt owner for routine design/commit/tests. Professional adjudication conflicts, privacy exposure, branch protection failures and invalid Gate evidence are STOP conditions, not prompts to invent facts.
- Controller updates one GitHub Issue with checkpoint ledger: baseline → design adjudication → RED/GREEN → preflight/freeze → Gate D → holdout → Gate E/UAT → merge/release. For major changes, link PR/commit/tests evidence.
- **Never start a fresh official Gate D merely to gauge progress.** Use new synthetic canaries and tests until candidate ready; official run is a release gate.
- If blocked, preserve all evidence, protect history, and return an actionable architectural decision rather than repetitive "30 minutes to fix" optimism.

## Completion / reviewer checklist

- [ ] All spec requirements mapped to tasks; no untested professional semantic claim.
- [ ] Fresh runtime actually called evidence authorization gate; no raw bool bypass.
- [ ] Case 10, expense-boundary, Mode A/B and 24+ holdout professional matrix agree with pre-registered oracle.
- [ ] No false SW, no missing independent SW where warranted; ambiguity becomes needs_review.
- [ ] Gate D fresh 26/26 and holdout security conditions PASS, no post-hoc scorer changes.
- [ ] Read-only independent Gate E 0C/0I; install and Chinese report UAT demonstrable.
- [ ] Version/tree/tag/CI exactly match, v2.2.0 history immutable.
