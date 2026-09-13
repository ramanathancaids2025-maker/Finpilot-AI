import os
import sys
import joblib

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.database.db import DB_PATH, init_db
from backend.training.train_models import MODELS_DIR, train_all

def main():
    print("=" * 60)
    print("      LAUNCHING FINPILOT AI - AI PERSONAL FINANCE ASSISTANT")
    print("=" * 60)
    
    # 1. Initialize SQLite DB if not exists
    if not os.path.exists(DB_PATH):
        print("[Setup] Initializing SQLite database...")
        init_db()
    else:
        print(f"[Setup] SQLite Database verified at {DB_PATH}")

    # 2. Check all ML models, train if any artifact is missing
    required_models = [
        'intent_model.joblib',
        'health_model.joblib',
        'purchase_model.joblib',
        'forecast_model.joblib'
    ]
    invalid_models = []
    for name in required_models:
        model_path = os.path.join(MODELS_DIR, name)
        if not os.path.exists(model_path):
            invalid_models.append(name)
            continue
        try:
            joblib.load(model_path)
        except Exception as exc:
            print(f"[Setup] Could not load {name}: {exc}")
            invalid_models.append(name)

    if invalid_models:
        print(f"[Setup] Missing or invalid ML models: {', '.join(invalid_models)}")
        print("[Setup] Training all models locally...")
        train_all()
    else:
        print("[Setup] All 4 local machine learning models verified in backend/models/")

    # 3. Start Flask app
    from backend.app import app
    print("\n[Server] Starting FinPilot AI Web Dashboard on http://127.0.0.1:5000\n")
    app.run(host='127.0.0.1', port=5000, debug=True)

if __name__ == '__main__':
    main()
