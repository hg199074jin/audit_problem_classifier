# 法规与制度依据索引（V2）

> **V2 结构化法规库是正式法规对象的权威入口：\`references/laws/\`。**  
> 本文件只保留迁移说明和人工导航，不再承载可被 Skill 直接当作“已核验现行依据”的法规正文清单。

## 1. 使用顺序

1. 先建立 Project Context；
2. 从 \`references/laws/national/\`、\`references/laws/henan/\` 等目录检索结构化 Law Object；
3. 按 \`rules/law-applicability.md\` 执行**时效 → 地域 → 主体 → 事项 → 资金 → 事实/证据**过滤；
4. 只有 \`applicable\` 且来源已核验的对象可以进入正式法规依据；
5. \`needs_review\` 必须写“法规依据需人工核验”或进入 HARD-GATE；
6. \`historical/\` 默认不得参与当前年度候选，只允许历史业务日期落入其有效期间时使用。

## 2. 当前 V2.0 已迁移的 P0 组

- 现行《中华人民共和国发票管理办法》第二十条，以及旧第二十一条历史对象；
- 2017年《党政机关公务用车管理办法》及2011年旧办法历史对象；
- 2018年《评比达标表彰活动管理办法》及2010年试行办法历史对象；
- 《中国共产党廉洁自律准则》及旧《廉洁从政若干准则》历史对象；
- 2019年起政府会计制度与旧行政/事业单位会计制度历史对象；
- 财政部令第81号《基本建设财务规则》与财建〔2002〕394号历史对象；
- 财政部令第102号《政府购买服务管理办法》第十条、第十八条；
- 2020年修订的《公务员奖励规定》；
- 河南省政府集中采购目录及标准（2020年版）按省级、郑州、其他市级、县级及货物/服务/工程拆分的参数规则。

## 2.1 国企审计法规组（2026-11-20 新增，见 docs/decisions/v225-minutes-gap-auditee-confirmation.md）

面向国有企业的审计场景新增 9 个已核验对象：

- 《中华人民共和国企业国有资产法》第三十条（重大事项决策，`CN-SOE-ASSETS-LAW-2008-ART30`）；
- 企业内部控制应用指引第 3 号（人力资源）、第 6 号（资金活动）、第 7 号（采购业务）、第 15 号（全面预算）、第 16 号（合同管理）的关键条款（`CN-IC-GUIDE-*`）；
- 《企业会计准则——基本准则》第十二条（可靠性，`CN-EAS-BASIC-ART12`）；
- 《必须招标的工程项目规定》第五条（含同类采购合并计算规则，`CN-MANDATORY-TENDER-NDRC16-ART5`，以项目属第二至四条强制招标范围为适用前提）；
- 财企〔2009〕242 号职工福利费货币化改革部分（`CN-WELFARE-FEES-2009-242`）。

注意事项：①企业通用类对象均以 `organization.is_public_institution` 为排除条件——行政事业单位硬排除；该事实缺失时按引擎语义转 `needs_review`，因此 Project Context 必须设置 `organization.is_public_institution`（国企项目设 `false`）；②企业内控配套指引施行范围分步（2011 年境内外同时上市公司 → 2012 年主板上市公司 → 鼓励非上市大中型企业执行），对非上市国企引用时报告行文宜保留“参照”表述；③中办发〔2010〕17 号（“三重一大”）因无官方全文公开，**不入库**，引用继续标“法规依据需人工核验”。

## 2.2 第二批：国企专项与国家基础规范（2026-11-20）

- 《企业国有资产监督管理暂行条例》第二十一条、第二十四条（`CN-SOE-SUPERVISION-2019`，国务院令第378号，2019 修订）；
- 《国有企业商务招待管理规定》第七条至第九条（`CN-SOE-BUSINESS-RECEPTION-2020`，国资发考分规〔2020〕20号）——**商务接待陪餐人数、人均标准、清单制度的国家层面依据**；
- 《会计基础工作规范》第四十八条、第五十一条（`CN-ACCOUNTING-BASICS-2019`，财政部令第98号修改）——原始凭证与记账凭证基本要求，**账证不符、附件不齐类问题的直接依据**；
- 《河南省省属国有企业违规经营投资责任追究暂行办法》第六条至第八条（`HENAN-SOE-INVEST-LIABILITY-2017`，`rule_role: supporting_basis`）——仅适用省属企业，市属企业按参照使用。

## 2.3 开封市地方规则组（2026-11-20，目录 `references/laws/kaifeng/`）

`jurisdiction.city = "Kaifeng"`，用于开封市属企业及市直机关审计：

- 开封市市管国有企业工资总额管理实施细则（试行）（`KAIFENG-SOE-WAGE-2024`，2024/11/14）——工资总额范围与“超提、超发”违规情形；
- 开封市市管国有企业负责人履职待遇、业务支出管理暂行办法（`KAIFENG-SOE-BUSINESS-EXPENDITURE-2021`，汴办〔2021〕16号）——**商务宴请 300 元/人次、总额与人均双控、严格控制陪同人数、报销须附招待清单**；
- 开封市市直机关差旅费管理办法（`KAIFENG-TRAVEL-2017`，汴财行〔2017〕18号）与关于规范差旅伙食费和市内交通费收交管理的通知（`KAIFENG-TRAVEL-2019`，汴财行〔2019〕18号）——后者已取代前者关于公杂费与免费提供交通工具的口径；
- 开封市市级会议费管理办法（`KAIFENG-MEETING-2025`，汴财规〔2025〕2号）——会议费综合限额（一类460/二类380/三类350/四类300 元/人天）。

**地方规则与国家规则的效力顺序**：同一事项地方标准严于国家标准的，优先适用地方标准（如开封商务宴请 300 元/人次 严于 国资发考分规〔2020〕20号 600 元/人次）。

**文本来源**：2.2、2.3 两批对象中，部分取自用户政策文件库的政府文件原件（`source.url` 为空、`source.identifier` 载明文号与文件形态）。扫描件经 OCR 录入的，`identifier` 已注明可能存在个别字符识别差异，交付正式报告前应回原件核对。

## 2.4 第三批：按目录顺序全量结构化（2026-11-20）

对用户政策文件库 453 份文件按 37 个目录逐一甄别后新增 **53 个对象**，库内合计 103 个。

### national/ 新增（30）

- 预算与会计：预算法（`CN-BUDGET-LAW-2018`）、政府会计准则——基本准则（`CN-GOV-ACCOUNTING-BASIC-78`）、部门预算支出经济分类科目（`CN-BUDGET-ECONOMIC-CLASS`）、事业单位财务规则（`CN-PUBLIC-INST-FINANCE-RULE`）、企业会计准则第17号借款费用（`CN-EAS-17-BORROWING`）、行政事业单位资产清查核实管理办法（`CN-ASSET-INVENTORY-2016`）；
- 采购与招投标：招标投标法（`CN-TENDER-LAW`）、实施条例（`CN-TENDER-LAW-REG`）、政府采购法（`CN-GP-LAW`）、实施条例（`CN-GP-LAW-REG`）、87号令（`CN-GP-87`）、74号令（`CN-GP-74`）；
- 内控与财经纪律：行政事业单位内部控制规范（`CN-IC-2012`）、收支两条线处分暂行规定（`CN-TWO-LINES-DISCIPLINE`）、增值税发票开具公告2017年第16号（`CN-VAT-INVOICE-2017-16`）、八项规定及实施细则（`CN-EIGHT-RULES`）、厉行节约反对浪费条例2025修订（`CN-ANTI-WASTE-2025`）、纪律处分条例（`CN-PARTY-DISCIPLINE-2023`）、党费规定（`CN-PARTY-DUES-2008`）、公务接待管理规定（`CN-DOMESTIC-RECEPTION-2013`）；
- 绩效、建设、国资、工会、内审：项目支出绩效评价管理办法（`CN-PERFORMANCE-EVAL-2020`）、建设工程价款结算暂行办法（`CN-CONSTRUCTION-SETTLEMENT-2004`）、质量保证金管理办法（`CN-CONSTRUCTION-DEPOSIT-2017`）、企业国有资产交易监督管理办法32号令（`CN-SOE-ASSET-TRANSACTION-32`）、国有企业参股管理暂行办法（`CN-SOE-EQUITY-PARTICIPATION-2023`）、国有企业领导人员廉洁从业规定2026修订（`CN-SOE-INTEGRITY-2026`）、基层工会经费收支管理办法（`CN-UNION-FUND-2017`）、审计署关于内部审计工作的规定11号令（`CN-INTERNAL-AUDIT-11`）、中国内部审计准则（`CN-INTERNAL-AUDIT-STANDARDS`）、第2205号经济责任审计准则（`CN-INTERNAL-AUDIT-2205`）。

### historical/ 新增（2）

- 工程建设项目招标范围和规模标准规定（`CN-ENG-TENDER-SCOPE-2000`）：规模标准已被16号令的 400/200/100 万元取代，仅适用于 2018/05/31 前业务；
- 开封市市级会议费管理办法2014年版（`KAIFENG-MEETING-2014-HIST`）：已被汴财规〔2025〕2号替代，仅适用于 2025/12/30 前业务。

### henan/ 新增（11）

差旅费办法（`HENAN-TRAVEL-2016`）与公杂费改市内交通费通知（`HENAN-TRAVEL-2019-108`）、公务接待办法（`HENAN-RECEPTION-2014`）、培训费管理通知（`HENAN-TRAINING-2025`）、国企工资总额预算编制指引（`HENAN-SOE-WAGE-GUIDE-2023`）与工资决定机制实施意见（`HENAN-SOE-WAGE-REFORM-2019`）、省级财政专项资金管理办法（`HENAN-SPECIAL-FUND-2014`）、政府投资基金管理办法（`HENAN-GOV-FUND-2023`）、驻村干部补助标准（`HENAN-VILLAGE-SUBSIDY-2018`）、省级通用资产配置标准2023版（`HENAN-ASSET-STANDARD-2023`）、基本公共卫生服务补助资金管理办法（`HENAN-PUBLIC-HEALTH-FUND-2024`）。

### kaifeng/ 新增（10）

行政事业单位国有资产配置办法（`KAIFENG-ASSET-CONFIG-2023`）、党政机关公务用车办法（`KAIFENG-OFFICIAL-VEHICLE-2020`）、国有企业公务用车制度改革实施意见（`KAIFENG-VEHICLE-REFORM-2018`）、市直机关培训费办法（`KAIFENG-TRAINING-2018`）、差旅住宿费标准调整通知（`KAIFENG-TRAVEL-LODGING-2016`）、机关事业单位岗位津贴和福利管理通知（`KAIFENG-ALLOWANCE-2019`）、党政机关办公用房办法（`KAIFENG-OFFICE-SPACE-2020`）、驻村第一书记专项经费办法（`KAIFENG-VILLAGE-FUND-2021`）、集体土地附着物和青苗补偿标准（`KAIFENG-LAND-COMP-2021`）、房屋征收工作经费管理通知（`KAIFENG-HOUSING-LEVY-2017`）。

### 未入库文件及原因

见 `references/laws/NOT-INCLUDED.md`——其中 4 份因**版本失效或部分失效**被主动排除（预算法实施条例本地为1995年版、资产损失税前扣除办法已改留存备查、研发费加计比例已调整、河南省级会议费办法已被2025版取代），引用时须另行取得现行文本。

### 业务标签（business_scope）词表

新增对象的 `business_scope` 使用稳定英文标签，便于 runtime 传参匹配。接待类统一包含 `reception`（并保留 `official_reception` / `business_reception`），差旅 `travel_expense`、会议 `meeting_expense`、培训 `training_expense`、公务用车 `official_vehicle`、工资总额 `total_wage_management`、专项资金 `special_fund_use`、内审 `internal_audit`、工会 `union_fund` 等。Project Context 的 `business_type` 应与对象标签一致，否则会被事项过滤为 `not_applicable`。

### 河南政府采购特别提醒

不得再使用“河南分散采购统一100万元、公开招标统一400万元”的概括口径。市级（不含郑州）和县级存在不同限额，工程公开招标数额标准还要另按工程招标规定判断。

## 3. 尚未结构化迁移的 V1 内容

V1 原法规清单已原样归档至：

- \`references/laws-legacy-v1.md\`

这些内容只是**候选依据**。如果正式审计问题需要引用其中某项，应先完成官方来源、版本、效力状态和适用范围核验，再新增结构化 Law Object；不得因为 legacy 文件中存在某条文字就直接视为现行有效。

## 4. 维护入口

- Law Object schema：\`schemas/law.schema.json\`
- 适用性规则：\`rules/law-applicability.md\`
- 法规库维护说明：\`references/laws/README.md\`
- 法规库回归测试：\`tests/test_law_library.py\`
