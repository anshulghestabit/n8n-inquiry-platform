import json
from pathlib import Path
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.db.client import get_supabase_admin_client
from app.middleware.auth import get_current_user


router = APIRouter(tags=["workflows"])
settings = get_settings()

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "inquiry_workflow.json"
N8N_MUTABLE_KEYS = {"name", "nodes", "connections", "settings"}

AgentRole = Literal["classifier", "researcher", "qualifier", "responder", "executor"]
TriggerChannel = Literal["gmail", "telegram", "both"]

ROLE_TO_NODE = {
    "classifier": "Classifier_Agent",
    "researcher": "Researcher_Agent",
    "qualifier": "Qualifier_Agent",
    "responder": "Responder_Agent",
    "executor": "Executor_Agent",
}

DEFAULT_AGENTS = [
    {
        "name": "Classifier Agent",
        "role": "classifier",
        "system_prompt": "You are a sales-focused customer inquiry classifier for a demo workflow. Think internally if needed, but output ONLY compact raw JSON with no markdown and no explanation. Required keys: type, priority, confidence. Classify pricing, demo, procurement, enterprise, seats, onboarding, automation, implementation timeline, or purchase-intent messages as sales_inquiry. type must be one of sales_inquiry, support_ticket, complaint, general_question, order_request. priority must be low, medium, or high. confidence must be a number from 0 to 1.",
        "tools": [],
        "handoff_rules": "Pass valid classification JSON to the researcher.",
        "output_format": "json",
        "order_index": 1,
    },
    {
        "name": "Researcher Agent",
        "role": "researcher",
        "system_prompt": "You are a sales knowledge-base researcher. Think internally if needed, but output ONLY compact raw JSON with no markdown and no explanation. Required keys: relevant_info, source. Prefer information from the provided Google Drive KB content and return source as google_drive when KB content is present. If no specific information is available, use {\"relevant_info\":\"No specific information found.\",\"source\":\"none\"}.",
        "tools": ["google_drive"],
        "handoff_rules": "Pass research context to the qualifier.",
        "output_format": "json",
        "order_index": 2,
    },
    {
        "name": "Qualifier Agent",
        "role": "qualifier",
        "system_prompt": "You are a sales lead qualifier. Think internally if needed, but output ONLY compact raw JSON with no markdown and no explanation. Required keys: lead_score, reason. lead_score must be a number from 1 to 10. Score sales inquiries higher when they mention pricing, demo, procurement, team size, enterprise requirements, or implementation timeline. reason must be one sentence.",
        "tools": [],
        "handoff_rules": "Pass qualification to the responder.",
        "output_format": "json",
        "order_index": 3,
    },
    {
        "name": "Responder Agent",
        "role": "responder",
        "system_prompt": "You are a sales response specialist. Think internally if needed, but output ONLY compact raw JSON with no markdown and no explanation. Required key: draft_reply. draft_reply must contain the complete professional reply text. For sales inquiries, reference the relevant plan, pricing range, setup timeline, and offer a demo. If information is missing, promise a follow-up within 24 business hours.",
        "tools": [],
        "handoff_rules": "Pass the draft reply to the executor.",
        "output_format": "json",
        "order_index": 4,
    },
    {
        "name": "Executor Agent",
        "role": "executor",
        "system_prompt": "You are an execution coordinator. Think internally if needed, but output ONLY compact raw JSON with no markdown and no explanation. Required keys: sent, channel, logged. Confirm the final response is ready for the selected channel and logging step. Use sent as a boolean, channel as gmail or telegram based on the normalized inquiry channel, and logged as true when the execution should be recorded.",
        "tools": ["gmail", "google_sheets"],
        "handoff_rules": "Route the final reply to the configured channel and logging step.",
        "output_format": "json",
        "order_index": 5,
    },
]

DEFAULT_AGENTS_BY_ROLE = {agent["role"]: agent for agent in DEFAULT_AGENTS}

LEGACY_SYSTEM_PROMPTS = {
    "classifier": "Classify the customer inquiry. Return only JSON with type, priority, and confidence.",
    "researcher": "Find relevant knowledge base context for the inquiry. Return only JSON with relevant_info and source.",
    "qualifier": "Score the lead or request from 1 to 10 and explain the score in one sentence. Return only JSON.",
    "responder": "Draft a professional customer reply using the inquiry, classification, research, and qualification. Return only JSON.",
    "executor": "Confirm the reply is ready to send and log. Return only JSON with sent, channel, and logged.",
}


class WorkflowCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    trigger_channel: TriggerChannel = "both"


class WorkflowUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    trigger_channel: TriggerChannel | None = None
    status: Literal["active", "inactive", "draft"] | None = None


class AgentUpdateRequest(BaseModel):
    system_prompt: str = Field(min_length=1)
    tools: list[str] | None = None
    handoff_rules: str | None = None
    output_format: str | None = None


def api_error(status_code: int, message: str, code: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": message, "code": code})


def n8n_headers() -> dict[str, str]:
    if not settings.n8n_api_key:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "n8n API key is not configured", "N8N_UNAVAILABLE")
    return {"X-N8N-API-KEY": settings.n8n_api_key}


def clone_workflow_template(name: str, trigger_channel: TriggerChannel) -> dict:
    with TEMPLATE_PATH.open() as template_file:
        workflow = json.load(template_file)

    workflow.pop("id", None)
    workflow.pop("active", None)
    workflow["name"] = name

    has_gmail_trigger = False
    has_telegram_trigger = False

    for node in workflow.get("nodes", []):
        node["id"] = f"{node.get('id', node.get('name', 'node'))}-{uuid4().hex[:8]}"
        if node.get("type") == "n8n-nodes-base.gmailTrigger":
            has_gmail_trigger = True
            node["disabled"] = trigger_channel == "telegram"
        if node.get("type") in {"n8n-nodes-base.telegramTrigger", "n8n-nodes-base.webhook"} and node.get("name") == "Telegram Trigger":
            has_telegram_trigger = True
            node["disabled"] = trigger_channel == "gmail"

    if trigger_channel == "gmail" and not has_gmail_trigger:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Gmail trigger is not available in the workflow template",
            "TRIGGER_NOT_SUPPORTED",
        )

    if trigger_channel == "telegram" and not has_telegram_trigger:
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Telegram trigger is not available in the workflow template",
            "TRIGGER_NOT_SUPPORTED",
        )

    if trigger_channel == "both" and (not has_gmail_trigger or not has_telegram_trigger):
        raise api_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Both-channel trigger mode requires Gmail and Telegram trigger nodes",
            "TRIGGER_NOT_SUPPORTED",
        )

    return workflow


def sanitize_n8n_workflow_payload(workflow: dict) -> dict:
    return {key: workflow[key] for key in N8N_MUTABLE_KEYS if key in workflow}


async def n8n_request(method: str, path: str, payload: dict | None = None) -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                f"{settings.n8n_url}{path}",
                headers=n8n_headers(),
                json=payload,
                timeout=10.0,
            )
            response.raise_for_status()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "n8n API unavailable", "N8N_UNAVAILABLE")

    if response.status_code == status.HTTP_204_NO_CONTENT:
        return {}
    return response.json()


async def create_n8n_workflow(workflow: dict) -> dict:
    return await n8n_request("POST", "/api/v1/workflows", sanitize_n8n_workflow_payload(workflow))


async def get_n8n_workflow(n8n_workflow_id: str) -> dict:
    return await n8n_request("GET", f"/api/v1/workflows/{n8n_workflow_id}")


async def update_n8n_workflow(n8n_workflow_id: str, workflow: dict) -> dict:
    return await n8n_request(
        "PUT",
        f"/api/v1/workflows/{n8n_workflow_id}",
        sanitize_n8n_workflow_payload(workflow),
    )


async def delete_n8n_workflow(n8n_workflow_id: str) -> None:
    await n8n_request("DELETE", f"/api/v1/workflows/{n8n_workflow_id}")


def agent_rows(workflow_id: str) -> list[dict]:
    return [{**agent, "workflow_id": workflow_id} for agent in DEFAULT_AGENTS]


def backfill_legacy_agent_prompts(db, agents: list[dict]) -> list[dict]:
    updated_agents = []
    for agent in agents:
        role = agent.get("role")
        default_agent = DEFAULT_AGENTS_BY_ROLE.get(role)
        if default_agent and agent.get("system_prompt") == LEGACY_SYSTEM_PROMPTS.get(role):
            update_data = {
                "system_prompt": default_agent["system_prompt"],
                "tools": default_agent["tools"],
                "handoff_rules": default_agent["handoff_rules"],
                "output_format": default_agent["output_format"],
            }
            db.table("agents").update(update_data).eq("id", agent["id"]).execute()
            agent = {**agent, **update_data}
        updated_agents.append(agent)
    return updated_agents


def replace_system_prompt(node: dict, system_prompt: str) -> bool:
    parameters = node.setdefault("parameters", {})

    if isinstance(parameters.get("jsonBody"), str):
        try:
            body = json.loads(parameters["jsonBody"])
        except json.JSONDecodeError:
            expression_body = parameters["jsonBody"]
            escaped_prompt = json.dumps(system_prompt)
            marker = '"role": "system", "content": '
            marker_index = expression_body.find(marker)
            if marker_index != -1:
                start = marker_index + len(marker)
                if start < len(expression_body) and expression_body[start] == '"':
                    scan = start + 1
                    while scan < len(expression_body):
                        if expression_body[scan] == '"' and expression_body[scan - 1] != "\\":
                            parameters["jsonBody"] = expression_body[:start] + escaped_prompt + expression_body[scan + 1 :]
                            return True
                        scan += 1
            return False
        messages = body.get("messages", [])
        for message in messages:
            if message.get("role") == "system":
                message["content"] = system_prompt
                parameters["jsonBody"] = json.dumps(body)
                return True

    values = parameters.get("messages", {}).get("values", [])
    for message in values:
        if message.get("role") == "system" or message.get("type") == "system":
            message["content"] = system_prompt
            return True

    return False


async def sync_agent_to_n8n(n8n_workflow_id: str, agent_role: AgentRole, system_prompt: str) -> None:
    workflow = await get_n8n_workflow(n8n_workflow_id)
    node_name = ROLE_TO_NODE[agent_role]
    for node in workflow.get("nodes", []):
        if node.get("name") == node_name:
            updated = replace_system_prompt(node, system_prompt)
            if not updated:
                raise api_error(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "Unable to update system prompt in n8n workflow node",
                    "N8N_PROMPT_UPDATE_FAILED",
                )
            await update_n8n_workflow(n8n_workflow_id, workflow)
            return
    raise api_error(status.HTTP_404_NOT_FOUND, "Agent node not found in n8n workflow", "NOT_FOUND")


def get_owned_workflow(db, workflow_id: str, user_id: str) -> dict:
    try:
        result = db.table("workflows").select("*").eq("id", workflow_id).eq("user_id", user_id).single().execute()
    except Exception:
        raise api_error(status.HTTP_404_NOT_FOUND, "Workflow not found", "NOT_FOUND")
    return result.data


@router.post("/workflows", status_code=status.HTTP_201_CREATED)
async def create_workflow(data: WorkflowCreateRequest, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    n8n_workflow = await create_n8n_workflow(clone_workflow_template(data.name, data.trigger_channel))
    n8n_workflow_id = str(n8n_workflow.get("id", ""))
    workflow_id = None

    try:
        workflow_result = (
            db.table("workflows")
            .insert(
                {
                    "user_id": current_user["id"],
                    "name": data.name,
                    "description": data.description,
                    "trigger_channel": data.trigger_channel,
                    "status": "draft",
                    "n8n_workflow_id": n8n_workflow_id,
                    "agent_config": {},
                }
            )
            .execute()
        )
        workflow = workflow_result.data[0]
        workflow_id = workflow["id"]
        db.table("agents").insert(agent_rows(workflow["id"])).execute()
    except Exception:
        if workflow_id:
            try:
                db.table("workflows").delete().eq("id", workflow_id).execute()
            except Exception:
                pass
        if n8n_workflow_id:
            try:
                await delete_n8n_workflow(n8n_workflow_id)
            except Exception:
                pass
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")

    return workflow


@router.get("/workflows")
async def list_workflows(current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    try:
        result = (
            db.table("workflows")
            .select("*")
            .eq("user_id", current_user["id"])
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")
    return result.data or []


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    workflow = get_owned_workflow(db, workflow_id, current_user["id"])
    agents = db.table("agents").select("*").eq("workflow_id", workflow_id).order("order_index").execute()
    return {**workflow, "agents": agents.data or []}


@router.put("/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    data: WorkflowUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    workflow = get_owned_workflow(db, workflow_id, current_user["id"])
    update_data = data.model_dump(exclude_none=True)
    if not update_data:
        return workflow

    if "name" in update_data and workflow.get("n8n_workflow_id"):
        n8n_workflow = await get_n8n_workflow(workflow["n8n_workflow_id"])
        n8n_workflow["name"] = update_data["name"]
        await update_n8n_workflow(workflow["n8n_workflow_id"], n8n_workflow)

    try:
        result = db.table("workflows").update(update_data).eq("id", workflow_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")
    return result.data[0]


@router.delete("/workflows/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    workflow = get_owned_workflow(db, workflow_id, current_user["id"])
    if workflow.get("n8n_workflow_id"):
        await delete_n8n_workflow(workflow["n8n_workflow_id"])
    try:
        db.table("workflows").delete().eq("id", workflow_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")


@router.get("/workflows/{workflow_id}/agents")
async def list_agents(workflow_id: str, current_user: dict = Depends(get_current_user)):
    db = get_supabase_admin_client()
    get_owned_workflow(db, workflow_id, current_user["id"])
    try:
        result = db.table("agents").select("*").eq("workflow_id", workflow_id).order("order_index").execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")
    try:
        return backfill_legacy_agent_prompts(db, result.data or [])
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")


@router.put("/agents/{agent_id}")
async def update_agent(
    agent_id: str,
    data: AgentUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    db = get_supabase_admin_client()
    try:
        agent_result = db.table("agents").select("*").eq("id", agent_id).single().execute()
    except Exception:
        raise api_error(status.HTTP_404_NOT_FOUND, "Agent not found", "NOT_FOUND")

    agent = agent_result.data
    workflow = get_owned_workflow(db, agent["workflow_id"], current_user["id"])
    await sync_agent_to_n8n(workflow["n8n_workflow_id"], agent["role"], data.system_prompt)

    update_data = data.model_dump(exclude_none=True)
    try:
        result = db.table("agents").update(update_data).eq("id", agent_id).execute()
    except Exception:
        raise api_error(status.HTTP_503_SERVICE_UNAVAILABLE, "Database query failed", "DB_ERROR")
    return result.data[0]
