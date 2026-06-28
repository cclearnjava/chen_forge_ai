from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.auth.middleware import get_admin_email
from app.schemas import RunAgentRequest
from app.services.agent_workflow import run_diagnosis, run_proposal, run_intake_response
from app.models import AgentTask

router = APIRouter(tags=["agents"])


@router.post("/leads/{lead_id}/run-diagnosis", status_code=202)
def trigger_diagnosis(
    lead_id: str,
    req: RunAgentRequest = RunAgentRequest(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    try:
        result = run_diagnosis(db, lead_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@router.post("/leads/{lead_id}/run-proposal", status_code=202)
def trigger_proposal(
    lead_id: str,
    req: RunAgentRequest = RunAgentRequest(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    try:
        result = run_proposal(db, lead_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@router.post("/leads/{lead_id}/run-intake-response", status_code=202)
def trigger_intake_response(
    lead_id: str,
    req: RunAgentRequest = RunAgentRequest(),
    db: Session = Depends(get_db),
    _admin: str = Depends(get_admin_email),
):
    try:
        result = run_intake_response(db, lead_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")


@router.get("/agent-tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(AgentTask).filter(AgentTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task": {
            "id": task.id,
            "lead_id": task.lead_id,
            "agent_name": task.agent_name,
            "status": task.status.value,
            "input_json": task.input_json,
            "output_json": task.output_json,
            "error_message": task.error_message,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    }
