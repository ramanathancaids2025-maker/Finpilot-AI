import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'finpilot.db')
SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    print(f"Initializing database at: {DB_PATH}")
    conn = get_db_connection()
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
    
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS user_count FROM users")
    if cursor.fetchone()['user_count'] > 0:
        conn.commit()
        conn.close()
        print("Database schema verified; existing data preserved.")
        return
    
    # 1. Insert Default User Profile in Rupees (₹)
    # Income: ₹1,50,000/mo, Current Savings: ₹4,50,000
    cursor.execute("""
        INSERT INTO users (name, email, monthly_income, current_savings)
        VALUES (?, ?, ?, ?)
    """, ("Alex Morgan", "alex.morgan@finpilot.ai", 150000.0, 450000.0))
    user_id = cursor.lastrowid

    # 2. Insert Category Budgets in INR (₹)
    budgets = [
        ("Housing & Utilities", 35000.0),
        ("Food & Dining", 18000.0),
        ("Transportation", 8000.0),
        ("Shopping & Electronics", 12000.0),
        ("Entertainment & Leisure", 7000.0),
        ("Healthcare & Fitness", 5000.0),
        ("Investments & Savings", 55000.0),
        ("Subscriptions & Misc", 4000.0)
    ]
    for cat, amt in budgets:
        cursor.execute("""
            INSERT INTO monthly_budgets (user_id, category, allocated_amount)
            VALUES (?, ?, ?)
        """, (user_id, cat, amt))

    # 3. Insert Savings Goals in INR (₹)
    goals = [
        ("Emergency Reserve", 500000.0, 450000.0, "2026-12-31"),
        ("New MacBook Pro", 180000.0, 120000.0, "2026-09-30"),
        ("Japan Vacation", 250000.0, 140000.0, "2027-04-15")
    ]
    for title, target, curr, target_date in goals:
        cursor.execute("""
            INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, title, target, curr, target_date))

    # 4. Generate realistic historical transactions in INR over past 3 months (~12 concise total entries)
    today = datetime.now()
    
    # Monthly Income Credits
    cursor.execute("INSERT INTO transactions (user_id, date, title, amount, category, type) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, (today - timedelta(days=2)).strftime("%Y-%m-%d"), "Monthly Salary Credit", 150000.0, "Income", "income"))
    cursor.execute("INSERT INTO transactions (user_id, date, title, amount, category, type) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, (today - timedelta(days=16)).strftime("%Y-%m-%d"), "Freelance Consulting Credit", 25000.0, "Income", "income"))
    cursor.execute("INSERT INTO transactions (user_id, date, title, amount, category, type) VALUES (?, ?, ?, ?, ?, ?)",
                   (user_id, (today - timedelta(days=32)).strftime("%Y-%m-%d"), "Monthly Salary Credit", 150000.0, "Income", "income"))

    # Expenses (Clean, non-repetitive entries)
    expenses_seed = [
        ("House Rent Payment", 32000.0, "Housing & Utilities", 3),
        ("Electricity Bill (BESCOM)", 4500.0, "Housing & Utilities", 6),
        ("Starbucks Coffee & Snacks", 1850.0, "Food & Dining", 8),
        ("Amazon.in Electronics", 6490.0, "Shopping & Electronics", 12),
        ("Zomato Dinner Order", 2150.0, "Food & Dining", 15),
        ("Cult.fit Gym Subscription", 2500.0, "Healthcare & Fitness", 18),
        ("Shell Petrol Filling", 2400.0, "Transportation", 21),
        ("Zepto Grocery Delivery", 2850.0, "Food & Dining", 24),
        ("PVR Movie Tickets", 1600.0, "Entertainment & Leisure", 27)
    ]

    for title, amount, cat, days_ago in expenses_seed:
        tx_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        cursor.execute("""
            INSERT INTO transactions (user_id, date, title, amount, category, type)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, tx_date, title, amount, cat, "expense"))

    conn.commit()
    conn.close()
    print("Database initialized with balanced Rupee (INR) seed data.")

if __name__ == '__main__':
    init_db()
