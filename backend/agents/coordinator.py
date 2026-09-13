import time
import json
from backend.database.db import get_db_connection
from backend.agents.intent_agent import IntentAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.health_agent import HealthAgent
from backend.agents.budget_agent import BudgetAgent
from backend.agents.purchase_agent import PurchaseAgent
from backend.agents.forecast_agent import ForecastAgent
from backend.agents.recommendation_agent import RecommendationAgent
from backend.agents.validation_agent import ValidationAgent

class CoordinatorAgent:
    def __init__(self):
        self.intent_agent = IntentAgent()
        self.analysis_agent = AnalysisAgent()
        self.health_agent = HealthAgent()
        self.budget_agent = BudgetAgent()
        self.purchase_agent = PurchaseAgent()
        self.forecast_agent = ForecastAgent()
        self.validation_agent = ValidationAgent()
        self.recommendation_agent = RecommendationAgent()

    def process_request(self, query, user_id=1):
        """Run the workflow and persist its complete execution telemetry once."""
        try:
            result = self._process_request(query, user_id=user_id)
        except Exception as exc:
            try:
                self._record_agent_log(
                    user_id=user_id,
                    query=query,
                    detected_intent="Unknown",
                    response="",
                    agent_steps=[{
                        "agent": "Coordinator Workflow",
                        "status": "Error",
                        "order": 1,
                        "details": str(exc)
                    }]
                )
            except Exception as log_error:
                print(f"[Coordinator Error Log Failure] {log_error}")
            raise

        try:
            self._record_agent_log(
                user_id=user_id,
                query=query,
                detected_intent=result["intent"],
                response=result["response"],
                agent_steps=[
                    {**step, "order": index}
                    for index, step in enumerate(result["pipeline_steps"], start=1)
                ]
            )
        except Exception as log_error:
            print(f"[Coordinator Log Failure] {log_error}")
        return result

    def _record_agent_log(self, user_id, query, detected_intent, response, agent_steps):
        """Store one complete workflow record using the existing agent_logs table."""
        conn = get_db_connection()
        try:
            conn.execute("""
                INSERT INTO agent_logs
                    (user_id, query, detected_intent, agent_steps, response)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                query,
                detected_intent,
                json.dumps(agent_steps, ensure_ascii=False),
                response
            ))
            conn.commit()
        finally:
            conn.close()

    def _process_request(self, query, user_id=1):
        start_time = time.time()
        pipeline_steps = []

        # 1. Intent Detection Agent
        t0 = time.time()
        intent_res = self.intent_agent.analyze_intent(query)
        t_intent = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Intent Detection Agent",
            "status": "Completed",
            "latency_ms": t_intent,
            "details": f"Detected Intent: {intent_res['intent']} (Confidence: {intent_res['confidence']*100:.1f}%)"
        })

        # 2. Financial Analysis Agent
        t0 = time.time()
        analysis_res = self.analysis_agent.run_analysis(user_id=user_id)
        t_analysis = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Financial Analysis Agent",
            "status": "Completed",
            "latency_ms": t_analysis,
            "details": f"Monthly Income: ₹{analysis_res.get('monthly_income',0):,.2f}, Expenses: ₹{analysis_res.get('monthly_expenses',0):,.2f}"
        })

        # 3. Financial Health Prediction Agent
        t0 = time.time()
        health_res = self.health_agent.evaluate_health(analysis_res)
        t_health = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Financial Health Prediction Agent",
            "status": "Completed",
            "latency_ms": t_health,
            "details": f"Health Score: {health_res['health_score']}/100 ({health_res['health_tier']})"
        })

        # 4. Budget Optimisation Agent
        t0 = time.time()
        budget_res = self.budget_agent.optimize_budget(analysis_res, health_res)
        t_budget = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Budget Optimisation Agent",
            "status": "Completed",
            "latency_ms": t_budget,
            "details": f"Optimized Strategy: {budget_res['strategy']}, Savings Target: ₹{budget_res['target_allocation']['savings_target']:,.2f}"
        })

        # 5. Purchase Decision Agent
        t0 = time.time()
        purchase_res = self.purchase_agent.evaluate_purchase(query, analysis_res, health_res, {})
        t_purchase = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Purchase Decision Agent",
            "status": "Completed",
            "latency_ms": t_purchase,
            "details": f"Evaluated Item: {purchase_res['item']} (₹{purchase_res['price']:,.2f}) -> {purchase_res['recommendation']}"
        })

        # 6. Savings Forecast Agent
        t0 = time.time()
        forecast_res = self.forecast_agent.forecast_savings(analysis_res)
        t_forecast = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Savings Forecast Agent",
            "status": "Completed",
            "latency_ms": t_forecast,
            "details": f"3M: ₹{forecast_res['forecast_3_months']:,.2f}, 6M: ₹{forecast_res['forecast_6_months']:,.2f}, 12M: ₹{forecast_res['forecast_12_months']:,.2f}"
        })

        # 7. Prediction Validation Agent (self-correcting AI layer)
        t0 = time.time()
        validation_res = self.validation_agent.validate(
            analysis_res=analysis_res,
            health_res=health_res,
            forecast_res=forecast_res,
            purchase_res=purchase_res,
            query=query,
            intent=intent_res["intent"]
        )
        t_validation = round((time.time() - t0) * 1000, 2)
        corrections_count = len(validation_res["corrections_applied"])
        pipeline_steps.append({
            "agent": "Prediction Validation Agent",
            "status": "Completed",
            "latency_ms": t_validation,
            "details": (
                f"Self-Corrected: {validation_res['is_self_corrected']} — "
                f"{corrections_count} rule(s) triggered. "
                + (f"Rules: {', '.join(c['rule'] for c in validation_res['corrections_applied'])}"
                   if corrections_count else "All predictions valid.")
            )
        })

        # Use corrected values downstream (validated data replaces raw model output)
        effective_forecast = validation_res["corrected_forecast"]
        effective_health   = validation_res["corrected_health"]

        # 8. Recommendation Generator Agent
        t0 = time.time()
        final_response = self.recommendation_agent.generate_response(
            intent_res, analysis_res, effective_health, budget_res,
            purchase_res, effective_forecast,
            query=query,
            validation_res=validation_res
        )
        t_rec = round((time.time() - t0) * 1000, 2)
        pipeline_steps.append({
            "agent": "Recommendation Generator Agent",
            "status": "Completed",
            "latency_ms": t_rec,
            "details": "Synthesized multi-agent telemetry into natural response."
        })

        total_latency = round((time.time() - start_time) * 1000, 2)

        # DEBUG LOGGING (Requirement 4)
        print(f"\n==================================================")
        print(f"   [Coordinator Pipeline Complete in {total_latency}ms]")
        print(f"   Query: '{query}' | Intent: {intent_res['intent']}")
        print(f"   Income: INR {analysis_res['monthly_income']:,.2f} | Expenses: INR {analysis_res['monthly_expenses']:,.2f}")
        print(f"   Health Score: {effective_health['health_score']}/100 ({effective_health['health_tier']})")
        print(f"   6-Month Forecast: INR {effective_forecast['forecast_6_months']:,.2f}")
        print(f"   Self-Corrected: {validation_res['is_self_corrected']}")
        print(f"==================================================\n")

        return {
            "query": query,
            "intent": intent_res["intent"],
            "intent_confidence": intent_res["confidence"],
            "response": final_response,
            "total_latency_ms": total_latency,
            "pipeline_steps": pipeline_steps,
            "data": {
                "analysis": analysis_res,
                "health": effective_health,
                "budget": budget_res,
                "purchase": purchase_res,
                "forecast": effective_forecast,
                "validation": validation_res
            }
        }
