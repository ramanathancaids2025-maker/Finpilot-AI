import os
import pandas as pd
import numpy as np
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error, r2_score

from backend.training.generate_dataset import (
    generate_intent_dataset,
    generate_health_dataset,
    generate_purchase_dataset,
    generate_savings_forecast_dataset
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

def train_intent_model():
    print("\n--- Training Model 1: NLP Intent Classifier (TF-IDF + Logistic Regression) ---")
    df = generate_intent_dataset()
    X = df['text']
    y = df['intent']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2), max_features=3000)),
        ('clf', LogisticRegression(C=5.0, max_iter=500, random_state=42))
    ])
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Intent Model Accuracy: {acc * 100:.2f}%")
    
    model_path = os.path.join(MODELS_DIR, 'intent_model.joblib')
    joblib.dump(pipeline, model_path)
    print(f"Saved Intent Model to {model_path}")
    return pipeline


def train_health_model():
    print("\n--- Training Model 2: Financial Health Predictor (Random Forest Regressor) ---")
    df = generate_health_dataset()
    
    features = ['income', 'monthly_expenses', 'savings', 'expense_ratio', 'tx_count', 'cat_variance']
    X = df[features]
    y = df['health_score']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"Health Model MAE: {mae:.2f}, R2 Score: {r2:.4f}")
    
    model_path = os.path.join(MODELS_DIR, 'health_model.joblib')
    joblib.dump({"model": model, "features": features}, model_path)
    print(f"Saved Health Model to {model_path}")
    return model


def train_purchase_model():
    print("\n--- Training Model 3: Purchase Decision AI (Random Forest Classifier) ---")
    df = generate_purchase_dataset()
    
    features = ['income', 'monthly_expenses', 'savings', 'health_score', 'item_price',
                'monthly_surplus', 'price_to_savings', 'price_to_surplus']
    X = df[features]
    y = df['decision']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    model = RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42)
    model.fit(X_train, y_train)
    
    preds = model.predict(X_test)
    acc = accuracy_score(y_test, preds)
    print(f"Purchase Decision Model Accuracy: {acc * 100:.2f}%")
    
    model_path = os.path.join(MODELS_DIR, 'purchase_model.joblib')
    joblib.dump({"model": model, "features": features}, model_path)
    print(f"Saved Purchase Model to {model_path}")
    return model


def train_forecast_model():
    print("\n--- Training Model 4: Savings Forecast (Gradient Boosting Regressor) ---")
    df = generate_savings_forecast_dataset()

    features = [
        'income', 'monthly_expenses', 'current_savings',
        'monthly_surplus', 'spending_volatility'
    ]
    targets = ['forecast_3m', 'forecast_6m', 'forecast_12m']
    X = df[features]
    y = df[targets]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    base_model = GradientBoostingRegressor(
        n_estimators=120, max_depth=3, learning_rate=0.05, random_state=42
    )
    model = MultiOutputRegressor(base_model)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)
    print(f"Forecast Model MAE: INR {mae:,.2f}")

    model_path = os.path.join(MODELS_DIR, 'forecast_model.joblib')
    joblib.dump({"model": model, "features": features, "targets": targets}, model_path)
    print(f"Saved Forecast Model to {model_path}")
    return model


def train_all():
    print("=" * 60)
    print("FINPILOT AI - LOCAL MACHINE LEARNING MODEL TRAINING")
    print("=" * 60)
    train_intent_model()
    train_health_model()
    train_purchase_model()
    train_forecast_model()
    print("\n[SUCCESS] All 4 AI models trained & saved successfully to backend/models/")

if __name__ == '__main__':
    train_all()
