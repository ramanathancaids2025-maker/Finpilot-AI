class BudgetAgent:
    def __init__(self):
        pass

    def optimize_budget(self, financial_data, health_data):
        income = financial_data.get('monthly_income', 5000)
        current_expenses = financial_data.get('category_distribution', {})
        total_spent = financial_data.get('monthly_expenses', 3000)
        health_tier = health_data.get('health_tier', 'Good')

        # 50/30/20 Rule: 50% Needs, 30% Wants, 20% Savings
        # Adjust allocation dynamically based on health tier
        if health_tier in ['Poor', 'Fair']:
            needs_pct, wants_pct, savings_pct = 0.55, 0.20, 0.25
        elif health_tier == 'Good':
            needs_pct, wants_pct, savings_pct = 0.50, 0.30, 0.20
        else: # Excellent
            needs_pct, wants_pct, savings_pct = 0.45, 0.25, 0.30

        target_needs = round(income * needs_pct, 2)
        target_wants = round(income * wants_pct, 2)
        target_savings = round(income * savings_pct, 2)

        # Categorize actual spending into Needs vs Wants
        needs_categories = ["Housing & Utilities", "Transportation", "Healthcare & Fitness"]
        wants_categories = ["Food & Dining", "Shopping & Electronics", "Entertainment & Leisure", "Subscriptions & Misc"]

        actual_needs = sum(current_expenses.get(cat, 0.0) for cat in needs_categories)
        actual_wants = sum(current_expenses.get(cat, 0.0) for cat in wants_categories)

        over_budget_cats = []
        optimizations = {}

        for cat, amount in current_expenses.items():
            if cat in wants_categories and amount > (target_wants * 0.35):
                suggested = round(amount * 0.8, 2)
                savings_potential = round(amount - suggested, 2)
                over_budget_cats.append({
                    "category": cat,
                    "current_spending": amount,
                    "recommended_limit": suggested,
                    "potential_monthly_savings": savings_potential
                })
                optimizations[cat] = suggested
            else:
                optimizations[cat] = amount

        potential_total_savings = sum(item["potential_monthly_savings"] for item in over_budget_cats)

        return {
            "strategy": f"Adaptive 50/30/20 ({health_tier} Financial Tier)",
            "target_allocation": {
                "needs_budget": target_needs,
                "wants_budget": target_wants,
                "savings_target": target_savings
            },
            "actual_spending": {
                "needs": round(actual_needs, 2),
                "wants": round(actual_wants, 2)
            },
            "over_budget_categories": over_budget_cats,
            "potential_monthly_savings": round(potential_total_savings, 2),
            "recommended_category_limits": optimizations
        }
