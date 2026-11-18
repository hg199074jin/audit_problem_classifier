# V2.2.4 Holdout Protocol（预注册 + 封存）

> 冻结于任何 holdout 模型运行之前。

## 案例集

`evals/holdout/v224-holdout.jsonl` — 26 个全新合成案例（与正式 26 例措辞不重合），覆盖：

- SW 授权 5 例（h01-h05：唯一发票事项/咨询/代购/开收不一致 + 定性或合法性发问）
- FY 附带 5 例（h06-h09, h26：清单附带瑕疵/泛化附件/具体清单对象/Mode B 组合）
- needs_review 3 例（h10 仅否定证据 / h11 焦点无缺陷 / h16 未核验法规）
- 无 Finding 1 例（h12 假设性咨询）
- 决策码 2 例（h13 三兄弟码 blocked / h14 证据链未闭合不发射）
- 安全结论 4 例（h17-h20）
- 法规 2 例（h15 已废止 / h24 资金不适用）
- 模式 3 例（h21 FY-ModeB / h22-h23 发票 ModeA/B 对称 + 适用性配对 + 覆盖金额）
- 金额 1 例（h25 同凭证双 Finding 金额去重）

## Expected 预注册

全部 expected 在**任何模型运行前**按以下依据写入并通过独立裁定审核：

1. 用户 2026-11-18《V2.2.4 审计认定对象分类专业规则裁定》（APPROVED）；
2. `docs/decisions/v224-invoice-audit-object-adjudication.md` 冻结决策表；
3. 既有 26 例 oracle 的同型结构（notes 中标注形态来源，措辞全新）。

## 封存与执行

1. 冻结后记录 jsonl + 本协议的 SHA256（写入执行台账 + Issue #9 checkpoint），此后**不得修改**案例/expected；如必须修改，重新封存并声明版本。
2. 运行：26 例 fresh independent runtime（与 Gate D 同纪律：first-valid、archive-first、输入仅 prompt+context、runtime 不接触 evals/tests/fixtures）。
3. 评分：与正式 Gate D 同一冻结 scorer（`python evals/score.py --cases evals/holdout --results <run>`）。
4. 通过标准：26/26 PASS；任何安全关键错误（虚构违规/虚构法条/金额重复/未授权 SW/裸 bool 绕过）→ BLOCKED。
5. 稳定性探测（Gate D 后）：对 h01/g-case-10 形态做 3 次改写往返（加入否定句/换动词/换主体），断言 FY/SW 判定不翻转。

## 泄漏边界

runtime 安装树不含 evals/（含 holdout）、tests/、docs/、fixtures、任何 expected；holdout 输入在运行前才写入隔离 inputs 目录；评分器与 expected 只存在于评分侧。

## 版本记录（协议 §1：修改必须重新封存并声明版本）

- **v2（2026-11-18，preflight F-001 修复）**：h12 expected 改为空集 exact 钉空性（原 {} 违反 case.schema minProperties）；h15/h24 补 applicability_target 成对（dependentRequired）；h24 重构为询问结构化对象 HENAN-GP-2020-TENDER-WORKS-DELEGATED（对齐正式 p1-henan-works 形态，消除不可满足缺陷）。专业结论未变（独立裁定 26/26 AGREE 针对 v1 专业内容，v2 仅机器 schema 对齐）；v2 经冻结 scorer load_cases 26/26 可加载验证。新 SHA256 见执行台账。
