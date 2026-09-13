import sys
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from backend.agents.coordinator import CoordinatorAgent

def test_pipeline():
    print("Testing Multi-Agent Coordinator Pipeline (Micro-purchase & Rupee Scaling)...")
    coordinator = CoordinatorAgent()

    test_queries = [
        "can i buy ps for 5rs?",
        "Can I buy a chocolate for 10 rupees?",
        "Can I buy a PS5 for 50000rs?",
        "Should I buy a MacBook Pro for 180000 rupees?",
        "Predict my 6 month savings balance",
        "Where is my money going?"
    ]

    for q in test_queries:
        print(f"\n[Query]: '{q}'")
        res = coordinator.process_request(q, user_id=1)
        print(f" -> Intent: {res['intent']} (Confidence: {res['intent_confidence']*100:.1f}%)")
        purchase_info = res["data"]["purchase"]
        print(f" -> Purchase Decision: {purchase_info['item']} (Rs {purchase_info['price']:,.2f}) => Code {purchase_info['decision_code']}: {purchase_info['recommendation']}")

    print("\n[SUCCESS] Pipeline verified!")

if __name__ == '__main__':
    test_pipeline()
