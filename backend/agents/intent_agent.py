import os
import warnings
import joblib
import numpy as np

# Suppress unpickling version warnings for clean terminal logging
warnings.filterwarnings('ignore', category=UserWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'intent_model.joblib')

class IntentAgent:
    """
    NLP Intent Classification Agent.
    Uses trained TF-IDF Vectorizer + Logistic Regression pipeline to classify
    user queries into canonical intent categories with confidence estimation.
    Falls back gracefully to rule-based heuristics if the ML model is unreachable.
    """
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            if os.path.exists(MODEL_PATH):
                self.model = joblib.load(MODEL_PATH)
                print(f"[IntentAgent] Loaded trained ML Intent Model from {MODEL_PATH}")
            else:
                print(f"[IntentAgent WARNING] Model file not found at {MODEL_PATH}. Using rule-based fallback.")
        except Exception as e:
            print(f"[IntentAgent ERROR] Failed to load model from {MODEL_PATH}: {e}. Using rule-based fallback.")
            self.model = None

    def analyze_intent(self, text):
        if not text or not str(text).strip():
            return {
                "intent": "Unknown",
                "confidence": 0.0,
                "probabilities": {}
            }

        query = str(text).strip()

        # Primary Path: Scikit-learn Pipeline (TF-IDF + Logistic Regression)
        if self.model is not None:
            try:
                probs = self.model.predict_proba([query])[0]
                classes = self.model.classes_
                best_idx = int(np.argmax(probs))
                predicted_intent = str(classes[best_idx])
                confidence = float(probs[best_idx])

                prob_dict = {
                    str(classes[i]): round(float(probs[i]), 4)
                    for i in range(len(classes))
                }

                print(f"--- [IntentAgent ML Classification] ---")
                print(f"Query: '{query}' -> Intent: {predicted_intent} (Confidence: {confidence*100:.1f}%)")
                print(f"----------------------------------------\n")

                return {
                    "intent": predicted_intent,
                    "confidence": round(confidence, 4),
                    "probabilities": prob_dict
                }
            except Exception as e:
                print(f"[IntentAgent ML Prediction Error] {e}. Engaging rule-based fallback.")

        # Safe Fallback Path: Rule-based heuristic matching with canonical names
        q_lower = query.lower()
        if any(w in q_lower for w in ["buy", "afford", "can i get", "purchase", "check item", "price", "order", "cost of"]):
            intent = "Purchase Decision"
        elif any(w in q_lower for w in ["health", "score", "rating", "status", "financial health", "stability", "wellbeing"]):
            intent = "Financial Health"
        elif any(w in q_lower for w in ["forecast", "future", "project", "prediction", "growth", "next year", "in 6 months", "in 12 months"]):
            intent = "Forecast"
        elif any(w in q_lower for w in ["spend", "spending", "expense", "cut", "reduce", "dining out", "distribution"]):
            intent = "Spending Analysis"
        elif any(w in q_lower for w in ["savings balance", "how much savings", "emergency fund", "liquid savings", "savings rate"]):
            intent = "Savings"
        elif any(w in q_lower for w in ["budget", "50 30 20", "allocat", "category limit"]):
            intent = "Budget"
        elif any(w in q_lower for w in ["hello", "hi", "hey", "namaste", "good morning", "good evening"]):
            intent = "Greeting"
        else:
            intent = "General Question"

        return {
            "intent": intent,
            "confidence": 0.85,
            "probabilities": {intent: 0.85}
        }

