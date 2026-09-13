import os
import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'health_model.joblib')

class HealthAgent:
    def __init__(self):
        self.model_data = None
        if os.path.exists(MODEL_PATH):
            self.model_data = joblib.load(MODEL_PATH)
        else:
            raise FileNotFoundError(f"[CRITICAL ERROR] Health model file missing at {MODEL_PATH}! (File: backend/agents/health_agent.py, Line 13)")

    def evaluate_health(self, financial_data):
        if not self.model_data:
            raise RuntimeError(f"[CRITICAL ERROR] Health model not loaded! (File: backend/agents/health_agent.py, Line 18)")

        income = float(financial_data.get('monthly_income', 0))
        expenses = float(financial_data.get('monthly_expenses', 0))

        if income <= 0 and expenses <= 0:
            raise ValueError(f"[CRITICAL ERROR] Invalid financial metrics passed to HealthAgent: income={income}, expenses={expenses}! (File: backend/agents/health_agent.py, Line 22)")

        model = self.model_data["model"]
        features = self.model_data["features"]

        # Create input DataFrame matching model schema
        input_data = pd.DataFrame([{
            'income': income,
            'monthly_expenses': expenses,
            'savings': float(financial_data.get('current_savings', 0)),
            'expense_ratio': float(financial_data.get('expense_ratio', 0)),
            'tx_count': int(financial_data.get('tx_count', 1)),
            'cat_variance': float(financial_data.get('cat_variance', 0.1))
        }])[features]

        predicted_score = float(model.predict(input_data)[0])
        predicted_score = float(np.clip(predicted_score, 0.0, 100.0))

        if predicted_score >= 80.0:
            tier = "Excellent"
            risk = "Low Risk"
        elif predicted_score >= 65.0:
            tier = "Good"
            risk = "Moderate-Low Risk"
        elif predicted_score >= 50.0:
            tier = "Fair"
            risk = "Moderate-High Risk"
        else:
            tier = "Poor"
            risk = "High Risk"

        # Calculate sub-factor scores
        exp_ratio = float(financial_data.get('expense_ratio', 0.5))
        savings = float(financial_data.get('current_savings', 0))
        months_runway = savings / (expenses + 1e-5)

        savings_health = min(100.0, round((months_runway / 6.0) * 100.0, 1))
        spending_health = max(0.0, round((1.0 - exp_ratio) * 100.0, 1))

        # DEBUG LOGGING (Requirement 4)
        print(f"--- [HealthAgent Debug Pass] ---")
        print(f"Extracted features: {input_data.to_dict(orient='records')[0]}")
        print(f"Model prediction score: {predicted_score:.1f}/100")
        print(f"Health Tier: {tier}, Risk Level: {risk}")
        print(f"--------------------------------\n")

        return {
            "health_score": round(predicted_score, 1),
            "health_tier": tier,
            "risk_level": risk,
            "breakdown": {
                "savings_runway_months": round(months_runway, 1),
                "savings_health_score": savings_health,
                "spending_health_score": spending_health,
                "expense_ratio_pct": round(exp_ratio * 100, 1)
            }
        }

