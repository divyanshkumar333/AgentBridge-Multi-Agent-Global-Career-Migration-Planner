import os
import re
import json
import time
import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv
from openai import OpenAI

# Configure logger
logger = logging.getLogger('agent_bridge')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('agent_bridge.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Load env vars
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from google.adk import Agent
from google.adk.tools import FunctionTool

import database

# ==========================================
# 1. Security Feature: PII Redaction Guard
# ==========================================
def redact_pii(text: str) -> str:
    """
    Redacts sensitive personal information (PII) like email, phone number,
    addresses, and name patterns to protect candidate privacy.
    """
    # Redact Emails
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    redacted = re.sub(email_pattern, '[REDACTED_EMAIL]', text)
    
    # Redact Phone Numbers (covers +1-xxx-xxx-xxxx, (xxx) xxx-xxxx, xxxxxxxxxx, etc.)
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    redacted = re.sub(phone_pattern, '[REDACTED_PHONE]', redacted)
    
    # Redact common social security / national ID patterns (xxx-xx-xxxx etc.)
    ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
    redacted = re.sub(ssn_pattern, '[REDACTED_ID]', redacted)
    
    # Redact explicit label markers
    redacted = re.sub(r'(?i)\b(?:name|fullname|full name)\s*:\s*[^\n]+', 'Name: [REDACTED_NAME]', redacted)
    redacted = re.sub(r'(?i)\b(?:address|location)\s*:\s*[^\n]+', 'Address: [REDACTED_LOCATION]', redacted)
    
    return redacted


def normalize_llm_json(raw_content: str) -> str:
    """
    Cleans and normalizes JSON responses from the LLM, handling markdown blocks,
    trailing commas, single quotes, and other minor formatting deviations.
    """
    if not raw_content:
        return ""
    content = raw_content.strip()
    content = re.sub(r"^```(?:json)?\s*", "", content, flags=re.IGNORECASE)
    content = re.sub(r"\s*```$", "", content)
    content = content.strip()
    
    # Try parsing first. If valid, return content
    try:
        json.loads(content)
        return content
    except json.JSONDecodeError:
        pass
        
    # Attempt parsing Python-like literal strings (single quotes)
    import ast
    try:
        parsed = ast.literal_eval(content)
        return json.dumps(parsed)
    except Exception:
        pass
        
    # Clean up trailing commas in objects and lists
    content = re.sub(r',\s*([\]}])', r'\1', content)
    return content


def parse_nested_json_strings(obj):
    """
    Recursively finds and parses nested JSON strings inside lists/dicts.
    """
    if isinstance(obj, str):
        stripped = obj.strip()
        if (stripped.startswith('[') and stripped.endswith(']')) or (stripped.startswith('{') and stripped.endswith('}')):
            try:
                parsed = json.loads(stripped)
                return parse_nested_json_strings(parsed)
            except Exception:
                pass
        return obj
    elif isinstance(obj, dict):
        return {k: parse_nested_json_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [parse_nested_json_strings(item) for item in obj]
    return obj


def resolve_country_code(code_str: str) -> str:
    if not code_str:
        return ""
    code_upper = code_str.upper().strip()
    if code_upper in ["US", "USA", "UNITED STATES"]:
        return "US"
    if code_upper in ["CA", "CAN", "CANADA"]:
        return "CA"
    if code_upper in ["DE", "GER", "GERMANY"]:
        return "DE"
    if code_upper in ["UK", "GB", "GBR", "UNITED KINGDOM", "ENGLAND"]:
        return "UK"
    if code_upper in ["AU", "AUS", "AUSTRALIA"]:
        return "AU"
    if code_upper in ["NL", "NLD", "NETHERLANDS", "HOLLAND"]:
        return "NL"
    if code_upper in ["IN", "IND", "INDIA"]:
        return "IN"
    if code_upper in ["JP", "JPN", "JAPAN"]:
        return "JP"
    
    # Try substring matches
    for code, name in [("US", "UNITED STATES"), ("CA", "CANADA"), ("DE", "GERMANY"), ("UK", "UNITED KINGDOM"), ("AU", "AUSTRALIA"), ("NL", "NETHERLANDS"), ("IN", "INDIA"), ("JP", "JAPAN")]:
        if code in code_upper or name in code_upper:
            return code
    return code_upper


# ==========================================
# 2. Pydantic Output Schemas
# ==========================================

class ProfileResult(BaseModel):
    summary: str = Field(description="A concise summary of the user's educational and professional profile.")
    skills_identified: List[str] = Field(description="Key skills extracted from the profile.")
    target_role: str = Field(description="Primary target career role or occupation suggested.")
    degree_level: str = Field(description="Current or target degree level (e.g., Bachelor's, Master's, PhD).")
    employability_index: int = Field(description="A score out of 10 indicating general international employability.")
    employability_index_100: int = Field(description="A score out of 100 indicating global employability rating.")
    skill_gaps: List[str] = Field(description="Key skills required for the target role that the user currently lacks.")
    strengths: List[str] = Field(description="Core academic or professional strengths.")
    recommended_certifications: List[str] = Field(description="Industry certifications (e.g. AWS, CISSP, PMP) recommended to bridge gaps.")
    recommended_projects: List[str] = Field(description="Specific hands-on projects recommended to build portfolio.")

class MatchedCountry(BaseModel):
    country_code: str = Field(description="Two-letter country code (JP, DE, CA, AU, NL).")
    country_name: str = Field(description="Full name of the country.")
    match_score: int = Field(description="A matching score from 1 to 100 based on compatibility.")
    match_reason: str = Field(description="Clear explanation of why this country is a good fit.")
    visa_route: str = Field(description="The primary study or post-study immigration visa route.")
    visa_process_summary: str = Field(description="Brief summary of the application steps.")
    post_study_work_months: int = Field(description="Duration of post-study work visa in months.")
    risk_analysis: str = Field(description="Specific country risk factors (e.g., housing, language, high costs).")
    visa_complexity: str = Field(description="Visa complexity rating: Low, Medium, or High.")
    language_barrier: str = Field(description="Language barrier level: Low, Medium, or High.")
    risk_level: str = Field(description="Overall risk level: Low, Medium, or High.")

class ExplorerResult(BaseModel):

    matched_countries: List[MatchedCountry] = Field(description="List of matching countries with visa and risk details.")
    
    @validator('matched_countries', pre=True)
    def parse_matched_countries(cls, v):
        if isinstance(v, str):
            import json, ast
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return ast.literal_eval(v)
        return v

class CostBreakdown(BaseModel):
    country_code: str = Field(description="Two-letter country code (US, CA, DE, UK, AU).")
    annual_tuition_usd: float = Field(description="Average annual tuition costs in USD.")
    annual_living_usd: float = Field(description="Average annual living costs in USD.")
    visa_app_fee_usd: float = Field(description="Average visa and application fees in USD.")
    health_insurance_usd: float = Field(description="Average health insurance cost in USD.")
    first_year_setup_usd: float = Field(description="Typical first-year setup costs in USD.")
    gross_first_year_cost_usd: float = Field(description="Estimated gross total cost for the first year (tuition + living + visa + health + setup).")
    expected_salary_usd: float = Field(description="Average starting salary for target role in USD.")
    financial_roi_score: int = Field(description="Financial Return on Investment score from 1 to 10.")

class MatchingScholarship(BaseModel):
    name: str = Field(description="Name of the scholarship.")
    sponsor: str = Field(description="Sponsor or donor.")
    award_amount_usd: float = Field(description="Estimated value of the scholarship in USD.")
    deadline: str = Field(description="Application deadline.")
    eligibility_summary: str = Field(description="Summary of criteria/eligibility.")
    application_link: str = Field(description="URL to details/application.")

class FundingResult(BaseModel):
    cost_analysis: List[CostBreakdown] = Field(default_factory=list, description="Financial analysis per matched country.")
    matching_scholarships: List[MatchingScholarship] = Field(default_factory=list, description="Relevant scholarships matches.")

    @validator('cost_analysis', 'matching_scholarships', pre=True)
    def parse_list(cls, v):
        if isinstance(v, str):
            import json, ast
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(v)
                except Exception:
                    pass
        return v


# ==========================================
# 3. Agent Tools (Database Grounding)
# ==========================================

def get_countries_db() -> str:
    """
    Fetches all available target countries along with cost benchmarks, visa details,
    post-study work permit durations, language barriers, and risk profiles.
    """
    try:
        countries = database.get_countries()
        return json.dumps(countries, indent=2)
    except Exception as e:
        return f"Error retrieving countries: {str(e)}"

def get_country_details_db(code: str) -> str:
    """
    Retrieves full details for a specific country by its two-letter code (e.g. US, CA, DE, UK, AU).
    """
    try:
        country = database.get_country(code)
        if country:
            return json.dumps(country, indent=2)
        return f"Country '{code}' not found in the database."
    except Exception as e:
        return f"Error retrieving country details: {str(e)}"

def get_scholarships_db(country_code: Optional[str] = None, degree_level: Optional[str] = None) -> str:
    """
    Queries the database for major international scholarships matching the given country code and degree level.
    """
    try:
        clean_level = None
        if degree_level:
            level_lower = degree_level.lower()
            if "master" in level_lower:
                clean_level = "Master"
            elif "phd" in level_lower or "doctor" in level_lower:
                clean_level = "PhD"
            elif "bachelor" in level_lower:
                clean_level = "Bachelor"
        scholarships = database.get_scholarships(country_code, clean_level)
        return json.dumps(scholarships, indent=2)
    except Exception as e:
        return f"Error retrieving scholarships: {str(e)}"

# Instantiate tools as FunctionTool objects
get_countries_tool = FunctionTool(func=get_countries_db)
get_country_details_tool = FunctionTool(func=get_country_details_db)
get_scholarships_tool = FunctionTool(func=get_scholarships_db)


# ==========================================
# 4. Agent Definitions
# ==========================================

# Model to use across agents
MODEL_NAME = "meta/llama-3.1-8b-instruct"

# Agent 1: Profiler
profiler_agent = Agent(
    name="profiler_agent",
    instruction=(
        "You are an expert academic and professional skills evaluator. "
        "Your task is to analyze the provided resume/profile text. "
        "1. Summarize their professional/academic background.\n"
        "2. Identify key skills and current degree level.\n"
        "3. Suggest a single high-demand target job title/role based on their profile.\n"
        "4. Highlight core skill gaps that they must fill to transition into this target role.\n"
        "5. Estimate their overall international employability index (1-10).\n"
        "Ensure your output strictly conforms to the ProfileResult schema."
    ),
    model=MODEL_NAME,
    output_schema=ProfileResult
)

# Agent 2: Explorer
explorer_agent = Agent(
    name="explorer_agent",
    instruction=(
        "You are an international migration strategist. "
        "Your job is to match and evaluate the candidate's profile against exactly five countries: Japan (JP), Germany (DE), Canada (CA), Australia (AU), and Netherlands (NL).\n"
        "1. Evaluate country options using the `get_countries_db` tool.\n"
        "2. For each of the five countries, evaluate the compatibility with the candidate's target role, language skills, and visa goals, and assign a match score (1-100).\n"
        "3. Extract and present the official study/work visa pathways, post-study work durations, and risk factors for each from the database.\n"
        "4. For each country, determine the visa complexity (Low, Medium, or High), language barrier level (Low, Medium, or High), and overall risk level (Low, Medium, or High) based on database details.\n"
        "5. Your output must contain exactly five items in `matched_countries`, representing JP, DE, CA, AU, and NL.\n"
        "Ground your answers in the database; do not invent visa requirements, language barriers, or housing risks.\n"
        "Ensure your output strictly conforms to the ExplorerResult schema."
    ),
    model=MODEL_NAME,
    tools=[get_countries_tool, get_country_details_tool],
    output_schema=ExplorerResult
)

# Agent 3: Funding
funding_agent = Agent(
    name="funding_agent",
    instruction=(
        "You are a financial analyst providing cost analysis and scholarship recommendations for the candidate. "
        "Use the `get_countries_db` tool to retrieve cost benchmarks for each matched country provided in the input. "
        "Use the `get_scholarships_db` tool to retrieve relevant scholarships for the target degree level and countries. "
        "Populate the `FundingResult` schema with a list of `CostBreakdown` for each country and a list of `MatchingScholarship`. "
        "Ensure your output strictly conforms to the FundingResult schema."
    ),
    model=MODEL_NAME,
    tools=[get_countries_tool, get_scholarships_tool],
    output_schema=FundingResult
)

# Agent 3: Funding


# ==========================================
# 5. Orchestration Pipeline Run Helper
# ==========================================

# Fallback Generators
def get_profile_fallback(resume_text: str, degree_level: str) -> dict:
    return {
        "summary": "Fallback profile summary for candidate (system default).",
        "skills_identified": ["AI", "Data Analysis", "Software Engineering"],
        "target_role": "AI Engineer",
        "degree_level": degree_level,
        "employability_index": 7,
        "employability_index_100": 70,
        "skill_gaps": ["Cloud Infrastructure", "System Design"],
        "strengths": ["Python Programming"],
        "recommended_certifications": ["Certified AI Engineer"],
        "recommended_projects": ["Data Visualization Dashboard"]
    }

def get_explorer_fallback() -> dict:
    return {
        "matched_countries": [
            {"country_code": "JP", "country_name": "Japan", "match_score": 60, "match_reason": "High demand for tech, but high language barrier.", "visa_route": "Student Visa", "visa_process_summary": "Apply to school, get COE, apply for visa.", "post_study_work_months": 12, "risk_analysis": "Language barrier.", "visa_complexity": "Medium", "language_barrier": "High", "risk_level": "Medium"},
            {"country_code": "DE", "country_name": "Germany", "match_score": 80, "match_reason": "Strong engineering market and affordable education.", "visa_route": "Student Visa", "visa_process_summary": "Apply to university, open blocked account, apply at embassy.", "post_study_work_months": 18, "risk_analysis": "Bureaucracy and language barrier.", "visa_complexity": "Medium", "language_barrier": "High", "risk_level": "Medium"},
            {"country_code": "CA", "country_name": "Canada", "match_score": 75, "match_reason": "Open post-graduation work opportunities.", "visa_route": "Study Permit", "visa_process_summary": "Get admission, pay tuition, apply for study permit online.", "post_study_work_months": 36, "risk_analysis": "Housing shortage and high cost of living.", "visa_complexity": "Medium", "language_barrier": "Low", "risk_level": "Medium"},
            {"country_code": "AU", "country_name": "Australia", "match_score": 70, "match_reason": "Good post-study work options.", "visa_route": "Student Visa (Subclass 500)", "visa_process_summary": "Get CoE, purchase health cover, apply online.", "post_study_work_months": 24, "risk_analysis": "High cost of living.", "visa_complexity": "Medium", "language_barrier": "Low", "risk_level": "Medium"},
            {"country_code": "NL", "country_name": "Netherlands", "match_score": 65, "match_reason": "English-friendly environment.", "visa_route": "Student Visa (MVV/VVR)", "visa_process_summary": "University applies on student's behalf.", "post_study_work_months": 12, "risk_analysis": "Severe student housing shortage.", "visa_complexity": "Low", "language_barrier": "Medium", "risk_level": "Medium"}
        ]
    }

def get_funding_fallback() -> dict:
    return {
        "cost_analysis": [
            {"country_code": "JP", "annual_tuition_usd": 8000, "annual_living_usd": 13200, "visa_app_fee_usd": 30, "health_insurance_usd": 400, "first_year_setup_usd": 1500, "gross_first_year_cost_usd": 23130, "expected_salary_usd": 40000, "financial_roi_score": 7},
            {"country_code": "DE", "annual_tuition_usd": 3000, "annual_living_usd": 13200, "visa_app_fee_usd": 80, "health_insurance_usd": 1400, "first_year_setup_usd": 1500, "gross_first_year_cost_usd": 19180, "expected_salary_usd": 55000, "financial_roi_score": 9},
            {"country_code": "CA", "annual_tuition_usd": 25000, "annual_living_usd": 18000, "visa_app_fee_usd": 150, "health_insurance_usd": 800, "first_year_setup_usd": 2500, "gross_first_year_cost_usd": 46450, "expected_salary_usd": 65000, "financial_roi_score": 7},
            {"country_code": "AU", "annual_tuition_usd": 30000, "annual_living_usd": 20000, "visa_app_fee_usd": 430, "health_insurance_usd": 1500, "first_year_setup_usd": 2500, "gross_first_year_cost_usd": 54430, "expected_salary_usd": 70000, "financial_roi_score": 6},
            {"country_code": "NL", "annual_tuition_usd": 18000, "annual_living_usd": 16800, "visa_app_fee_usd": 230, "health_insurance_usd": 1200, "first_year_setup_usd": 2000, "gross_first_year_cost_usd": 38230, "expected_salary_usd": 60000, "financial_roi_score": 7}
        ],
        "matching_scholarships": [
            {"name": "DAAD Scholarship", "sponsor": "German Government", "award_amount_usd": 15000, "deadline": "Varies (Aug - Nov)", "eligibility_summary": "Stipend of 934-1,200 EUR monthly, travel allowance, health insurance, and tuition waivers.", "application_link": "https://www.daad.de/"}
        ]
    }

async def run_agent_pipeline(resume_text: str, goals: str, degree_level: str) -> dict:
    """
    Executes the multi-agent orchestration pipeline sequentially using Nvidia NIM with detailed logging and 90‑second timeouts:
    1. Redact PII.
    2. Run Profiler Agent.
    3. Run Explorer Agent.
    4. Run Funding Agent.
    5. Return unified strategic analysis.
    """
    logger.info("Starting agent pipeline for degree level %s", degree_level)
    # 1. PII Redaction
    logger.info("PII Guard started")
    clean_resume = redact_pii(resume_text)
    clean_goals = redact_pii(goals)
    logger.info("PII Guard finished")
    logger.info("PII redaction completed")
    # Initialize Nvidia NIM OpenAI client with timeout and env check
    if not os.environ.get("NVIDIA_API_KEY"):
        logger.error("NVIDIA_API_KEY is missing from environment.")
        raise RuntimeError("Missing NVIDIA_API_KEY in .env")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY"),
        timeout=30.0
    )
    logger.info("NVIDIA client initialized with 30s timeout")

    # Helper to execute a single agent run via Nvidia NIM with JSON schema enforcement, tools handling, and timeout
    async def execute_agent(agent, message_text: str):
        logger.info("Executing agent %s", agent.name)
        schema_dict = agent.output_schema.model_json_schema()
        
        # Build tools if the agent has them
        tools_declarations = []
        tools_map = {}
        
        agent_tools = getattr(agent, "tools", [])
        if agent_tools:
            # Replicate the SetModelResponseTool declaration
            set_response_tool_desc = {
                "name": "set_model_response",
                "description": "Set your final response using the required output schema. Use this tool to provide your final structured answer instead of outputting text directly.",
                "parameters": schema_dict
            }
            tools_declarations.append({"type": "function", "function": set_response_tool_desc})
            
            for t in agent_tools:
                decl = t._get_declaration()
                func_decl = {
                    "name": decl.name,
                    "description": decl.description,
                    "parameters": json.loads(json.dumps(decl.parameters, default=lambda o: o.__dict__ if hasattr(o, '__dict__') else str(o))) if decl.parameters else {"type": "object", "properties": {}}
                }
                if "type" in func_decl["parameters"] and isinstance(func_decl["parameters"]["type"], str):
                    pass
                else:
                    func_decl["parameters"]["type"] = "object"
                
                tools_declarations.append({"type": "function", "function": func_decl})
                tools_map[t.name] = t
        
        system_prompt = (
            f"{agent.instruction}\n\n"
        )
        if not agent_tools:
            system_prompt += (
                f"You MUST output your response strictly as a JSON object conforming to this schema:\n"
                f"{json.dumps(schema_dict, indent=2)}\n\n"
                f"Do not include any explanation, markdown wrapping (such as ```json), or preamble. "
                f"Output only raw, valid JSON."
            )
        else:
            system_prompt += (
                f"IMPORTANT: You have access to other tools, but you must provide your final response "
                f"using the set_model_response tool with the required structured format. "
                f"After using any other tools needed to complete the task, always call set_model_response "
                f"with your final answer in the specified schema format."
            )

        async def call_api_with_retry(messages, turn_num, attempt_limit=3):
            last_err = None
            for attempt in range(attempt_limit):
                try:
                    kwargs = {
                        "model": agent.model,
                        "messages": messages,
                        "temperature": 0.2,
                        "top_p": 0.7,
                        "max_tokens": 2048
                    }
                    if tools_declarations:
                        kwargs["tools"] = tools_declarations
                    
                    logger.info("Sending request to NVIDIA API for agent %s (turn %d, request attempt %d)", agent.name, turn_num, attempt + 1)
                    completion = client.chat.completions.create(**kwargs)
                    return completion.choices[0].message
                except Exception as api_err:
                    last_err = api_err
                    err_str = str(api_err)
                    is_transient = False
                    if hasattr(api_err, "status_code"):
                        is_transient = api_err.status_code in [429, 500, 502, 503, 504]
                    elif "timeout" in err_str.lower() or "connection" in err_str.lower() or "504" in err_str or "503" in err_str:
                        is_transient = True
                    
                    if not is_transient:
                        logger.error("Non-transient error in API call for %s: %s", agent.name, err_str)
                        raise api_err
                        
                    logger.warning("Transient error in API call for %s (attempt %d/%d): %s. Retrying...", agent.name, attempt + 1, attempt_limit, err_str)
                    if attempt < attempt_limit - 1:
                        await asyncio.sleep(2 ** attempt)
            raise last_err

        async def call_agent():
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message_text}
            ]
            
            max_turns = 10
            for turn in range(1, max_turns + 1):
                message = await call_api_with_retry(messages, turn)
                
                # Check if model wants to call tools
                if message.tool_calls:
                    logger.info("Agent %s invoked tool calls: %s", agent.name, [tc.function.name for tc in message.tool_calls])
                    
                    messages.append({
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            } for tc in message.tool_calls
                        ]
                    })
                    
                    set_response_call = None
                    for tool_call in message.tool_calls:
                        tc_name = tool_call.function.name
                        if tc_name == "set_model_response":
                            set_response_call = tool_call
                            break
                    
                    if set_response_call:
                        tc_args_raw = set_response_call.function.arguments
                        logger.info("Agent %s submitted final response via set_model_response", agent.name)
                        try:
                            tc_args_clean = normalize_llm_json(tc_args_raw)
                            tc_args = json.loads(tc_args_clean)
                            tc_args = parse_nested_json_strings(tc_args)
                            
                            validated = agent.output_schema.model_validate(tc_args)
                            logger.info("%s validation completed", agent.name.capitalize())
                            return validated.model_dump_json()
                        except Exception as val_err:
                            logger.error("Schema validation failed for %s set_model_response: %s", agent.name, str(val_err))
                            error_feedback = {
                                "role": "tool",
                                "tool_call_id": set_response_call.id,
                                "name": "set_model_response",
                                "content": json.dumps({
                                    "error": "Schema validation failed",
                                    "details": str(val_err),
                                    "instruction": "Please correct your parameters to match the required output schema and call set_model_response again."
                                })
                            }
                            messages.append(error_feedback)
                            continue
                            
                    for tool_call in message.tool_calls:
                        tc_name = tool_call.function.name
                        if tc_name == "set_model_response":
                            continue
                        
                        try:
                            tc_args = json.loads(tool_call.function.arguments)
                        except Exception:
                            tc_args = {}
                            
                        if tc_name in tools_map:
                            tool_obj = tools_map[tc_name]
                            from google.adk.tools.tool_context import ToolContext
                            class DummyToolContext(ToolContext):
                                def __init__(self): pass
                                def request_confirmation(self, hint: str): pass
                            
                            try:
                                tool_res = await tool_obj.run_async(args=tc_args, tool_context=DummyToolContext())
                                tool_content = json.dumps(tool_res)
                            except Exception as tool_err:
                                tool_content = json.dumps({"error": f"Tool execution failed: {str(tool_err)}"})
                                
                            logger.info("Tool %s returned result", tc_name)
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tc_name,
                                "content": tool_content
                            })
                        else:
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tc_name,
                                "content": f"Error: Tool {tc_name} not found."
                            })
                    continue
                
                raw_content = message.content or ""
                if not raw_content.strip():
                    logger.warning("Agent %s returned an empty response body on turn %d.", agent.name, turn)
                    if turn == max_turns:
                        raise ValueError("Empty response from NVIDIA NIM/OpenAI API")
                    continue
                    
                clean_content = normalize_llm_json(raw_content)
                try:
                    parsed_content = json.loads(clean_content)
                    parsed_content = parse_nested_json_strings(parsed_content)
                    validated = agent.output_schema.model_validate(parsed_content)
                    logger.info("Agent %s succeeded on turn %d (validated direct response)", agent.name, turn)
                    return validated.model_dump_json()
                except Exception as val_err:
                    logger.error("Direct response validation failed for %s on turn %d: %s", agent.name, turn, str(val_err))
                    if turn == max_turns:
                        raise ValueError(f"Failed to get valid JSON from agent {agent.name} after {max_turns} turns: {str(val_err)}")
                    
                    messages.append({
                        "role": "user",
                        "content": f"Your response did not match the required schema: {str(val_err)}. Please respond with raw, valid JSON matching the schema."
                    })
            
            raise ValueError(f"Agent {agent.name} reached maximum turns ({max_turns}) without producing a valid final response.")

        # Apply 90‑second timeout for the entire sequence of turns
        try:
            return await asyncio.wait_for(call_agent(), timeout=90.0)
        except asyncio.TimeoutError:
            logger.error("Agent %s timed out after 90 seconds overall execution", agent.name)
            raise

    # 2. Run Profiler Agent
    logger.info("Profiler started")
    profiler_input = f"Candidate Profile:\n{clean_resume}\n\nCareer Goals:\n{clean_goals}\nTarget Degree: {degree_level}"
    logger.info("====================================")
    logger.info("Pipeline Step 1: Profiler Agent Input: %s", profiler_input)
    t_start = time.time()
    try:
        profiler_raw = await execute_agent(profiler_agent, profiler_input)
        t_end = time.time()
        logger.info("Pipeline Step 1: Profiler Agent Raw Output (Time: %.2fs)", t_end - t_start)
        if not profiler_raw or not profiler_raw.strip():
            raise ValueError("Profiler agent returned empty raw response")
        profile_data = json.loads(profiler_raw)
        logger.info("Profiler agent completed and parsed successfully")
    except Exception as e:
        logger.error("Pipeline Step 1 (Profiler Agent) Failed: %s. Proceeding with fallback.", str(e))
        profile_data = get_profile_fallback(resume_text, degree_level)

    # 3. Run Explorer Agent
    logger.info("Explorer started")
    logger.info("====================================")
    logger.info("Pipeline Step 2: Explorer Agent Input: %s", json.dumps(profile_data))
    t_start = time.time()
    try:
        explorer_raw = await execute_agent(explorer_agent, json.dumps(profile_data))
        t_end = time.time()
        logger.info("Pipeline Step 2: Explorer Agent Raw Output (Time: %.2fs)", t_end - t_start)
        if not explorer_raw or not explorer_raw.strip():
            raise ValueError("Explorer agent returned empty raw response")
        explorer_data = json.loads(explorer_raw)
        logger.info("Explorer agent completed and parsed successfully")
    except Exception as e:
        logger.error("Pipeline Step 2 (Explorer Agent) Failed: %s. Proceeding with fallback.", str(e))
        explorer_data = get_explorer_fallback()

    # 4. Run Funding Agent
    logger.info("Funding started")
    logger.info("====================================")
    logger.info("Pipeline Step 3: Funding Agent Input: %s", json.dumps(explorer_data))
    t_start = time.time()
    try:
        funding_raw = await execute_agent(funding_agent, json.dumps(explorer_data))
        t_end = time.time()
        logger.info("Pipeline Step 3: Funding Agent Raw Output (Time: %.2fs)", t_end - t_start)
        if not funding_raw or not funding_raw.strip():
            raise ValueError("Funding agent returned empty raw response")
        funding_data = json.loads(funding_raw)
        logger.info("Funding agent completed and parsed successfully")
        
        # 1. Populate cost_analysis if missing or empty
        if not funding_data.get("cost_analysis") or len(funding_data.get("cost_analysis", [])) == 0:
            logger.info("Funding agent output missing cost analysis, populating programmatically from database")
            cost_analysis = []
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
            
            for country in explorer_data.get("matched_countries", []):
                code = resolve_country_code(country.get("country_code"))
                try:
                    db_country = database.get_country(code)
                    if db_country:
                        tuition = db_country.get("avg_tuition_annual_usd", 15000.0)
                        living = db_country.get("avg_living_annual_usd", 15000.0)
                        visa_fee = db_country.get("visa_app_fee_usd", 150.0)
                        health = db_country.get("health_insurance_usd", 1000.0)
                        setup = db_country.get("first_year_setup_usd", 1500.0)
                        total_1yr = tuition + living + visa_fee + health + setup
                        salary = base_salary * salary_factors.get(code, 0.7)
                        
                        roi_score = 7
                        if code == "DE":
                            roi_score = 9
                        elif code == "AU":
                            roi_score = 6
                        elif code == "NL":
                            roi_score = 7
                        elif code == "CA":
                            roi_score = 7
                        elif code == "JP":
                            roi_score = 7
                            
                        cost_analysis.append({
                            "country_code": code,
                            "annual_tuition_usd": tuition,
                            "annual_living_usd": living,
                            "visa_app_fee_usd": visa_fee,
                            "health_insurance_usd": health,
                            "first_year_setup_usd": setup,
                            "gross_first_year_cost_usd": total_1yr,
                            "expected_salary_usd": salary,
                            "financial_roi_score": roi_score
                        })
                except Exception as e:
                    logger.error("Error populating cost analysis for %s: %s", code, str(e))
            funding_data["cost_analysis"] = cost_analysis

        # 2. Supplement/Populate matching_scholarships from database
        existing_scholarships = funding_data.get("matching_scholarships", [])
        if not isinstance(existing_scholarships, list):
            existing_scholarships = []
            
        # We always supplement to ensure a complete, database-grounded list in the UI
        logger.info("Supplementing scholarship list from database")
        matching_scholarships = list(existing_scholarships)
        seen_scholarships = {s.get("name") for s in matching_scholarships if isinstance(s, dict) and s.get("name")}
        
        degree_level = profile_data.get("degree_level", "Master")
        clean_level = None
        if degree_level:
            level_lower = degree_level.lower()
            if "master" in level_lower:
                clean_level = "Master"
            elif "phd" in level_lower or "doctor" in level_lower:
                clean_level = "PhD"
            elif "bachelor" in level_lower:
                clean_level = "Bachelor"
            
        for country in explorer_data.get("matched_countries", []):
            code = country.get("country_code")
            try:
                db_scholarships = database.get_scholarships(code, clean_level)
                for s in db_scholarships:
                    if s['name'] not in seen_scholarships:
                        seen_scholarships.add(s['name'])
                        matching_scholarships.append({
                            "name": s['name'],
                            "sponsor": s['sponsor'],
                            "award_amount_usd": s['award_amount_usd'],
                            "deadline": s['application_deadline'],
                            "eligibility_summary": s['description'],
                            "application_link": s['link']
                        })
            except Exception as e:
                logger.error("Error populating scholarships for %s: %s", code, str(e))
        funding_data["matching_scholarships"] = matching_scholarships
    except Exception as e:
        logger.error("Pipeline Step 3 (Funding Agent) Failed: %s. Proceeding with fallback.", str(e))
        funding_data = get_funding_fallback()

    # ==========================================================
    # Dynamic Data Normalization & Validation Layer
    # Ensures 100% realism, consistency, and alignment with DB
    # ==========================================================
    logger.info("Applying dynamic data normalization layer")
    
    # 1. Normalize Country Data in Explorer
    visa_complexity_map = {
        "US": "High", "CA": "Medium", "DE": "Medium", "UK": "High", "AU": "High", "NL": "Medium", "JP": "Medium", "IN": "Low"
    }
    risk_level_map = {
        "US": "Medium", "CA": "Low", "DE": "Low", "UK": "Medium", "AU": "Low", "NL": "Low", "JP": "Low", "IN": "Medium"
    }
    salary_factors = {
        "US": 1.0, "CA": 0.75, "DE": 0.65, "UK": 0.65, "AU": 0.80, "NL": 0.70, "JP": 0.50, "IN": 0.15
    }
    scholarship_matches = {
        "US": ["Fulbright Foreign Student Program"],
        "DE": ["DAAD Scholarship", "Erasmus Mundus Joint Masters"],
        "CA": ["Ontario Graduate Scholarship (OGS)"],
        "NL": ["Holland Scholarship", "Erasmus Mundus Joint Masters"],
        "UK": ["Chevening Scholarships"],
        "AU": [],
        "JP": []
    }

    # Identify base salary for the target role from database
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
        logger.error("Error resolving base salary: %s", str(e))

    # Clean and synchronize Explorer Matched Countries
    normalized_countries = []
    for country in explorer_data.get("matched_countries", []):
        code = resolve_country_code(country.get("country_code", ""))
        country["country_code"] = code
        try:
            db_country = database.get_country(code)
            if db_country:
                country["country_name"] = db_country.get("name", country.get("country_name"))
                country["post_study_work_months"] = int(db_country.get("post_study_work_months", country.get("post_study_work_months", 12)))
                country["visa_complexity"] = visa_complexity_map.get(code, country.get("visa_complexity", "Medium"))
                country["language_barrier"] = db_country.get("language_barrier_level", country.get("language_barrier", "Low"))
                country["risk_level"] = risk_level_map.get(code, country.get("risk_level", "Medium"))
                country["risk_analysis"] = db_country.get("risk_factors", country.get("risk_analysis", ""))
        except Exception as e:
            logger.error("Error normalizing country card %s: %s", code, str(e))
        normalized_countries.append(country)
    explorer_data["matched_countries"] = normalized_countries

    # Normalize Scholarships first to strictly align with target countries
    final_scholarships = []
    seen_sch = set()
    for country in explorer_data.get("matched_countries", []):
        code = country.get("country_code", "")
        allowed_names = scholarship_matches.get(code, [])
        for name in allowed_names:
            if (name, code) in seen_sch:
                continue
            try:
                conn = sqlite3.connect(database.DB_PATH)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM scholarships WHERE name = ?", (name,))
                row = cursor.fetchone()
                conn.close()
                if row:
                    s = dict(row)
                    final_scholarships.append({
                        "name": s['name'],
                        "sponsor": s['sponsor'],
                        "award_amount_usd": s['award_amount_usd'],
                        "deadline": s['application_deadline'],
                        "eligibility_summary": s['description'],
                        "application_link": s['link'],
                        "country_code": code
                    })
                    seen_sch.add((name, code))
            except Exception as e:
                logger.error("Error fetching scholarship %s: %s", name, str(e))
    funding_data["matching_scholarships"] = final_scholarships

    # Synchronize Cost Breakdowns in Funding and compute ROI using net cost
    normalized_cost_analysis = []
    for cost in funding_data.get("cost_analysis", []):
        code = resolve_country_code(cost.get("country_code", ""))
        cost["country_code"] = code
        try:
            db_country = database.get_country(code)
            if db_country:
                tuition = db_country.get("avg_tuition_annual_usd", 15000.0)
                living = db_country.get("avg_living_monthly_usd", 1200.0)
                total_1yr = tuition + 12 * living
                salary = base_salary * salary_factors.get(code, 0.7)
                
                # Retrieve the max scholarship value for this country to calculate Net (Final) Cost
                country_schs = [s for s in final_scholarships if s.get("country_code") == code]
                max_sch_val = max([s.get("award_amount_usd", 0.0) for s in country_schs], default=0.0)
                final_cost = max(0.0, total_1yr - max_sch_val)
                
                # Determine ROI dynamically based on net cost
                if final_cost > 0:
                    roi_score = min(10, max(1, int((salary / final_cost) * 2.5 + 2.0)))
                else:
                    roi_score = 10
                
                cost["annual_tuition_usd"] = tuition
                cost["monthly_living_usd"] = living
                cost["total_1yr_usd"] = total_1yr
                cost["expected_salary_usd"] = salary
                cost["financial_roi_score"] = roi_score
        except Exception as e:
            logger.error("Error normalizing cost breakdown for %s: %s", code, str(e))
        normalized_cost_analysis.append(cost)
    funding_data["cost_analysis"] = normalized_cost_analysis

    logger.info("Data normalization complete.")
    logger.info("====================================")
    return {"profile": profile_data, "explorer": explorer_data, "funding": funding_data}
