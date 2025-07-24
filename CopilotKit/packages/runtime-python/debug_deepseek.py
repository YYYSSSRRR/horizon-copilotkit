#!/usr/bin/env python3
"""
Debug script to test DeepSeek adapter schema generation
"""

import sys
import os
import asyncio
import json
from typing import Dict, Any

# Add the package to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from copilotkit_runtime.service_adapters.deepseek.adapter import DeepSeekAdapter, DeepSeekAdapterParams
from copilotkit_runtime.api.models.requests import ActionInput


class MockActionInput:
    """Mock action input for testing"""
    
    def __init__(self, name: str, description: str = "", json_schema: Any = None, parameters: Any = None):
        self.name = name
        self.description = description
        if json_schema is not None:
            self.json_schema = json_schema
        if parameters is not None:
            self.parameters = parameters


def test_schema_generation():
    """Test various schema generation scenarios"""
    
    # Create adapter with test key
    params = DeepSeekAdapterParams(api_key="test_key")
    adapter = DeepSeekAdapter(params)
    
    print("🧪 Testing DeepSeek adapter schema generation...")
    
    # Test case 1: Empty json_schema
    print("\n--- Test 1: Empty json_schema ---")
    action1 = MockActionInput(
        name="test_action_1", 
        description="Test action with empty json_schema",
        json_schema=""
    )
    tool1 = adapter._convert_action_input_to_openai_tool(action1)
    print("Generated tool:", json.dumps(tool1, indent=2))
    
    # Test case 2: Valid json_schema
    print("\n--- Test 2: Valid json_schema ---")
    action2 = MockActionInput(
        name="test_action_2",
        description="Test action with valid json_schema",
        json_schema='{"type": "object", "properties": {"location": {"type": "string", "description": "The location"}}, "required": ["location"]}'
    )
    tool2 = adapter._convert_action_input_to_openai_tool(action2)
    print("Generated tool:", json.dumps(tool2, indent=2))
    
    # Test case 3: Dict json_schema
    print("\n--- Test 3: Dict json_schema ---")
    action3 = MockActionInput(
        name="test_action_3",
        description="Test action with dict json_schema",
        json_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    )
    tool3 = adapter._convert_action_input_to_openai_tool(action3)
    print("Generated tool:", json.dumps(tool3, indent=2))
    
    # Test case 4: Parameters dict
    print("\n--- Test 4: Parameters dict ---")
    action4 = MockActionInput(
        name="test_action_4",
        description="Test action with parameters dict",
        parameters={
            "message": {"type": "string", "description": "Message to send"}
        }
    )
    tool4 = adapter._convert_action_input_to_openai_tool(action4)
    print("Generated tool:", json.dumps(tool4, indent=2))
    
    # Test case 5: No schema at all
    print("\n--- Test 5: No schema ---")
    action5 = MockActionInput(
        name="test_action_5",
        description="Test action with no schema"
    )
    tool5 = adapter._convert_action_input_to_openai_tool(action5)
    print("Generated tool:", json.dumps(tool5, indent=2))
    
    # Test case 6: Invalid json_schema
    print("\n--- Test 6: Invalid json_schema ---")
    action6 = MockActionInput(
        name="test_action_6",
        description="Test action with invalid json_schema",
        json_schema='{"invalid": json}'
    )
    tool6 = adapter._convert_action_input_to_openai_tool(action6)
    print("Generated tool:", json.dumps(tool6, indent=2))
    
    print("\n✅ Schema generation tests completed")


if __name__ == "__main__":
    test_schema_generation()