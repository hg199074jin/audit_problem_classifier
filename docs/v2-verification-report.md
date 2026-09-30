# Audit Problem Classifier V2 Verification Report

**分支：** `feature/v2-audit-finding-engine`  
**设计基线：** `docs/v2-architecture@942f942671a2659b408b1b7fe28da1068f85388a`  
**报告日期：** 2026-10-01  
**状态：** Gate C 验证进行中

## 1. 已完成的实现检查

已完成：

- V2 eval case contract；
- Project Context / Source Record / Finding / Law Schema；
- 法规适用性三态 Gate；
- Skill 编排与 rules/profile 分层；
- 首批 P0 结构化法规迁移；
- references 案例/建议/模板分层；
- deterministic eval scorer；
- GitHub Actions V2 Verification 工作流。

开发过程中的阶段性本地测试曾达到 **48 tests passed**。该数字属于实施阶段证据，Gate C 结束前仍需在最终分支状态重新执行完整 `pytest -q`。

## 2. 法规 P0 专业复核

已覆盖并结构化：

- 现行发票报销凭证条款及旧版本历史对象；
- 公务用车现行/历史规则；
- 评比达标表彰现行/历史规则；
- 廉洁自律现行/历史规则；
- 政府会计制度及旧行政/事业单位会计制度；
- 基本建设财务规则及旧规定；
- 政府购买服务变相用工相关直接依据；
- 公务员奖励规定；
- 河南政府采购分层参数。

河南采购对象已将原错误文号“豫财购〔2020〕4号”修正并锁定为 **“豫财办〔2020〕4号”**。

## 3. 自动化验证命令

Gate C 最终应执行：

```bash
pytest -q
```

以及全部 Law Object：

```bash
find references/laws -type f -name '*.yaml' -print0 |
  sort -z |
  while IFS= read -r -d '' file; do
    python scripts/validate_v2_data.py --schema law "$file"
  done
```

确定性 eval：

```bash
python evals/score.py --cases evals/cases --results evals/fixtures/passing-results.jsonl
```

## 4. 独立 Skill runtime 实测限制

**独立 Skill runtime 端到端实测当前未执行。**

本次实施环境能够直接修改 GitHub 仓库、执行结构化数据/规则/评分器测试，但当前会话没有一个可以把该分支安装后重新启动为“独立、干净 Agent Skill runtime”的执行器。因此：

- 不能把 `evals/fixtures/passing-results.jsonl` 冒充模型真实输出；
- deterministic scorer 的 PASS 只证明评分器和基准 fixture 契约正确；
- 原 6 个 prompt 和新增 P0 prompt 的真实 Agent 行为，仍应在可加载本分支 Skill 的 ZCode/ChatGPT/其他 runtime 中生成 candidate results 后再评分。

这不阻塞 V2 仓库结构和法规引擎的静态发布验收，但属于正式推广前的独立运行时验收项。

## 5. Mode A / Mode B

- 模式 A 模板：`references/report-templates/classification-report.md`
- 模式 B 模板：`references/report-templates/special-audit-report.md`

最终 Gate C 需确认两者继续服从 HARD-GATE、profile、证据措辞和法规适用性规则。

## 6. 待完成的 Gate C 项

- [ ] 最终分支完整 `pytest -q`；
- [ ] 全部结构化法规逐文件 schema validation；
- [ ] deterministic eval final run；
- [ ] whole-branch review；
- [ ] 如可用，GitHub Actions/独立 runtime 的额外验证；
- [ ] 更新本报告为最终状态。

在这些项目完成前，本报告不声称 V2 已经完成最终发布验收。
