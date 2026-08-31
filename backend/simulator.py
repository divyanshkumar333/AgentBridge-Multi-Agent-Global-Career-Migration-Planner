import os
import json
import time
from typing import List
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool
from google.genai import types

import database
from agents import resolve_country_code

# ==========================================
# 1. Pydantic Output Schemas
# ==========================================

class ScenarioComparisonItem(BaseModel):
    country_code: str = Field(description="Two-letter country code (IN, JP, DE, CA, AU, NL).")
    country_name: str = Field(description="Full name of the country.")
    migration_cost_1yr_usd: float = Field(description="Estimated total cost for year 1 (tuition + 12 * living, or domestic benchmarks).")
    time_to_employment_months: int = Field(description="Expected time to secure target role post-graduation (in months).")
    employability_score: int = Field(description="Employability score from 1 to 10 for this candidate in this country.")
    visa_complexity: str = Field(description="Visa complexity rating: Low, Medium, or High.")
    risk_level: str = Field(description="Geopolitical/economic/housing risk level: Low, Medium, or High.")
    expected_salary_usd: float = Field(description="Expected entry-level starting salary for target role in USD.")
    analysis_summary: str = Field(description="Brief summary of the pros/cons for this country scenario.")

class SimulatorResult(BaseModel):
    scenarios: List[ScenarioComparisonItem] = Field(description="List of country scenario comparisons.")


# ==========================================
# 2. Simulator Agent Tools (Database Grounding)
# ==========================================

def get_simulator_countries_db() -> str:
    """
    Fetches details for the six simulator countries: India, Japan, Germany, Canada, Australia, Netherlands.
    """
    try:
        codes = ["IN", "JP", "DE", "CA", "AU", "NL"]
        results = []
        for code in codes:
            country = database.get_country(code)
            if country:
                results.append(country)
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error retrieving countries: {str(e)}"

get_simulator_countries_tool = FunctionTool(func=get_simulator_countries_db)


# ==========================================
# 3. Simulator Agent Definition
# ==========================================

MODEL_NAME = "gemini-2.5-flash"

simulator_agent = Agent(
    name="simulator_agent",
    instruction=(
        "You are an AI migration risk advisor and scenario modeling expert.\n"
        "Your task is to simulate the career and migration outcomes for a candidate across six countries:\n"
        "India (IN), Japan (JP), Germany (DE), Canada (CA), Australia (AU), and Netherlands (NL).\n\n"
        "1. Retrieve country database facts using the `get_simulator_countries_db` tool.\n"
        "2. Assess the candidate's profile (target role, skills, budget, language capacity) against each country's job market.\n"
        "3. Estimate realistic Starting Salary, 1-Year Migration Cost, and Time to Employment (months) for the target role.\n"
        "4. Rate Employability (1-10), Visa Complexity (Low/Medium/High), and Risk Level (Low/Medium/High) for each option.\n"
        "Make sure to adjust expectations dynamically: e.g., domestic market (India) has lower costs and salary; Japan has N3+ language requirements.\n"
        "Ensure your output strictly conforms to the SimulatorResult schema."
    ),
    model=MODEL_NAME,
    tools=[get_simulator_countries_tool],
    output_schema=SimulatorResult
)


# ==========================================
# 4. Simulation Run Helper
# ==========================================

def get_simulator_fallback(profile_data: dict, goals: str, budget: float = None, experience_level: str = None, require_scholarship: bool = False) -> dict:
    """
    Returns a calculated fallback simulation dataset if the LLM API fails or rate limits.
    """
    target_role = profile_data.get("target_role", "Software Engineer")
    base_salary = 105000.0
    try:
        careers = database.get_careers()
        for c in careers:
            if c['title'].lower() in target_role.lower() or target_role.lower() in c['title'].lower():
                base_salary = c['avg_salary_usd']
                break
    except Exception:
        pass

    salary_factors = {
        "US": 1.0, "CA": 0.75, "DE": 0.65, "UK": 0.65, "AU": 0.80, "NL": 0.70, "JP": 0.50, "IN": 0.15
    }

    scenarios = []
    codes = ["IN", "JP", "DE", "CA", "AU", "NL"]
    
    for code in codes:
        try:
            db_country = database.get_country(code)
            if db_country:
                name = db_country.get("name")
                tuition = db_country.get("avg_tuition_annual_usd", 15000.0)
                living = db_country.get("avg_living_monthly_usd", 1200.0)
                total_1yr = tuition + 12 * living
                salary = base_salary * salary_factors.get(code, 0.7)
                
                emp_score = 7
                visa_comp = "Medium"
                risk_lvl = "Medium"
                summary = f"Stable career outlook in {name} with competitive starting salaries."
                
                if code == "DE":
                    emp_score = 8
                    visa_comp = "High"
                    risk_lvl = "Medium"
                    summary = "Strong tech sector, low tuition fees, but requires local language integration."
                elif code == "CA":
                    emp_score = 8
                    visa_comp = "Medium"
                    risk_lvl = "Low"
                    summary = "Highly structured post-study work permit, but faces high housing costs."
                elif code == "IN":
                    emp_score = 9
                    visa_comp = "Low"
                    risk_lvl = "Low"
                    summary = "Domestic market requires zero visa processing and low cost of living, though salaries are lower."
                elif code == "JP":
                    emp_score = 6
                    visa_comp = "Medium"
                    risk_lvl = "Medium"
                    summary = "High demand for IT, but requires conversational language capability."
                elif code == "NL":
                    emp_score = 7
                    visa_comp = "Medium"
                    risk_lvl = "Medium"
                    summary = "Strong international job hub, high english proficiency, but competitive housing market."
                elif code == "AU":
                    emp_score = 7
                    visa_comp = "High"
                    risk_lvl = "Medium"
                    summary = "Excellent quality of life, high wage standards, but visa processing is strict."
                
                scenarios.append({
                    "country_code": code,
                    "country_name": name,
                    "migration_cost_1yr_usd": total_1yr,
                    "time_to_employment_months": 6 if code == "IN" else 12,
                    "employability_score": emp_score,
                    "visa_complexity": visa_comp,
                    "risk_level": risk_lvl,
                    "expected_salary_usd": salary,
                    "analysis_summary": summary
                })
        except Exception:
            scenarios.append({
                "country_code": code,
                "country_name": code,
                "migration_cost_1yr_usd": 20000.0,
                "time_to_employment_months": 12,
                "employability_score": 7,
                "visa_complexity": "Medium",
                "risk_level": "Medium",
                "expected_salary_usd": 50000.0,
                "analysis_summary": f"Fallback scenario projection for {code}."
            })
            
    return {"scenarios": scenarios}

def run_simulation(profile_data: dict, goals: str, budget: float = None, experience_level: str = None, require_scholarship: bool = False) -> dict:
    """
    Runs the scenario simulator agent for the six countries.
    """
    session_service = InMemorySessionService()
    
    # Cascade model list to bypass rate limits
    models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    last_error = None
    
    message_text = (
        f"Candidate Target Role: {profile_data.get('target_role')}\n"
        f"Identified Skills: {', '.join(profile_data.get('skills_identified', []))}\n"
        f"Degree Level: {profile_data.get('degree_level')}\n"
        f"Employability Index: {profile_data.get('employability_index')}/10\n"
        f"Goals & Budgets: {goals}\n"
    )
    if budget is not None:
        message_text += f"Available Budget: ${budget} USD\n"
    if experience_level:
        message_text += f"Experience Level: {experience_level}\n"
    if require_scholarship:
        message_text += f"Requires Scholarship: Yes\n"
    
    sim_result = None
    for model in models_to_try:
        simulator_agent.model = model
        max_attempts = 2
        base_delay = 3.0
        
        for attempt in range(max_attempts):
            try:
                runner = Runner(agent=simulator_agent, session_service=session_service, app_name="agentbridge", auto_create_session=True)
                generator = runner.run(
                    user_id="pipeline_user",
                    session_id="simulator_session",
                    new_message=types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=message_text)]
                    )
                )
                response_text = ""
                for event in generator:
                    if hasattr(event, "error_code") and event.error_code:
                        err_msg = str(event.error_message)
                        if "RESOURCE_EXHAUSTED" in err_msg or "503" in err_msg or "quota" in err_msg.lower():
                            raise RuntimeError(f"FallbackTrigger: {err_msg}")
                        raise RuntimeError(f"Agent yielded error: {event.error_code} - {err_msg}")
                    if event.content and event.content.parts:
                        response_text = event.content.parts[0].text
                if not response_text:
                    raise RuntimeError("Agent returned empty response")
                sim_result = json.loads(response_text)
                break
            except Exception as e:
                last_error = e
                err_msg = str(e).lower()
                if "resource_exhausted" in err_msg or "429" in err_msg or "quota" in err_msg or "503" in err_msg or "unavailable" in err_msg or "fallbacktrigger" in err_msg:
                    print(f"[simulator_agent] Model {model} hit rate limit. Sleeping 8s before switching...")
                    time.sleep(8)
                    break
                
                if attempt == max_attempts - 1:
                    break
                    
                delay = base_delay * (2 ** attempt)
                print(f"[simulator_agent] Attempt {attempt + 1} with model {model} failed: {str(e)}. Retrying in {delay}s...")
                time.sleep(delay)
        if sim_result:
            break
                
    if not sim_result:
        print(f"Scenario simulator agent failed: {str(last_error)}. Using fallback computation.")
        sim_result = get_simulator_fallback(profile_data, goals, budget, experience_level, require_scholarship)

    # Apply data normalization layer on simulation result
    visa_complexity_map = {
        "US": "High", "CA": "Medium", "DE": "Medium", "UK": "High", "AU": "High", "NL": "Medium", "JP": "Medium", "IN": "Low"
    }
    risk_level_map = {
        "US": "Medium", "CA": "Low", "DE": "Low", "UK": "Medium", "AU": "Low", "NL": "Low", "JP": "Low", "IN": "Medium"
    }
    salary_factors = {
        "US": 1.0, "CA": 0.75, "DE": 0.65, "UK": 0.65, "AU": 0.80, "NL": 0.70, "JP": 0.50, "IN": 0.15
    }

    target_role = profile_data.get("target_role", "Software Engineer")
    base_salary = 105000.0
    try:
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM careers")
        careers = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        for c in careers:
            title_lower = c['title'].lower()
            role_lower = target_role.lower()
            if title_lower in role_lower or role_lower in title_lower:
                base_salary = c['avg_salary_usd']
                break
    except Exception as e:
        print(f"Error resolving simulation base salary: {str(e)}")

    normalized_scenarios = []
    for item in sim_result.get("scenarios", []):
        code = resolve_country_code(item.get("country_code", ""))
        item["country_code"] = code
        try:
            db_country = database.get_country(code)
            if db_country:
                item["country_name"] = db_country.get("name", item.get("country_name"))
                tuition = db_country.get("avg_tuition_annual_usd", 15000.0)
                living = db_country.get("avg_living_monthly_usd", 1200.0)
                total_1yr = tuition + 12 * living
                salary = base_salary * salary_factors.get(code, 0.7)
                
                item["migration_cost_1yr_usd"] = total_1yr
                item["expected_salary_usd"] = salary
                item["visa_complexity"] = visa_complexity_map.get(code, item.get("visa_complexity", "Medium"))
                item["risk_level"] = risk_level_map.get(code, item.get("risk_level", "Medium"))
                
                # Check employability score constraints
                if code == "DE":
                    item["employability_score"] = 8
                elif code == "CA":
                    item["employability_score"] = 8
                elif code == "IN":
                    item["employability_score"] = 9
                elif code == "JP":
                    item["employability_score"] = 6
                elif code == "NL":
                    item["employability_score"] = 7
                elif code == "AU":
                    item["employability_score"] = 7
        except Exception as e:
            print(f"Error normalizing simulation country {code}: {str(e)}")
        normalized_scenarios.append(item)
    sim_result["scenarios"] = normalized_scenarios

    return sim_result
