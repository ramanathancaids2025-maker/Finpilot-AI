import pandas as pd
import numpy as np
import random
import os

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_intent_dataset(n_samples=1500):
    print("Generating NLP Intent Dataset...")
    
    intent_templates = {
        "Greeting": [
            "hello", "hi there", "hey finpilot", "good morning", "good evening", "greetings assistant",
            "hey AI", "hi finpilot how are you", "start assistant", "hello finpilot", "namaste", "hi"
        ],
        "Spending Analysis": [
            "where is my money going", "how much did I spend this month", "show my expense distribution",
            "breakdown of my spending", "what did I spend on dining out", "analyze my recent transactions",
            "which category is taking most of my money", "show total expenses for this week",
            "give me spending metrics", "how much money did I spend on electronics", "spending summary",
            "why are my expenses so high", "review my transaction logs", "show expense report"
        ],
        "Savings": [
            "how much savings do I have", "what is my current savings balance", "how much should I put into savings",
            "check my emergency fund", "am I saving enough money each month", "show my savings progress",
            "what is my savings rate", "how close am I to my savings goal", "savings stats", "my total liquid savings"
        ],
        "Budget": [
            "show my category budget limits", "am I exceeding my food budget", "create a optimal monthly budget",
            "suggest budget allocations", "how to adjust my housing budget", "show 50 30 20 budget breakdown",
            "am I over budget this month", "rebalance my monthly spending limits", "budget recommendations"
        ],
        "Purchase Decision": [
            "can I afford to buy a PS5 for 50000", "should I purchase a new MacBook Pro", "can I buy an iPhone 16",
            "can I buy a motorcycle for 150000", "is it safe to purchase a luxury watch for 25000", "can I afford a vacation",
            "should I buy a gaming PC right now", "can I get a new car", "will buying a PS5 hurt my financial health",
            "can I afford buying a new television for 45000", "is buying a laptop recommended for me", "can i buy ps for 5rs"
        ],
        "Financial Health": [
            "what is my financial health score", "how healthy are my finances", "is my financial score good or bad",
            "give me my financial health assessment", "what is my risk level", "how can I improve my health score",
            "evaluate my overall financial condition", "show my financial stability rating", "health report"
        ],
        "Forecast": [
            "predict my savings for the next 6 months", "how much money will I have in 1 year", "3 month savings forecast",
            "project my future savings", "forecast my financial growth for 12 months", "how much will I save by next year",
            "show future wealth trajectory", "savings forecast breakdown"
        ],
        "General Question": [
            "what can you do for me", "explain how finpilot works", "what features do you offer",
            "how do your multi agent models work", "who built finpilot", "help me understand my options",
            "what AI models are you using", "guide me through the dashboard"
        ],
        "Unknown": [
            "who won the basketball game last night", "what is the recipe for chocolate cake",
            "tell me a joke", "what is the capital of France", "python code for bubble sort",
            "random noise text blablabla", "xyz 123 test sample", "weather forecast in Tokyo"
        ]
    }
    
    data = []
    prefixes = ["", "can you please ", "hey ", "finpilot ", "please ", "i want to know ", "tell me "]
    suffixes = ["", " please", " right now", " for this month", " thanks", " assistant", "?"]

    for intent, phrases in intent_templates.items():
        for phrase in phrases:
            data.append({"text": phrase, "intent": intent})
            for _ in range(15):
                p = random.choice(prefixes)
                s = random.choice(suffixes)
                text_aug = f"{p}{phrase}{s}".strip().lower()
                data.append({"text": text_aug, "intent": intent})

    df = pd.DataFrame(data).drop_duplicates(subset=["text"])
    print(f"Generated {len(df)} NLP Intent samples.")
    return df


def generate_health_dataset(n_samples=1500):
    print("Generating Financial Health Dataset (Rupees Scale)...")
    np.random.seed(42)
    
    income = np.random.uniform(25000, 500000, n_samples)
    expense_ratio = np.random.uniform(0.25, 1.2, n_samples)
    monthly_expenses = income * expense_ratio
    savings = np.random.uniform(10000, 2500000, n_samples)
    tx_count = np.random.randint(10, 120, n_samples)
    cat_variance = np.random.uniform(0.05, 0.45, n_samples)
    
    savings_months = savings / (monthly_expenses + 1e-5)
    
    score = (
        (1 - np.clip(expense_ratio, 0.25, 1.2)) * 40 +
        np.clip(savings_months / 6.0, 0, 1) * 35 +
        (1 - cat_variance) * 15 +
        np.clip(income / 300000, 0, 1) * 10
    )
    
    score = score + np.random.normal(0, 2, n_samples)
    score = np.clip(score, 10, 100)
    
    tiers = []
    for s in score:
        if s >= 80:
            tiers.append("Excellent")
        elif s >= 65:
            tiers.append("Good")
        elif s >= 50:
            tiers.append("Fair")
        else:
            tiers.append("Poor")

    df = pd.DataFrame({
        "income": income,
        "monthly_expenses": monthly_expenses,
        "savings": savings,
        "expense_ratio": expense_ratio,
        "tx_count": tx_count,
        "cat_variance": cat_variance,
        "health_score": score,
        "health_tier": tiers
    })
    return df


def generate_purchase_dataset(n_samples=2000):
    print("Generating Purchase Decision Dataset (Rupees Scale)...")
    np.random.seed(101)
    
    income = np.random.uniform(30000, 400000, n_samples)
    expenses = income * np.random.uniform(0.25, 0.95, n_samples)
    savings = np.random.uniform(5000, 1500000, n_samples)
    health_score = np.random.uniform(20, 98, n_samples)
    
    # Mix of cheap items (e.g. 5 to 500 Rs) and expensive items (5,000 to 500,000 Rs)
    item_price = np.concatenate([
        np.random.uniform(1, 500, n_samples // 4),
        np.random.uniform(500, 15000, n_samples // 4),
        np.random.uniform(15000, 100000, n_samples // 4),
        np.random.uniform(100000, 600000, n_samples // 4)
    ])
    np.random.shuffle(item_price)
    
    monthly_surplus = income - expenses
    price_to_savings = item_price / (savings + 1e-5)
    price_to_surplus = item_price / (monthly_surplus + 1e-5)
    
    # Target Class:
    # 0: Safe to Buy
    # 1: Moderate Caution
    # 2: Risky
    # 3: Unaffordable / Reject
    targets = []
    for i in range(n_samples):
        ps = price_to_savings[i]
        pr = price_to_surplus[i]
        hs = health_score[i]
        surplus = monthly_surplus[i]
        price = item_price[i]
        sav = savings[i]
        
        if price > sav or (surplus <= 0 and price > sav * 0.1):
            targets.append(3) # Unaffordable
        # Small / Trivial items relative to savings (e.g. price < 2% of savings or < 10% of monthly surplus)
        elif ps <= 0.05 or price <= 1000 or (ps <= 0.15 and pr <= 1.0):
            targets.append(0) # 100% Safe to buy!
        elif ps <= 0.25 and pr <= 2.5 and hs >= 40:
            targets.append(1) # Moderate Caution
        elif ps <= 0.50 and pr <= 4.0:
            targets.append(2) # Risky
        else:
            targets.append(3) # Unaffordable

    df = pd.DataFrame({
        "income": income,
        "monthly_expenses": expenses,
        "savings": savings,
        "health_score": health_score,
        "item_price": item_price,
        "monthly_surplus": monthly_surplus,
        "price_to_savings": price_to_savings,
        "price_to_surplus": price_to_surplus,
        "decision": targets
    })
    return df


def generate_savings_forecast_dataset(n_samples=1500):
    print("Generating Savings Forecast Dataset (Rupees Scale)...")
    np.random.seed(202)
    
    income = np.random.uniform(30000, 400000, n_samples)
    expense_ratio = np.random.uniform(0.3, 0.95, n_samples)
    monthly_expenses = income * expense_ratio
    current_savings = np.random.uniform(20000, 2000000, n_samples)
    monthly_surplus = income - monthly_expenses
    spending_volatility = np.random.uniform(0.02, 0.25, n_samples)
    
    savings_3m = current_savings + (monthly_surplus * 3) * (1 - spending_volatility * 0.5)
    savings_6m = current_savings + (monthly_surplus * 6) * (1 - spending_volatility * 0.8)
    savings_12m = current_savings + (monthly_surplus * 12) * (1 - spending_volatility * 1.0)
    
    savings_3m += np.random.normal(0, 1000, n_samples)
    savings_6m += np.random.normal(0, 2500, n_samples)
    savings_12m += np.random.normal(0, 5000, n_samples)
    
    df = pd.DataFrame({
        "income": income,
        "monthly_expenses": monthly_expenses,
        "current_savings": current_savings,
        "monthly_surplus": monthly_surplus,
        "spending_volatility": spending_volatility,
        "forecast_3m": np.clip(savings_3m, 0, None),
        "forecast_6m": np.clip(savings_6m, 0, None),
        "forecast_12m": np.clip(savings_12m, 0, None)
    })
    return df

if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    df_intent = generate_intent_dataset()
    df_intent.to_csv(os.path.join(DATA_DIR, "intent_dataset.csv"), index=False)
    
    df_health = generate_health_dataset()
    df_health.to_csv(os.path.join(DATA_DIR, "health_dataset.csv"), index=False)
    
    df_purchase = generate_purchase_dataset()
    df_purchase.to_csv(os.path.join(DATA_DIR, "purchase_dataset.csv"), index=False)
    
    df_forecast = generate_savings_forecast_dataset()
    df_forecast.to_csv(os.path.join(DATA_DIR, "forecast_dataset.csv"), index=False)
    
    print("All datasets generated and saved successfully!")
