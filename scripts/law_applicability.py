#!/usr/bin/env python3
from __future__ import annotations

from datetime import date
from typing import Any, NamedTuple


class ApplicabilityResult(NamedTuple):
    status: str
    reasons: list[str]


def build_evaluation_context(
    project_context: dict,
    finding: dict | None = None,
    source_record: dict | None = None,
) -> dict:
    """Combine validated project facts with Finding-specific applicability facts.

    Project Context stays project-scoped. Finding-specific facts such as
    business_type, person_type, provider type, invoice status, or threshold
    amounts live under finding.applicability_facts and are merged only for
    law evaluation.
    """
    context: dict[str, Any] = {
        "jurisdiction": dict(project_context.get("jurisdiction") or {}),
        "organization": dict(project_context.get("organization") or {}),
    }
    if "funding" in project_context:
        funding = project_context.get("funding")
        context["funding"] = list(funding) if isinstance(funding, list) else funding

    if source_record and source_record.get("event_date") is not None:
        context["event_date"] = source_record["event_date"]

    if finding:
        facts = finding.get("applicability_facts") or {}
        if not isinstance(facts, dict):
            raise TypeError("finding.applicability_facts must be an object")
        context.update(facts)

        amounts = finding.get("amounts") or {}
        if "amount" not in context and isinstance(amounts, dict):
            issue_amount = amounts.get("issue_amount")
            if issue_amount is not None:
                context["amount"] = issue_amount

    return context


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError(f"unsupported date value: {value!r}")


def _get_path(data: dict, path: str) -> tuple[bool, Any]:
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _condition_value(context: dict, condition: dict) -> bool | None:
    field = condition["field"]
    operator = condition["operator"]
    expected = condition.get("value")
    present, actual = _get_path(context, field)

    if operator == "exists":
        return present is bool(expected)
    if not present:
        return None
    if operator == "eq":
        return actual == expected
    if operator == "neq":
        return actual != expected
    if operator == "in":
        return actual in expected
    if operator == "not_in":
        return actual not in expected
    if operator == "gte":
        return actual >= expected
    if operator == "lte":
        return actual <= expected
    raise ValueError(f"unsupported condition operator: {operator}")


def _scope_check(actual: Any, allowed: list[str], label: str) -> tuple[str | None, str | None]:
    if not allowed:
        return None, None
    if actual is None:
        return "needs_review", f"缺少{label}事实，无法判断适用范围"
    if actual not in allowed:
        return "not_applicable", f"{label}不在法规适用范围内"
    return None, None


def evaluate_applicability(
    context: dict,
    law: dict,
    event_date: date | None = None,
) -> ApplicabilityResult:
    """Evaluate one Law Object against one project/finding context.

    The function only filters applicability. It does not rank laws or decide
    which candidate is legally preferable.
    """
    needs_review: list[str] = []

    source = law.get("source") or {}
    if source.get("verified") is not True:
        needs_review.append("法规来源尚未核验，不能作为已确认依据")

    # 1. Effective period / status.
    status = law.get("status")
    start = _coerce_date(law.get("effective_from"))
    end = _coerce_date(law.get("effective_to"))
    event = _coerce_date(event_date)
    if event is None:
        context_event = context.get("event_date")
        event = _coerce_date(context_event) if context_event is not None else None

    if status == "unknown":
        needs_review.append("法规效力状态未知")
    if status in {"repealed", "superseded"} and end is None:
        needs_review.append("历史法规缺少失效日期，无法确认历史适用期")
    if start is not None or end is not None:
        if event is None:
            needs_review.append("缺少业务发生日期，无法判断法规时效")
        else:
            if start is not None and event < start:
                return ApplicabilityResult("not_applicable", ["业务发生日在法规生效日期之前"])
            if end is not None and event > end:
                return ApplicabilityResult("not_applicable", ["业务发生日在法规失效日期之后"])
    if status == "pending" and (event is None or start is None or event >= start):
        needs_review.append("法规状态为 pending，不能作为已确认现行依据")

    # 2. Jurisdiction.
    law_jur = law.get("jurisdiction") or {}
    ctx_jur = context.get("jurisdiction") or {}
    for field, label in (("country", "国家"), ("province", "省级地域"), ("city", "市级地域"), ("county", "县级地域")):
        required = law_jur.get(field)
        if required in (None, ""):
            continue
        actual = ctx_jur.get(field)
        if actual in (None, ""):
            needs_review.append(f"缺少{label}信息，无法判断地域适用")
            continue
        if actual != required:
            return ApplicabilityResult("not_applicable", [f"{label}不匹配：需要 {required}，实际 {actual}"])

    # 3. Subject.
    subject = law.get("subject_scope") or {}
    organization = context.get("organization") or {}
    subject_checks = [
        (organization.get("type"), subject.get("organization_types") or [], "单位性质"),
        (organization.get("level"), subject.get("organization_levels") or [], "单位层级"),
        (context.get("person_type"), subject.get("person_types") or [], "人员身份"),
    ]
    for actual, allowed, label in subject_checks:
        outcome, reason = _scope_check(actual, allowed, label)
        if outcome == "not_applicable":
            return ApplicabilityResult(outcome, [reason])
        if outcome == "needs_review":
            needs_review.append(reason)

    # 4. Business matter.
    business_scope = law.get("business_scope") or []
    outcome, reason = _scope_check(context.get("business_type"), business_scope, "业务事项")
    if outcome == "not_applicable":
        return ApplicabilityResult(outcome, [reason])
    if outcome == "needs_review":
        needs_review.append(reason)

    # 5. Funding.
    funding_scope = law.get("funding_scope") or []
    if funding_scope:
        actual_funding = context.get("funding")
        if actual_funding is None:
            needs_review.append("缺少资金性质，无法判断资金适用范围")
        else:
            actual_set = set(actual_funding if isinstance(actual_funding, list) else [actual_funding])
            if not actual_set.intersection(funding_scope):
                return ApplicabilityResult("not_applicable", ["资金性质不在法规适用范围内"])

    # 6. Required facts / evidence.
    for condition in law.get("applies_if") or []:
        matched = _condition_value(context, condition)
        if matched is False:
            return ApplicabilityResult("not_applicable", [f"适用前提不满足：{condition['field']}"])
        if matched is None:
            needs_review.append(f"缺少适用前提事实：{condition['field']}")

    for condition in law.get("excludes_if") or []:
        matched = _condition_value(context, condition)
        if matched is True:
            return ApplicabilityResult("not_applicable", [f"命中排除条件：{condition['field']}"])
        if matched is None:
            needs_review.append(f"缺少排除条件事实：{condition['field']}")

    if needs_review:
        return ApplicabilityResult("needs_review", needs_review)
    return ApplicabilityResult("applicable", ["时效、地域、主体、事项、资金及事实/证据条件均满足"])
