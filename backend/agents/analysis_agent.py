import sqlite3
import os
import numpy as np
import pandas as pd
from datetime import datetime
from backend.database.db import get_db_connection

class AnalysisAgent:
    def __init__(self):
        pass

    def run_analysis(self, user_id=1):
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Fetch User Profile
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            raise ValueError(f"[CRITICAL ERROR] User id={user_id} not found in database! (File: backend/agents/analysis_agent.py, Line 20)")

        base_income = float(user['monthly_income'])
        current_savings = float(user['current_savings'])

        # 2. Fetch Transactions from SQLite
        query = "SELECT amount, category, type, date FROM transactions WHERE user_id = ?"
        df_tx = pd.read_sql_query(query, conn, params=(user_id,))
        conn.close()

        # Handle empty transaction tables gracefully
        if df_tx.empty:
            return {
                "user_id": user_id,
                "monthly_income": base_income,
                "monthly_expenses": 0.0,
                "current_savings": current_savings,
                "monthly_surplus": base_income,
                "expense_ratio": 0.0,
                "tx_count": 0,
                "cat_variance": 0.1,
                "category_distribution": {"General": 0.0},
                "top_category": "None"
            }

        df_tx['amount'] = df_tx['amount'].astype(float)
        df_tx['date'] = pd.to_datetime(df_tx['date'])

        # Determine date window: use rolling past 30 days to capture full category distribution
        now = datetime.now()
        thirty_days_ago = now - pd.Timedelta(days=30)
        df_active = df_tx[df_tx['date'] >= thirty_days_ago]

        if df_active.empty:
            df_active = df_tx

        df_expenses = df_active[df_active['type'] == 'expense']
        df_income = df_active[df_active['type'] == 'income']

        # If active window has no expenses, fall back to all-time expenses
        if df_expenses.empty:
            df_expenses = df_tx[df_tx['type'] == 'expense']

        # If active window has no income, fall back to all-time income
        if df_income.empty:
            df_income = df_tx[df_tx['type'] == 'income']

        # Calculate monthly income (sum of income txns in window, fallback to base_income)
        income_sum = float(df_income['amount'].sum()) if not df_income.empty else 0.0
        monthly_income = round(max(base_income, income_sum), 2)

        # Calculate monthly expenses (handle zero expense transactions gracefully)
        if df_expenses.empty:
            monthly_expenses = 0.0
            tx_count = 0
            category_totals = {"General": 0.0}
            cat_variance = 0.1
            top_category = "None"
        else:
            monthly_expenses = round(float(df_expenses['amount'].sum()), 2)
            tx_count = len(df_expenses)

            # Category totals calculation
            cat_series = df_expenses.groupby('category')['amount'].sum()
            category_totals = {str(k): round(float(v), 2) for k, v in cat_series.to_dict().items()}
            if not category_totals:
                category_totals = {"General": 0.0}

            # Compute category variance (entropy measure)
            cat_amounts = np.array(list(category_totals.values()))
            if len(cat_amounts) > 0 and cat_amounts.sum() > 0:
                props = cat_amounts / cat_amounts.sum()
                cat_variance = float(-np.sum(props * np.log(props + 1e-9)))
            else:
                cat_variance = 0.1

            top_category = max(category_totals, key=category_totals.get)

        expense_ratio = round(monthly_expenses / (monthly_income + 1e-5), 4)
        monthly_surplus = round(monthly_income - monthly_expenses, 2)

        # DEBUG LOGGING (Requirement 4)
        print(f"\n--- [AnalysisAgent Debug Pass] ---")
        print(f"Loaded transactions: {len(df_tx)} total rows in database")
        print(f"Active window rows: {len(df_active)} rows")
        print(f"Total income: INR {monthly_income:,.2f}")
        print(f"Total expenses: INR {monthly_expenses:,.2f}")
        print(f"Monthly surplus: INR {monthly_surplus:,.2f}")
        print(f"Expense ratio: {expense_ratio*100:.1f}%")
        print(f"Category totals: {category_totals}")
        print(f"Top category: {top_category}")
        print(f"-----------------------------------\n")

        return {
            "user_id": user_id,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "current_savings": current_savings,
            "monthly_surplus": monthly_surplus,
            "expense_ratio": expense_ratio,
            "tx_count": tx_count,
            "cat_variance": round(cat_variance, 4),
            "category_distribution": category_totals,
            "top_category": top_category
        }

