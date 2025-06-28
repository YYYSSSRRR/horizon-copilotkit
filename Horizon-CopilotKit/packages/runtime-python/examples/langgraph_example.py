#!/usr/bin/env python3
"""
LangGraph integration example for CopilotKit Python Runtime

This example demonstrates how to use the CopilotKit Python Runtime
with LangGraph Platform agents.
"""

import os
from copilotkit_runtime import (
    CopilotRuntime,
    EmptyAdapter,
    LangGraphPlatformEndpoint,
    run_copilot_server,
)


def main():
    """Main function to run the CopilotKit server with LangGraph"""
    
    # Create LangGraph Platform endpoint
    langgraph_endpoint = LangGraphPlatformEndpoint(
        deployment_url=os.getenv("LANGGRAPH_DEPLOYMENT_URL", ""),
        langsmith_api_key=os.getenv("LANGSMITH_API_KEY", ""),
        agents=[
            {
                "name": "research_agent",
                "description": "A helpful research agent that can search and analyze information",
            },
            {
                "name": "writing_agent", 
                "description": "A writing assistant that helps with content creation",
            },
        ],
    )
    
    # Create runtime with remote endpoints
    runtime = CopilotRuntime(
        remote_endpoints=[langgraph_endpoint],
        delegate_agent_processing_to_service_adapter=True,
    )
    
    # Use EmptyAdapter for agent-only mode
    adapter = EmptyAdapter()
    
    # Run server
    print("Starting CopilotKit Python Runtime server with LangGraph...")
    print("GraphQL endpoint: http://localhost:8000/api/copilotkit")
    print("Available agents: research_agent, writing_agent")
    
    run_copilot_server(
        runtime=runtime,
        service_adapter=adapter,
        host="0.0.0.0",
        port=8000,
        endpoint="/api/copilotkit",
    )


if __name__ == "__main__":
    main() 