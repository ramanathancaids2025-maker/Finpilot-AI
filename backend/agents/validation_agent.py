"""
Prediction Validation Agent
============================
A self-correcting AI reasoning layer that sits between the Savings Forecast Agent
and the Recommendation Generator in the coordinator pipeline.

It detects impossible financial predictions, overwrites them with correct values,
explains WHY the correction was made, and generates a single dynamic AI insight.

Rules:
  R1 — Expenses > Income      → forecast must be negative / Not Possible
  R2 — Monthly surplus ≤ 0   → all forecasts = ₹0, trajectory flat
  R3 — Expense ratio > 100%  → risk_level = Critical, health_tier = Poor
  R4 — Health score < 40     → inject emergency recommendations
  R5 — Purchase intent        → 5-factor pre-check before answering
  R6 — Prediction contradicts metrics → overwrite + log self-correction
"""

import copy


class ValidationAgent:
    def __init__(self):
        pass

    # ------------------------------------------------------------------ #
    #  Public entry point                                                  #
    # ------------------------------------------------------------------ #

    def validate(self, analysis_res: dict, health_res: dict,
                 forecast_res: dict, purchase_res: dict,
                 query: str = "", intent: str = "") -> dict:
        """
        Run all validation rules and return a corrected, enriched result dict.

        Returns
        -------
        {
            "validated": True,
            "is_self_corrected": bool,
            "corrections_applied": [{"rule": str, "reason": str}],
            "corrected_forecast": dict,       # safe to use on dashboard
            "corrected_health": dict,         # safe to use on dashboard
            "purchase_precheck": dict | None, # Rule 5 enrichment
            "emergency_recommendations": [],  # Rule 4
            "ai_insight": str,
        }
        """
        # Work on deep copies — never mutate upstream agent output
        forecast = copy.deepcopy(forecast_res)
        health   = copy.deepcopy(health_res)

        corrections    = []
        emergency_recs = []
        purchase_check = None

        income          = analysis_res.get("monthly_income", 0)
        expenses        = analysis_res.get("monthly_expenses", 0)
        surplus         = analysis_res.get("monthly_surplus", 0)
        expense_ratio   = analysis_res.get("expense_ratio", 0)
        health_score    = health.get("health_score", 100)
        top_category    = analysis_res.get("top_category", "Unknown")
        cat_dist        = analysis_res.get("category_distribution", {})
        current_savings = analysis_res.get("current_savings", 0)

        # ---- Rule 1: Expenses > Income -----------------------------------
        if expenses > income:
            reason = (
                f"Expenses (₹{expenses:,.2f}) exceed Income (₹{income:,.2f}). "
                f"Monthly savings are negative (₹{surplus:,.2f}). "
                f"Positive forecasts are logically impossible."
            )
            forecast = self._correct_deficit_forecast(forecast, current_savings, surplus)
            forecast["months_to_goal"] = "Not Possible"
            corrections.append({"rule": "R1", "reason": reason})

        # ---- Rule 2: Monthly surplus ≤ 0 --------------------------------
        if surplus <= 0:
            reason = (
                f"Monthly net surplus is ₹{surplus:,.2f}. "
                f"No savings are being accumulated. "
                f"Forward forecasts now reflect the monthly deficit."
            )
            forecast = self._correct_deficit_forecast(forecast, current_savings, surplus)
            if not any(c["rule"] == "R1" for c in corrections):
                corrections.append({"rule": "R2", "reason": reason})

        # ---- Rule 3: Expense ratio > 100% --------------------------------
        if expense_ratio > 1.0:
            reason = (
                f"Expense ratio is {expense_ratio*100:.1f}% — spending exceeds income. "
                f"Risk level escalated to Critical."
            )
            health["risk_level"] = "Critical"
            health["health_tier"] = "Poor"
            # Also clamp health score to ≤ 35 if ratio is that bad
            health["health_score"] = min(health.get("health_score", 35), 35.0)
            corrections.append({"rule": "R3", "reason": reason})

        # ---- Rule 4: Health score < 40 → emergency recommendations ------
        effective_score = health.get("health_score", health_score)
        if effective_score < 40:
            top_cat_amount = cat_dist.get(top_category, 0)
            savings_15pct  = round(top_cat_amount * 0.15, 2)
            emergency_recs = [
                f"🔴 Reduce **{top_category}** spending by 15% — saves ₹{savings_15pct:,.2f}/month",
                "🔴 Avoid all luxury or discretionary purchases until surplus is positive",
                "🔴 Build an emergency fund of at least 3 months of expenses before new goals",
                f"🔴 Target expense ratio below 80% (currently {expense_ratio*100:.1f}%)",
            ]
            corrections.append({
                "rule": "R4",
                "reason": (
                    f"Financial Health Score is {effective_score}/100 (<40). "
                    f"Emergency action plan generated."
                )
            })

        # ---- Rule 5: Purchase intent pre-check ---------------------------
        is_purchase_intent = (
            intent == "Purchase Decision"
            or any(kw in query.lower() for kw in ["buy", "afford", "purchase", "get a", "can i get"])
        )
        if is_purchase_intent:
            purchase_check = self._run_purchase_precheck(
                purchase_res, analysis_res, health, current_savings, expense_ratio
            )
            if not purchase_check["affordable"]:
                corrections.append({
                    "rule": "R5",
                    "reason": purchase_check["reason"]
                })

        # ---- Rule 6: Forecast contradicts metrics (catch-all) ------------
        raw_f6m = forecast_res.get("forecast_6_months", 0)
        corrected_f6m = forecast.get("forecast_6_months", 0)
        if surplus <= 0 and raw_f6m > current_savings:
            reason = (
                f"Prediction model returned 6M forecast of ₹{raw_f6m:,.2f} "
                f"but monthly surplus is ₹{surplus:,.2f}. "
                f"Prediction overwritten to ₹{corrected_f6m:,.2f}."
            )
            if not any(c["rule"] in ("R1", "R2") for c in corrections):
                corrections.append({"rule": "R6", "reason": reason})

        # ---- Generate single AI insight ----------------------------------
        ai_insight = self._generate_ai_insight(
            corrections, analysis_res, health, top_category, cat_dist, surplus
        )

        is_self_corrected = len(corrections) > 0

        return {
            "validated": True,
            "is_self_corrected": is_self_corrected,
            "corrections_applied": corrections,
            "corrected_forecast": forecast,
            "corrected_health": health,
            "purchase_precheck": purchase_check,
            "emergency_recommendations": emergency_recs,
            "ai_insight": ai_insight,
        }

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #

    def _correct_deficit_forecast(self, forecast: dict, current_savings: float,
                                  monthly_surplus: float) -> dict:
        """Project savings decline from the current balance during a deficit."""
        projected_values = [
            max(0.0, current_savings + (monthly_surplus * months))
            for months in (3, 6, 12)
        ]
        forecast["forecast_3_months"] = round(projected_values[0], 2)
        forecast["forecast_6_months"] = round(projected_values[1], 2)
        forecast["forecast_12_months"] = round(projected_values[2], 2)
        forecast["monthly_net_surplus"] = monthly_surplus
        forecast["net_gain_12m"] = round(projected_values[2] - current_savings, 2)
        forecast["forecast_status"] = "Deficit" if monthly_surplus < 0 else "No Monthly Surplus"
        forecast["trajectory"] = [
            {
                "month": f"Month {m}",
                "projected_savings": round(
                    max(0.0, current_savings + (monthly_surplus * m)), 2
                )
            }
            for m in range(1, 13)
        ]
        forecast["correction_note"] = (
            "Savings are projected to decline because monthly expenses meet or exceed income."
        )
        return forecast

    def _run_purchase_precheck(self, purchase_res: dict, analysis_res: dict,
                                health: dict, current_savings: float,
                                expense_ratio: float) -> dict:
        """
        Rule 5 — 5-factor affordability pre-check.
        Returns enriched dict explaining whether and WHY a purchase is (un)affordable.
        """
        item       = purchase_res.get("item", "Item")
        price      = purchase_res.get("price", 0.0)
        surplus    = analysis_res.get("monthly_surplus", 0)
        risk_level = health.get("risk_level", "")
        score      = health.get("health_score", 100)

        # Load savings goals progress (passed as part of analysis if available)
        blockers = []
        passes   = []

        # Factor 1: Current savings vs price
        if current_savings < price:
            blockers.append(
                f"💰 **Savings insufficient**: ₹{current_savings:,.2f} < ₹{price:,.2f} item price"
            )
        else:
            passes.append(f"✅ Savings (₹{current_savings:,.2f}) cover the price")

        # Factor 2: Emergency fund (need ≥ 3 months of expenses)
        monthly_expenses = analysis_res.get("monthly_expenses", 1)
        emergency_threshold = monthly_expenses * 3
        if current_savings < emergency_threshold:
            blockers.append(
                f"🚨 **No emergency fund**: Need ₹{emergency_threshold:,.2f} (3 months) "
                f"— currently ₹{current_savings:,.2f}"
            )
        else:
            passes.append(f"✅ Emergency fund adequate (₹{current_savings:,.2f})")

        # Factor 3: Expense ratio
        if expense_ratio > 0.85:
            blockers.append(
                f"📊 **Expense ratio critical**: {expense_ratio*100:.1f}% of income spent "
                f"(safe threshold: <85%)"
            )
        else:
            passes.append(f"✅ Expense ratio {expense_ratio*100:.1f}% within safe range")

        # Factor 4: Risk level
        if risk_level in ("Critical", "High Risk"):
            blockers.append(
                f"⚠️ **Risk level {risk_level}**: High-risk financial state "
                f"(Health Score: {score}/100)"
            )
        else:
            passes.append(f"✅ Risk level {risk_level} is manageable")

        # Factor 5: Monthly surplus
        if surplus <= 0:
            blockers.append(
                f"📉 **Negative surplus**: Monthly savings are ₹{surplus:,.2f} — "
                f"spending exceeds income"
            )
        else:
            months_to_save = round(price / surplus, 1) if surplus > 0 else 99.9
            passes.append(
                f"✅ Can save for this in {months_to_save} months at current surplus"
            )

        affordable = len(blockers) == 0

        if affordable:
            reason = f"All 5 financial factors clear for purchasing {item} (₹{price:,.2f})."
        else:
            reason = (
                f"Purchase of **{item}** (₹{price:,.2f}) is not recommended. "
                f"{len(blockers)} of 5 financial factors failed:\n"
                + "\n".join(blockers)
            )

        return {
            "item": item,
            "price": price,
            "affordable": affordable,
            "blockers": blockers,
            "passes": passes,
            "reason": reason,
            "factor_summary": f"{len(passes)}/5 factors passed"
        }

    def _generate_ai_insight(self, corrections: list, analysis_res: dict,
                              health: dict, top_category: str,
                              cat_dist: dict, surplus: float) -> str:
        """Generate one dynamic, context-aware AI insight sentence."""
        expense_ratio = analysis_res.get("expense_ratio", 0)
        income        = analysis_res.get("monthly_income", 0)
        expenses      = analysis_res.get("monthly_expenses", 0)
        top_amount    = cat_dist.get(top_category, 0)
        rule_ids      = [c["rule"] for c in corrections]

        if "R3" in rule_ids or expense_ratio > 1.0:
            overspend = round(expenses - income, 2)
            return (
                f"🔴 You are currently spending ₹{overspend:,.2f} more than you earn each month. "
                f"Immediate action needed: cut **{top_category}** by at least "
                f"₹{round(top_amount * 0.25, 2):,.2f} to begin recovering."
            )

        if "R4" in rule_ids:
            cut = round(top_amount * 0.15, 2)
            return (
                f"⚠️ Your Financial Health Score is critically low. "
                f"Reducing **{top_category}** by 15% (₹{cut:,.2f}/mo) is the fastest path "
                f"to stabilising your finances."
            )

        if "R1" in rule_ids or "R2" in rule_ids:
            return (
                f"📉 With a monthly deficit of ₹{abs(surplus):,.2f}, savings growth is paused. "
                f"Focus on bringing **{top_category}** under control before planning future goals."
            )

        # No critical corrections — positive insight
        health_tier = health.get("health_tier", "Good")
        if surplus > 0:
            annual_gain = round(surplus * 12, 2)
            return (
                f"✅ Your finances are on track ({health_tier} tier). "
                f"Maintaining your current surplus of ₹{surplus:,.2f}/month "
                f"will grow your wealth by ₹{annual_gain:,.2f} over the next year."
            )

        return (
            f"FinPilot AI has validated your financial predictions. "
            f"Health tier: **{health_tier}**. Review spending in **{top_category}** for optimisation."
        )
