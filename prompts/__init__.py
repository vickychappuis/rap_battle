"""
Prompts package for Rap Battle AI

Contains all agent prompt templates.
Each agent has its own prompt file.
"""

from .agent_one_prompt import AGENT_ONE_PROMPT_TEMPLATE, AGENT_ONE_METADATA
from .agent_two_prompt import AGENT_TWO_PROMPT_TEMPLATE, AGENT_TWO_METADATA

# Legacy names for backwards compatibility
AGENT1_PROMPT_TEMPLATE = AGENT_ONE_PROMPT_TEMPLATE
AGENT2_PROMPT_TEMPLATE = AGENT_TWO_PROMPT_TEMPLATE

PROMPT_METADATA = {
    "agent1": AGENT_ONE_METADATA,
    "agent2": AGENT_TWO_METADATA
}

__all__ = [
    # New names
    "AGENT_ONE_PROMPT_TEMPLATE",
    "AGENT_TWO_PROMPT_TEMPLATE",
    "AGENT_ONE_METADATA",
    "AGENT_TWO_METADATA",
    # Legacy names (backwards compatible)
    "AGENT1_PROMPT_TEMPLATE",
    "AGENT2_PROMPT_TEMPLATE",
    "PROMPT_METADATA"
]
