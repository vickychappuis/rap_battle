"""Tests for the judge and lyricist prompt builders."""

from dataclasses import dataclass

from core.prompts import (
    TURN_INSTRUCTIONS,
    build_judge_system_prompt,
    build_judge_transcript,
    build_turn_instructions,
)

AI_NAME = "Max Gorilla"


@dataclass
class FakeTurn:
    player: str
    transcription: str | None = None
    lyrics: str | None = None


def _battle_history():
    return [
        FakeTurn(player="user", transcription="your bars are weak"),
        FakeTurn(player="ai", lyrics="nah I run this"),
    ]


# --- #4: judge prompt person mapping ---------------------------------------


def test_judge_prompt_addresses_the_human_as_you():
    prompt = build_judge_system_prompt(AI_NAME)

    # The verdict is shown to the human, so 'you' must be the human, and the
    # AI must never be the one addressed as 'you'.
    assert "the Challenger as 'you'" in prompt
    assert f"When talking about {AI_NAME}, refer to them as 'you'" not in prompt


def test_judge_prompt_names_the_ai_and_labels_both_sides():
    prompt = build_judge_system_prompt(AI_NAME)

    assert f"{AI_NAME}, the AI MC" in prompt
    assert "Challenger (you)" in prompt
    assert f"{AI_NAME} (AI)" in prompt


def test_judge_prompt_states_the_winner_value_mapping():
    prompt = build_judge_system_prompt(AI_NAME)

    assert '"winner" to "user" if the human Challenger won' in prompt
    assert f'to "ai" if {AI_NAME} won' in prompt
    # The strict JSON contract the caller json.loads() must stay intact.
    assert "Respond ONLY with valid JSON" in prompt
    assert '{"winner": "user" or "ai", "reason":' in prompt


def test_judge_prompt_keeps_the_hip_hop_voice():
    prompt = build_judge_system_prompt(AI_NAME)

    assert "legendary hip-hop battle judge" in prompt
    assert "bars, flow, punchlines, wordplay, and stage presence" in prompt


def test_judge_transcript_labels_match_the_system_prompt():
    transcript = build_judge_transcript(_battle_history(), AI_NAME)
    prompt = build_judge_system_prompt(AI_NAME)

    lines = transcript.split("\n")
    assert lines[0] == "Challenger (you) verse: your bars are weak"
    assert lines[1] == f"{AI_NAME} (AI) verse: nah I run this"
    # No ambiguous "Opponent" label the model has to map to a winner value.
    assert "Opponent verse:" not in transcript
    for label in ("Challenger (you)", f"{AI_NAME} (AI)"):
        assert label in prompt


def test_judge_transcript_handles_missing_content():
    history = [FakeTurn(player="user"), FakeTurn(player="ai")]
    transcript = build_judge_transcript(history, AI_NAME)

    assert "Challenger (you) verse: (no transcription)" in transcript
    assert f"{AI_NAME} (AI) verse: (no lyrics)" in transcript


# --- #15: turn instructions scale with the round count ----------------------


def test_turn_instructions_two_round_battle():
    assert build_turn_instructions(1, 2) == TURN_INSTRUCTIONS[1]
    assert build_turn_instructions(2, 2) == TURN_INSTRUCTIONS[2]


def test_turn_instructions_three_round_battle_has_a_real_middle_round():
    opening = build_turn_instructions(1, 3)
    middle = build_turn_instructions(2, 3)
    final = build_turn_instructions(3, 3)

    assert "opening response" in opening
    assert "Middle of the battle (round 2 of 3)" in middle
    assert "Final round" in final
    assert len({opening, middle, final}) == 3
    # The old dict-based lookup fell through to a generic fallback here.
    assert middle not in TURN_INSTRUCTIONS.values()


def test_turn_instructions_five_round_battle_covers_every_round():
    total = 5
    instructions = [build_turn_instructions(n, total) for n in range(1, total + 1)]

    assert "opening response" in instructions[0]
    assert all("Middle of the battle" in text for text in instructions[1:-1])
    assert "Final round" in instructions[-1]


def test_turn_instructions_single_round_battle_closes_out():
    assert "Final round" in build_turn_instructions(1, 1)


def test_turn_instructions_beyond_the_last_round_still_closes_out():
    assert "Final round" in build_turn_instructions(4, 3)
