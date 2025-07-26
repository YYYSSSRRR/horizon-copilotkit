"""
Debug Example LangGraph FastAPI Server
直接复用 demo-viewer 的 human_in_the_loop agent
"""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from copilotkit.integrations.fastapi import add_fastapi_endpoint
from copilotkit import CopilotKitSDK, LangGraphAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 直接从debug-example复制的human_in_the_loop agent
from debug_langgraph.human_in_the_loop_agent import debug_human_in_the_loop_graph

app = FastAPI()

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"📨 {request.method} {request.url} from {request.client.host if request.client else 'unknown'}")
    if request.method == "POST" and "/copilotkit" in str(request.url):
        # Read body for logging
        body = await request.body()
        logger.info(f"📨 CopilotKit POST request - Body length: {len(body)} bytes")
        if len(body) < 1000:  # Only log small bodies
            try:
                import json
                body_json = json.loads(body.decode())
                logger.info(f"📨 Request data: {body_json}")
            except:
                logger.info(f"📨 Raw body: {body.decode()[:200]}...")
        
        # Re-create request with body for downstream processing
        request = Request(request.scope, lambda: body)
    
    response = await call_next(request)
    logger.info(f"📤 Response status: {response.status_code}")
    return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有源，生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"🔍 Loading agent graph: {debug_human_in_the_loop_graph}")

sdk = CopilotKitSDK(
    agents=[
        LangGraphAgent(
            name="debug_human_in_the_loop",
            description="Debug task planning with human-in-the-loop confirmation.",
            graph=debug_human_in_the_loop_graph,
        ),
    ]
)

print(f"🔍 SDK initialized with agents: {[agent.name for agent in sdk.agents]}")

add_fastapi_endpoint(app, sdk, "/copilotkit")

@app.get("/healthz")
def health():
    """Health check."""
    return {"status": "ok"}

@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Debug Example LangGraph Server"}

@app.get("/test-agent")
def test_agent():
    """Test if agent is properly configured."""
    try:
        from debug_langgraph.human_in_the_loop_agent import debug_human_in_the_loop_graph
        return {"agent_loaded": True, "graph_type": str(type(debug_human_in_the_loop_graph))}
    except Exception as e:
        return {"agent_loaded": False, "error": str(e)}

@app.post("/test-copilotkit")
async def test_copilotkit(request: Request):
    """Test CopilotKit endpoint directly."""
    body = await request.json()
    logger.info(f"🧪 Test CopilotKit request: {body}")
    return {"received": True, "body_keys": list(body.keys())}

def main():
    """Run the uvicorn server."""
    port = int(os.getenv("PORT", "8001"))  # 使用8001避免与Node.js后端冲突
    uvicorn.run(
        "debug_langgraph.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )

if __name__ == "__main__":
    main()