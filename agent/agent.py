```python  # noqa: C901
"""
Core agent.py for motto-fleet-burn-rate-tracker Maritime agent.
Executes daily fleet cost aggregation, burn rate analysis, and reporting.
"""

import os
import json
import logging
import pytz
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dotenv import load_dotenv

import requests
import pandas as pd
from supabase import create_client, Client
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema import BaseMessage

# Import fleet_reporter (assumed available in environment)
try:
    from fleet_reporter import report_action
except ImportError:
    def report_action(cost_usd: float):
        """Fallback fleet_reporter for missing import."""
        logging.info(f"Fleet reporter fallback: reported ${cost_usd:.2f}")

load_dotenv()

# Configure logging to /app/logs/
os.makedirs("/app/logs", exist_ok=True)
log_filename = f"/app/logs/motto-fleet-burn-rate-{datetime.now().strftime('%Y%m%d')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables with validation
MAX_COST_PER_RUN = float(os.getenv("MAX_COST_PER_RUN", "5.0"))
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
MOTTO_FINANCE_API_URL = os.getenv("MOTTO_FINANCE_API_URL", "https://motto-finance-tracker.onrender.com/api")
MOTTO_FINANCE_API_KEY = os.getenv("MOTTO_FINANCE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
AGENT_NOTIFICATION_EMAIL = os.getenv("AGENT_NOTIFICATION_EMAIL")

class MaritimeFleetAgent:
    """Core maritime fleet burn rate tracking agent."""
    
    def __init__(self):
        if not all([SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, MOTTO_FINANCE_API_KEY, OPENAI_API_KEY]):
            raise ValueError("Missing required environment variables")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY, model="gpt-4o-mini", temperature=0.1)
        self.cost_tracker = 0.0
        self.utc = pytz.UTC
        
    def _safe_api_call(self, cost_usd: float, func, *args, **kwargs) -> Any:
        """Execute API call with cost tracking and error handling."""
        try:
            if self.cost_tracker + cost_usd > MAX_COST_PER_RUN:
                raise RuntimeError(f"Cost limit exceeded: {self.cost_tracker + cost_usd:.2f} > {MAX_COST_PER_RUN}")
            
            report_action(cost_usd)
            self.cost_tracker += cost_usd
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"API call failed: {e}")
            self._send_alert(f"API Error in {func.__name__}: {e}")
            raise
    
    def _query_previous_day_costs(self) -> pd.DataFrame:
        """Query Supabase agent_runs for previous 24 hours costs."""
        yesterday = datetime.now(self.utc) - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        response = self.supabase.table("agent_runs").select("*").gte(
            "created_at", start_time.isoformat()
        ).lte("created_at", end_time.isoformat()).execute()
        
        if not response.data:
            logger.warning("No cost data found for previous day")
            return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        if 'cost_usd' not in df.columns:
            logger.error("cost_usd column missing in agent_runs data")
            return pd.DataFrame()
        
        return df
    
    def _aggregate_costs(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Aggregate costs by vessel, category, and calculate burn rates."""
        if df.empty:
            return {"total_daily_spend": 0, "vessels": {}, "burn_rate": 0, "anomalies": []}
        
        # Categorize expenses (assumed columns or infer from description)
        df['category'] = df.get('category', 'uncategorized')
        df['vessel'] = df.get('vessel_name', df.get('vessel_id', 'unknown'))
        
        aggregations = {}
        total_spend = df['cost_usd'].sum()
        
        # Per vessel breakdown
        vessel_summary = df.groupby('vessel')['cost_usd'].agg(['count', 'sum']).round(2)
        vessel_summary.columns = ['transactions', 'total_cost']
        
        # Category breakdown
        category_summary = df.groupby('category')['cost_usd'].sum().round(2)
        
        # Rolling 30-day average for anomaly detection
        anomalies = []
        for _, row in df.iterrows():
            if row['cost_usd'] > 1.2 * (df['cost_usd'].rolling(30, min_periods=1).mean().iloc[-1] or 0):
                anomalies.append({
                    "vessel": row['vessel'],
                    "cost": row['cost_usd'],
                    "category": row['category'],
                    "flag": "EXCEEDS_120_PERCENT_30DAY_AVG"
                })
        
        return {
            "total_daily_spend": float(total_spend),
            "vessel_metrics": vessel_summary.to_dict(),
            "category_breakdown": category_summary.to_dict(),
            "burn_rate": float(total_spend / max(len(vessel_summary), 1)),
            "anomalies": anomalies,
            "active_vessels": int(len(vessel_summary)),
            "total_transactions": int(len(df))
        }
    
    def _generate_analysis(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Use LLM to generate structured analysis."""
        prompt_template = PromptTemplate(
            input_variables=["summary"],
            template="""Analyze this maritime fleet burn rate data and provide insights:

{summary}

Respond with JSON containing:
{{
  "trend_analysis": "string analysis of burn rate trends",
  "top_cost_drivers": ["list", "of", "top", "drivers"],
  "recommendations": ["actionable", "recommendations"],
  "risk_level": "LOW|MEDIUM|HIGH"
}}"""
        )
        
        try:
            chain = prompt_template | self.llm
            response = chain.invoke({"summary": json.dumps(summary, indent=2)})
            analysis = json.loads(response.content)
            return analysis
        except Exception as e:
            logger.error(f"Analysis generation failed: {e}")
            return {
                "trend_analysis": "Analysis unavailable",
                "top_cost_drivers": [],
                "recommendations": [],
                "risk_level": "UNKNOWN"
            }
    
    def _push_to_motto_finance(self, payload: Dict[str, Any]) -> bool:
        """Push summary to motto-finance-tracker API."""
        headers = {
            "Authorization": f"Bearer {MOTTO_FINANCE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            f"{MOTTO_FINANCE_API_URL}/daily-burn-rate",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        return response.status_code in [200, 201]
    
    def _write_agent_run(self, summary: Dict[str, Any], success: bool) -> bool:
        """Record agent run in Supabase."""
        run_data = {
            "agent_name": "motto-fleet-burn-rate-tracker",
            "status": "success" if success else "failed",
            "total_cost_usd": self.cost_tracker,
            "payload": summary,
            "run_date": datetime.now(self.utc).isoformat(),
            "anomalies_detected": len(summary.get("anomalies", []))
        }
        
        result = self.supabase.table("agent_runs").insert(run_data).execute()
        return bool(result.data)
    
    def _send_alert(self, message: str) -> None:
        """Send alert email for anomalies or failures."""
        if not AGENT_NOTIFICATION_EMAIL:
            logger.warning("No notification email configured")
            return
        
        try:
            # Placeholder for email sending (implement with SMTP or service)
            logger.critical(f"ALERT: {message} - Notify: {AGENT_NOTIFICATION_EMAIL}")
        except Exception as e:
            logger.error(f"Alert email failed: {e}")
    
    def run_agent(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main entrypoint for agent execution.
        
        Args:
            payload: Optional override payload
            
        Returns:
            Dict containing execution results
        """
        start_time = datetime.now(self.utc)
        result = {"status": "failed", "error": None, "summary": {}}
        
        try:
            logger.info("Starting daily fleet burn rate analysis")
            
            # 1. Query previous day costs
            df = self._safe_api_call(0.5, self._query_previous_day_costs)
            
            # 2. Aggregate costs
            summary = self._safe_api_call(0.5, self._aggregate  # noqa: C901