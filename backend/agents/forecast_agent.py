import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'forecast_model.joblib')

class ForecastAgent:
    """
    Savings Forecast Agent using the trained multi-output Gradient Boosting model.
    Computes multi-horizon financial projections (3-month, 6-month, 12-month)
    and a month-by-month trajectory using the same model for each horizon.
    """
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Forecast model not found at {MODEL_PATH}")

        artifact = joblib.load(MODEL_PATH)
        if not isinstance(artifact, dict) or 'model' not in artifact:
            raise ValueError(f"Invalid forecast model artifact at {MODEL_PATH}")

        self.model = artifact['model']
        self.features = artifact.get('features', [
            'income', 'monthly_expenses', 'current_savings',
            'monthly_surplus', 'spending_volatility'
        ])
        self.targets = artifact.get('targets', [
            'forecast_3m', 'forecast_6m', 'forecast_12m'
        ])

    def forecast_savings(self, financial_data):
        income = float(financial_data.get('monthly_income', 0))
        expenses = float(financial_data.get('monthly_expenses', 0))
        current_savings = float(financial_data.get('current_savings', 0))
        monthly_surplus = float(financial_data.get('monthly_surplus', 0))
        volatility = float(np.clip(
            financial_data.get('cat_variance', 0.15), 0.02, 0.25
        ))

        if income <= 0 and expenses <= 0:
            # Graceful handling for brand new accounts with no transactions yet
            return {
                "current_savings": current_savings,
                "monthly_net_surplus": 0.0,
                "forecast_3_months": current_savings,
                "forecast_6_months": current_savings,
                "forecast_12_months": current_savings,
                "net_gain_12m": 0.0,
                "trajectory": [{"month": f"Month {m}", "projected_savings": current_savings} for m in range(1, 13)]
            }

        if monthly_surplus <= 0:
            projected_values = [
                max(0.0, current_savings + (monthly_surplus * months))
                for months in (3, 6, 12)
            ]
            monthly_trajectory = [
                {
                    "month": f"Month {month}",
                    "projected_savings": round(
                        max(0.0, current_savings + (monthly_surplus * month)), 2
                    )
                }
                for month in range(1, 13)
            ]
            return {
                "current_savings": current_savings,
                "monthly_net_surplus": monthly_surplus,
                "forecast_3_months": round(projected_values[0], 2),
                "forecast_6_months": round(projected_values[1], 2),
                "forecast_12_months": round(projected_values[2], 2),
                "net_gain_12m": round(projected_values[2] - current_savings, 2),
                "forecast_status": "Deficit" if monthly_surplus < 0 else "No Monthly Surplus",
                "correction_note": (
                    "Savings are projected to decline because monthly expenses meet or exceed income."
                ),
                "trajectory": monthly_trajectory
            }

        model_input = pd.DataFrame([{
            'income': income,
            'monthly_expenses': expenses,
            'current_savings': current_savings,
            'monthly_surplus': monthly_surplus,
            'spending_volatility': volatility
        }])[self.features]
        predictions = np.asarray(self.model.predict(model_input)[0], dtype=float)
        if predictions.size != len(self.targets):
            raise ValueError(
                f"Forecast model returned {predictions.size} values; "
                f"expected {len(self.targets)}"
            )

        forecast_values = np.maximum(0.0, predictions)
        f3m, f6m, f12m = forecast_values.tolist()

        monthly_trajectory = []
        for m in range(1, 13):
            horizon_index = min((m - 1) // 3, len(forecast_values) - 1)
            horizon_month = (horizon_index + 1) * 3
            start_value = current_savings if horizon_index == 0 else forecast_values[horizon_index - 1]
            end_value = forecast_values[horizon_index]
            progress = m / horizon_month if horizon_index == 0 else (m - horizon_index * 3) / 3
            projected = start_value + ((end_value - start_value) * progress)
            monthly_trajectory.append({
                "month": f"Month {m}",
                "projected_savings": round(max(0.0, projected), 2)
            })

        print(f"--- [Savings Forecast Agent (Gradient Boosting Model)] ---")
        print(f"Forecast Projections -> 3M: INR {f3m:,.2f}, 6M: INR {f6m:,.2f}, 12M: INR {f12m:,.2f}")
        print(f"--------------------------------------------------------------\n")

        return {
            "current_savings": current_savings,
            "monthly_net_surplus": monthly_surplus,
            "forecast_3_months": round(f3m, 2),
            "forecast_6_months": round(f6m, 2),
            "forecast_12_months": round(f12m, 2),
            "net_gain_12m": round(f12m - current_savings, 2),
            "trajectory": monthly_trajectory
        }


