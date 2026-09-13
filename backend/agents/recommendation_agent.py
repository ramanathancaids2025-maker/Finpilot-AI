class RecommendationAgent:
    def __init__(self):
        pass

    def generate_response(self, intent_data, analysis_data, health_data,
                          budget_data, purchase_data, forecast_data,
                          query="", validation_res=None):
        intent     = intent_data.get("intent", "General Question")
        confidence = intent_data.get("confidence", 1.0)

        health_score = health_data.get("health_score", 70)
        health_tier  = health_data.get("health_tier", "Good")
        risk_level   = health_data.get("risk_level", "Low Risk")
        surplus      = analysis_data.get("monthly_surplus", 0)
        top_cat      = analysis_data.get("top_category", "Expenses")
        f6m          = forecast_data.get("forecast_6_months", 0)

        # ---------------------------------------------------------------- #
        # Build correction preamble if ValidationAgent corrected anything   #
        # ---------------------------------------------------------------- #
        correction_block = ""
        if validation_res and validation_res.get("is_self_corrected"):
            corrections   = validation_res.get("corrections_applied", [])
            ai_insight    = validation_res.get("ai_insight", "")
            emergency_rec = validation_res.get("emergency_recommendations", [])
            rules_hit     = ", ".join(c["rule"] for c in corrections)

            correction_block = (
                f"\n> ⚠️ **Prediction Corrected** (Rules: {rules_hit})\n"
                f"> *{corrections[0]['reason']}*\n\n"
            )

            if ai_insight:
                correction_block += f"**AI Insight**: {ai_insight}\n\n"

            if emergency_rec:
                correction_block += (
                    "**🚨 Emergency Action Plan**\n"
                    + "\n".join(f"- {r}" for r in emergency_rec)
                    + "\n\n"
                )

        # ---------------------------------------------------------------- #
        # Intent-specific response bodies                                   #
        # ---------------------------------------------------------------- #
        if intent == "Greeting":
            response_text = (
                f"Namaste! I am **FinPilot AI**, your multi-agent personal finance engine. "
                f"Your current Financial Health Score is **{health_score}/100 ({health_tier})** "
                f"with a monthly net surplus of **₹{surplus:,.2f}**. "
                f"How can I assist you with your budget, savings forecast, or purchase decisions today?"
            )

        elif intent == "Spending Analysis":
            cat_dist   = analysis_data.get("category_distribution", {})
            cat_summary = ", ".join([f"**{k}**: ₹{v:,.2f}/mo" for k, v in list(cat_dist.items())[:4]])
            response_text = (
                f"### Spending Analysis\n"
                f"Your total monthly expenses are **₹{analysis_data.get('monthly_expenses', 0):,.2f}** "
                f"against an income of **₹{analysis_data.get('monthly_income', 0):,.2f}** "
                f"(Expense Ratio: **{analysis_data.get('expense_ratio', 0)*100:.1f}%**).\n\n"
                f"- **Top Spending Category**: {top_cat}\n"
                f"- **Category Breakdown**: {cat_summary}\n\n"
                f"**AI Recommendation**: Reallocating 15% from *{top_cat}* could increase "
                f"annual savings by **₹{cat_dist.get(top_cat, 0)*0.15*12:,.2f}**."
            )

        elif intent == "Financial Health":
            breakdown = health_data.get("breakdown", {})
            response_text = (
                f"### Financial Health Assessment\n"
                f"Your AI Financial Health Score is **{health_score}/100** "
                f"(**{health_tier}**, *{risk_level}*).\n\n"
                f"- **Emergency Runway**: {breakdown.get('savings_runway_months', 0)} months of expenses saved\n"
                f"- **Savings Health Index**: {breakdown.get('savings_health_score', 0)}/100\n"
                f"- **Spending Health Index**: {breakdown.get('spending_health_score', 0)}/100\n\n"
                f"**Next Action**: Maintain an emergency cushion of at least 6 months to elevate "
                f"your health score to Excellent."
            )

        elif intent == "Purchase Decision":
            item   = purchase_data.get("item", "Item")
            price  = purchase_data.get("price", 0.0)
            rec    = purchase_data.get("recommendation", "")
            impact = purchase_data.get("impact", {})

            # Rule 5 — enrich with pre-check explanation if triggered
            precheck = validation_res.get("purchase_precheck") if validation_res else None
            if precheck and not precheck.get("affordable", True):
                blockers_str = "\n".join(f"  - {b}" for b in precheck.get("blockers", []))
                passes_str   = "\n".join(f"  - {p}" for p in precheck.get("passes", []))
                response_text = (
                    f"### Purchase Decision: **{item}** (₹{price:,.2f})\n"
                    f"**Verdict**: ❌ {rec}\n\n"
                    f"**Why this purchase is not recommended** "
                    f"({precheck.get('factor_summary', '')}):\n"
                    f"{blockers_str}\n\n"
                    f"**Factors that passed:**\n"
                    f"{passes_str}\n\n"
                    f"**Recommendation**: Stabilise your monthly surplus before making this purchase. "
                    f"Once surplus is positive, you can save for this item over time."
                )
            else:
                response_text = (
                    f"### Purchase Decision: **{item}** (₹{price:,.2f})\n"
                    f"**Verdict**: {rec} ({purchase_data.get('status', 'Evaluated')})\n\n"
                    f"- **Post-Purchase Savings**: ₹{impact.get('post_purchase_savings', 0):,.2f} "
                    f"(reduced by {impact.get('savings_reduction_pct', 0)}%)\n"
                    f"- **Recoup Time**: {impact.get('months_to_recoup', 0)} months of monthly surplus\n"
                    f"- **Max Recommended Safe Purchase**: ₹{impact.get('max_safe_budget', 0):,.2f}\n\n"
                    f"**AI Recommendation**: " + (
                        "Buying this item is safe and fits within your liquid reserves."
                        if purchase_data.get("decision_code") == 0 else
                        f"Proceed with caution — save for {impact.get('months_to_recoup', 1.0)} "
                        f"more months to avoid depleting emergency reserves."
                    )
                )

        elif intent == "Savings":
            f12m = forecast_data.get("forecast_12_months", 0)
            # Show corrected note if forecasts were zeroed
            correction_note = forecast_data.get("correction_note", "")
            savings_insight = (
                f"⚠️ {correction_note}"
                if correction_note else
                f"You are on track to build ₹{forecast_data.get('net_gain_12m', 0):,.2f} "
                f"in wealth over the next year."
            )
            response_text = (
                f"### Savings Performance & Reserves\n"
                f"Your liquid savings balance: **₹{analysis_data.get('current_savings', 0):,.2f}**\n\n"
                f"- **Monthly Net Savings Rate**: ₹{surplus:,.2f}/month\n"
                f"- **Projected 6-Month Savings**: **₹{f6m:,.2f}**\n"
                f"- **Projected 12-Month Savings**: **₹{f12m:,.2f}**\n\n"
                f"**AI Insight**: {savings_insight}"
            )

        elif intent == "Budget":
            over_cats = budget_data.get("over_budget_categories", [])
            over_str  = ", ".join([f"*{b['category']}*" for b in over_cats]) if over_cats else "None"
            response_text = (
                f"### AI Budget Optimization (50/30/20 Strategy)\n"
                f"Based on your **{health_tier}** health tier, here are your optimized monthly targets:\n\n"
                f"- **Essential Needs (50%)**: Target ₹{budget_data['target_allocation']['needs_budget']:,.2f} "
                f"(Actual: ₹{budget_data['actual_spending']['needs']:,.2f})\n"
                f"- **Wants & Discretionary (30%)**: Target ₹{budget_data['target_allocation']['wants_budget']:,.2f} "
                f"(Actual: ₹{budget_data['actual_spending']['wants']:,.2f})\n"
                f"- **Target Monthly Savings (20%)**: ₹{budget_data['target_allocation']['savings_target']:,.2f}\n\n"
                f"**Optimization Focus**: Over-budget areas: {over_str}. "
                f"Fixing these could boost monthly savings by **₹{budget_data.get('potential_monthly_savings', 0):,.2f}**."
            )

        elif intent == "Forecast":
            correction_note = forecast_data.get("correction_note", "")
            forecast_header = (
                f"> ⚠️ **Forecast Corrected**: {correction_note}\n\n"
                if correction_note else ""
            )
            response_text = (
                f"### Multi-Month Savings Forecast\n"
                f"{forecast_header}"
                f"Based on financial trend analysis and projection, here are your estimated savings balances:\n\n"
                f"- **3-Month Horizon**: **₹{forecast_data.get('forecast_3_months', 0):,.2f}**\n"
                f"- **6-Month Horizon**: **₹{forecast_data.get('forecast_6_months', 0):,.2f}**\n"
                f"- **12-Month Horizon**: **₹{forecast_data.get('forecast_12_months', 0):,.2f}**\n\n"
                f"**Growth Potential**: Net gain of **₹{forecast_data.get('net_gain_12m', 0):,.2f}** "
                f"under steady spending behaviour."
            )

        elif intent == "General Question":
            response_text = (
                f"FinPilot AI is a multi-agent personal finance assistant powered by local machine learning. "
                f"I evaluate financial data using 8 specialised AI agents including Intent Classifier, "
                f"Health Predictor, Budget Optimizer, Purchase Evaluator, Savings Forecaster, and a "
                f"**Prediction Validation Agent** that self-corrects impossible results before they reach you. "
                f"Try asking: *'Can I buy a PS5 for ₹50,000?'* or *'Predict my 6-month savings'*!"
            )

        else:
            response_text = (
                f"I processed your query with intent **{intent}** (Confidence: {confidence*100:.1f}%). "
                f"Your overall Financial Health is **{health_score}/100** with **₹{surplus:,.2f}** "
                f"monthly surplus and **₹{f6m:,.2f}** forecasted 6-month savings."
            )

        # Prepend correction block (if any) in front of every intent response
        return correction_block + response_text
