import os
import sys
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Add current folder to path
sys.path.append(os.path.dirname(__file__))

import agents
import database
import simulator
import report_generator

# Initialize database
database.init_db()

app = FastAPI(title="AgentBridge API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request schemas
class AnalysisRequest(BaseModel):
    resume_text: str
    goals: str
    degree_level: str

class ChatRequest(BaseModel):
    chat_history: List[Dict[str, str]]
    context_data: Dict[str, Any]

class SimulationRequest(BaseModel):
    profile_data: Dict[str, Any]
    goals: str
    budget: Optional[float] = None
    experience_level: Optional[str] = None
    require_scholarship: Optional[bool] = False

class ReportDownloadRequest(BaseModel):
    profile: Dict[str, Any]
    explorer: Dict[str, Any]
    funding: Dict[str, Any]
    simulation: Optional[Dict[str, Any]] = None
    currency: Optional[str] = "USD"

@app.post("/api/analyze")
async def analyze_profile(req: AnalysisRequest):
    try:
        if not req.resume_text.strip():
            raise HTTPException(status_code=400, detail="Resume text is required")
        if not req.goals.strip():
            raise HTTPException(status_code=400, detail="Career goals and preferences are required")
        
        print(f"Received analysis request for degree level: {req.degree_level}")
        result = await agents.run_agent_pipeline(
            resume_text=req.resume_text,
            goals=req.goals,
            degree_level=req.degree_level
        )
        return result
    except Exception as e:
        print(f"Error during agent pipeline execution: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")
@app.post("/api/chat")
async def chat_advisor(req: ChatRequest):
    try:
        response_text = await agents.run_chat_advisor(
            chat_history=req.chat_history,
            context_data=req.context_data
        )
        return {"response": response_text}
    except Exception as e:
        print(f"Error during chat advisor: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.post("/api/simulate")
async def simulate_scenarios(req: SimulationRequest):
    try:
        print(f"Running scenario simulation for role: {req.profile_data.get('target_role')}")
        result = simulator.run_simulation(
            profile_data=req.profile_data,
            goals=req.goals,
            budget=req.budget,
            experience_level=req.experience_level,
            require_scholarship=req.require_scholarship
        )
        return result
    except Exception as e:
        print(f"Error during scenario simulation: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@app.post("/api/report/download")
async def download_report(req: ReportDownloadRequest):
    try:
        profile = req.profile
        explorer = req.explorer
        funding = req.funding
        sim = req.simulation
        currency = req.currency

        # Generate PDF report
        pdf_bytes = report_generator.generate_pdf_report(
            profile=profile,
            explorer=explorer,
            funding=funding,
            simulation=sim,
            currency=currency
        )

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=AgentBridge_Global_Career_Blueprint.pdf"}
        )
    except Exception as e:
        print(f"Error exporting report: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")

# Mount static files at root (served after API endpoints)
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if not os.path.exists(frontend_dir):
    os.makedirs(frontend_dir)

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
