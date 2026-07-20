"""
Judge Prompt Template

This agent judges a rap battle and picks a winner.
"""


def build_judge_system_prompt(opponent_name: str) -> str:
    return (
        "You are a legendary hip-hop battle judge — think DJ Khaled meets Sway Calloway. "
        f"You just watched a rap battle between two MCs: {opponent_name} and their opponent. "
        f"When talking about {opponent_name}, refer to them as 'you' (e.g. 'you came weak' not '{opponent_name} came weak'). "
        f"Refer to the other rapper by their name: {opponent_name}'s opponent. "
        "Judge them on bars, flow, punchlines, wordplay, and stage presence. "
        "Keep it real — talk like you're on a rap battle stage, with energy and slang. "
        "Respond ONLY with valid JSON: "
        '{"winner": "user" or "ai", "reason": "one punchy sentence, hip-hop style"}'
    )


def build_judge_transcript(turn_history, opponent_name: str) -> str:
    lines = []
    for turn in turn_history:
        if turn.player == "user":
            lines.append(f"Opponent verse: {turn.transcription or '(no transcription)'}")
        else:
            lines.append(f"{opponent_name} verse: {turn.lyrics or '(no lyrics)'}")
    return "\n".join(lines)
