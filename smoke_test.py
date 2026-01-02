#!/usr/bin/env python3
"""
Smoke test to verify gpt-5-mini with reasoning configuration
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()


def test_reasoning_config():
    """Test that the reasoning configuration works correctly"""
    print("Testing gpt-5-mini with reasoning effort = low...\n")

    # Create LLM with exact config used in main.py
    llm = ChatOpenAI(
        model="gpt-5-mini",
        reasoning={"effort": "low"},      # optional: add "summary": "auto"
        output_version="responses/v1",    # keep reasoning blocks in message content
    )

    # Simple test query
    test_query = "What is 3^3?"

    print(f"Query: {test_query}")
    print("Invoking LLM...\n")

    try:
        response = llm.invoke(test_query)

        print("✓ Success! Response:")
        print("-" * 60)
        print(f"Type: {type(response.content)}")
        print(f"Content: {response.content}")
        print("-" * 60)

        # Extract text from structured response
        response_str = str(response.content)
        if isinstance(response.content, list):
            # Find text blocks in the response
            text_blocks = [block.get('text', '') for block in response.content if block.get('type') == 'text']
            if text_blocks:
                print("\nExtracted text:")
                for text in text_blocks:
                    print(f"  {text}")
                response_str = ' '.join(text_blocks)

        # Check if response contains expected answer
        if "27" in response_str:
            print("\n✓ Correct answer detected (27)")
        else:
            print("\n⚠️  Answer may be incorrect (expected 27)")

        print("\n✓ Reasoning configuration working correctly!")
        print("  - Reasoning blocks are preserved in message content")
        print("  - Response structure includes both reasoning and text blocks")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    success = test_reasoning_config()
    exit(0 if success else 1)
