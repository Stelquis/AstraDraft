"""
DeepAstraDraft v1.0 API — 公用 CAD 问答服务（无需登录）。

端点:
  POST /upload              — 上传 DWG/DXF → 自动解析 → 返回 drawing_id
  GET  /drawings            — 列出所有已解析图纸
  GET  /drawings/{id}       — 图纸详情
  POST /drawings/{id}/query — 对指定图纸提问
  GET  /drawings/{id}/history — 图纸问答历史
  GET  /health              — 健康检查
  GET  /skills              — 可用 Skill 列表

启动: uvicorn backend.api:app --host 0.0.0.0 --port 8000
"""
import json
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.config import AgentConfig
from agent.core import DeepAstraDraft
from backend.database import (
    add_drawing, update_drawing, get_drawing, list_drawings,
    add_query, get_query_history,
)

app = FastAPI(title="DeepAstraDraft v1.0", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

_config = AgentConfig()
_upload_dir = Path("data/uploads")
_upload_dir.mkdir(parents=True, exist_ok=True)

_agents: Dict[str, DeepAstraDraft] = {}


# ---- 数据模型 ----

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: str = Field(default="")


class DrawingSummary(BaseModel):
    id: str
    filename: str
    file_size: int
    status: str
    param_count: int
    created_at: str


# ---- 图纸上传 + 解析 ----

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    """上传 CAD 图纸 → 自动解析 → 返回 drawing_id"""
    drawing_id = uuid.uuid4().hex[:12]
    file_path = _upload_dir / f"{drawing_id}_{file.filename}"
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    db_id = add_drawing(file.filename, str(file_path), len(content))

    try:
        agent = DeepAstraDraft(_config)
        agent.load_cad(str(file_path))
        index_json = json.dumps([
            {"name": p.name, "value": p.value, "unit": p.unit,
             "layer": p.layer, "raw_text": p.raw_text}
            for p in agent._index.parameters
        ], ensure_ascii=False)
        update_drawing(db_id, status="ready", param_count=agent.parameter_count, index_json=index_json)
        _agents[db_id] = agent
        return {"drawing_id": db_id, "filename": file.filename, "status": "ready", "param_count": agent.parameter_count}
    except Exception as e:
        update_drawing(db_id, status="error")
        raise HTTPException(status_code=400, detail=f"解析失败: {e}")


# ---- 图纸列表 / 详情 ----

@app.get("/drawings")
async def drawings_list():
    drawings = list_drawings()
    return {"drawings": drawings, "total": len(drawings)}


@app.get("/drawings/{drawing_id}")
async def drawing_detail(drawing_id: str):
    d = get_drawing(drawing_id)
    if not d:
        raise HTTPException(status_code=404, detail="图纸不存在")
    return d


# ---- 对话查询 ----

def _resolve_agent(drawing_id: str) -> DeepAstraDraft:
    agent = _agents.get(drawing_id)
    if agent:
        return agent
    d = get_drawing(drawing_id)
    if not d:
        raise HTTPException(status_code=404, detail="图纸不存在")
    if d["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"图纸状态: {d['status']}")
    agent = DeepAstraDraft(_config)
    agent.load_cad(d["file_path"])
    _agents[drawing_id] = agent
    return agent


@app.post("/drawings/{drawing_id}/query")
async def query_drawing(drawing_id: str, req: QueryRequest):
    agent = _resolve_agent(drawing_id)
    answer = agent.ask(req.question)
    source = "deep_agent" if agent.is_deep_agent_available else "rule"
    add_query(drawing_id, req.question, answer, source, req.session_id)
    return {"answer": answer, "source": source, "drawing_id": drawing_id}


@app.get("/drawings/{drawing_id}/history")
async def drawing_history(drawing_id: str, limit: int = 50):
    history = get_query_history(drawing_id, limit)
    return {"drawing_id": drawing_id, "history": history, "total": len(history)}


# ---- 健康检查 / Skills ----

@app.get("/health")
async def health():
    return {"status": "ok", "cached_agents": len(_agents)}


@app.get("/skills")
async def list_skills():
    from agent.skills import SkillRegistry
    return SkillRegistry().get_all_skill_descriptions()


# ---- 静态文件（前端构建产物） ----

frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
