import os
import re
import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'purchase_model.joblib')

ITEM_PRICE_DATABASE = {
    "ps5": 50000.0,
    "playstation": 50000.0,
    "playstation 5": 50000.0,
    "macbook": 120000.0,
    "macbook pro": 180000.0,
    "macbook air": 95000.0,
    "iphone": 80000.0,
    "iphone 16": 85000.0,
    "car": 800000.0,
    "bike": 150000.0,
    "motorcycle": 180000.0,
    "watch": 25000.0,
    "tv": 45000.0,
    "television": 45000.0,
    "vacation": 100000.0,
    "trip": 80000.0,
    "gaming pc": 150000.0,
    "laptop": 65000.0
}

class PurchaseAgent:
    def __init__(self):
        self.model_data = None
        if os.path.exists(MODEL_PATH):
            self.model_data = joblib.load(MODEL_PATH)

    def extract_item_and_price(self, query):
        if not query:
            return "Item", 50000.0

        q = query.lower()
        
        # Check for explicit rupee / number amounts e.g., ₹5, 5rs, 5 rupees, $5
        price_match = re.search(r'(?:₹|rs\.?|\$)\s*([\d,]+(?:\.\d{2})?)', query, re.IGNORECASE)
        if not price_match:
            price_match = re.search(r'([\d,]+)\s*(?:rupees|inr|rs|dollars|usd|bucks|rs)', q)
        if not price_match:
            price_match = re.search(r'for\s*([\d,]+)\s*(?:rs|rupees)?', q)

        price = None
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
            except ValueError:
                price = None

        # Detect item name
        detected_item = "Requested Item"
        for item_key in ITEM_PRICE_DATABASE:
            if item_key in q:
                detected_item = item_key.title()
                if price is None:
                    price = ITEM_PRICE_DATABASE[item_key]
                break

        if price is None:
            # Look for any standalone number in query
            nums = re.findall(r'\b\d{1,7}\b', query)
            if nums:
                price = float(nums[0])
            else:
                price = 50000.0

        return detected_item, price

    def evaluate_purchase(self, query, financial_data, health_data, forecast_data):
        item_name, item_price = self.extract_item_and_price(query)

        income = financial_data.get('monthly_income', 150000)
        expenses = financial_data.get('monthly_expenses', 80000)
        savings = financial_data.get('current_savings', 450000)
        health_score = health_data.get('health_score', 75.0)
        monthly_surplus = financial_data.get('monthly_surplus', 70000)

        price_to_savings = item_price / (savings + 1e-5)
        price_to_surplus = item_price / (monthly_surplus + 1e-5)

        # Run Scikit-Learn Model Prediction
        if not self.model_data:
            if os.path.exists(MODEL_PATH):
                self.model_data = joblib.load(MODEL_PATH)
            else:
                raise FileNotFoundError(f"[CRITICAL ERROR] Purchase model missing at {MODEL_PATH}! (File: backend/agents/purchase_agent.py, Line 92)")

        model = self.model_data["model"]
        features = self.model_data["features"]

        input_df = pd.DataFrame([{
            'income': income,
            'monthly_expenses': expenses,
            'savings': savings,
            'health_score': health_score,
            'item_price': item_price,
            'monthly_surplus': monthly_surplus,
            'price_to_savings': price_to_savings,
            'price_to_surplus': price_to_surplus
        }])[features]

        decision_code = int(model.predict(input_df)[0])

        # Safety Check: Trivial / Micro-purchases (e.g. ₹500 item or price <= 2% of savings)
        if item_price <= 500 or price_to_savings <= 0.02:
            decision_code = 0

        # DEBUG LOGGING (Requirement 4)
        print(f"--- [PurchaseAgent Debug Pass] ---")
        print(f"Item: {item_name}, Price: INR {item_price:,.2f}")
        print(f"Model Inputs: {input_df.to_dict(orient='records')[0]}")
        print(f"Model Predicted Decision Code: {decision_code}")
        print(f"----------------------------------\n")

        status_map = {
            0: ("Safe to Buy", "YES - Safe Purchase", "emerald"),
            1: ("Moderate Caution", "MAYBE - Proceed with Caution", "cyan"),
            2: ("Risky", "NO - High Financial Risk", "amber"),
            3: ("Unaffordable", "NO - Exceeds Financial Capacity", "rose")
        }

        status_text, recommendation, color = status_map.get(decision_code, status_map[2])

        remaining_savings = max(0.0, round(savings - item_price, 2))
        months_to_recoup = round(item_price / (monthly_surplus + 1e-5), 1) if monthly_surplus > 0 else 99.0
        max_safe_budget = round(savings * 0.20 + (monthly_surplus if monthly_surplus > 0 else 0) * 0.5, 2)

        return {
            "item": item_name,
            "price": round(item_price, 2),
            "decision_code": decision_code,
            "status": status_text,
            "recommendation": recommendation,
            "theme_color": color,
            "impact": {
                "current_savings": savings,
                "post_purchase_savings": remaining_savings,
                "savings_reduction_pct": round(price_to_savings * 100, 1),
                "months_to_recoup": months_to_recoup,
                "max_safe_budget": max_safe_budget
            }
        }
