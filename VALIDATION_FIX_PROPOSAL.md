# Rap Battle AI: Validation System Analysis

## Problem Statement

The system currently fails with validation errors during lyrics generation.

### Observed Behavior
```
Error: Bar 1 has 9 words, expected exactly 8
Generated: "You say you're pro, but I'm the one winning"
Status: REJECTED
```

### Current Implementation

The system enforces strict word counts per bar (exactly 8 words per 4-beat bar), based on:
- Assumption: 2 words per beat = 8 words per 4-beat bar

### Technical Issue

1. **Words vs Syllables**
   - "You're" = 1 syllable
   - "heavyweight" = 3 syllables
   - 8 words can range from 8 to 24+ syllables

2. **Example:**
   ```
   Bar A: "You say you're pro but I'm the one" (8 words, 9 syllables) - Passes
   Bar B: "You say you're pro but I'm the one winning" (9 words, 11 syllables) - Fails
   ```
   Bar B has 2 additional syllables but fails validation.

3. **Industry Standard:**
   - Rappers vary word count per bar based on syllable density
   - TTS systems process syllables and phonemes, not word counts
   - Professional rap lyrics have variable word counts per bar

## Current System Impact

- System reliability: Frequent validation failures with GPT-4o-mini
- API costs: Failed generations incur charges
- User experience: System crashes on validation errors
- Output: Potentially valid lyrics are rejected

## Proposed Options

### Option A: Maintain Current Validation
- Keep exact 8-word-per-bar requirement
- Increase model to GPT-4 for better instruction following

### Option B: Flexible Validation
- Change from strict per-bar word counts to total budget approach

### Option B Details

#### Tier 1: Total Word Budget
```python
target_words = 29  # For 15 beats at 2 words/beat average
acceptable_range = 24-34 words  # ±20% tolerance

if total_words in acceptable_range:
    PASS
else:
    FAIL
```

#### Tier 2: Per-Bar Range
```python
# Current: Exactly 8 words per bar
bars_word_count = [8, 8, 8]

# Option B: 6-10 words per bar
bars_word_count = [7, 9, 8]
```

#### Tier 3: Beat Mapping (Agent 2)
Agent 2 maps words to beats with variable density:

```
Beat 1: "You say" (2 words)
Beat 2: "you're pro but" (3 words)
Beat 3: "I'm the" (2 words)
Beat 4: "one winning" (2 words)
Total: 9 words across 4 beats
```

## Technical Implementation (Option B)

### Change 1: Modify Bar Validation
**File:** `main.py`

```python
# Current
@field_validator('bars')
@classmethod
def validate_bars_word_count(cls, v):
    for i, bar in enumerate(v):
        word_count = len(bar.split())
        if word_count != 8:
            raise ValueError(f"Bar {i+1} has {word_count} words, expected exactly 8")
    return v

# Proposed
@field_validator('bars')
@classmethod
def validate_bars_word_count(cls, v):
    for i, bar in enumerate(v):
        word_count = len(bar.split())
        if word_count < 6 or word_count > 10:
            raise ValueError(f"Bar {i+1} has {word_count} words, expected 6-10 words")
    return v
```

### Change 2: Add Total Budget Check
**File:** `main.py`

```python
def validate_agent1_output(output: Agent1Output, expected_full_bars: int,
                          expected_tail_words: int, total_budget: int) -> None:
    # Check bar count
    if len(output.bars) != expected_full_bars:
        raise ValueError(f"Expected {expected_full_bars} full bars, got {len(output.bars)}")

    # NEW: Check total word budget (with tolerance)
    total_words = sum(len(bar.split()) for bar in output.bars)
    total_words += len(output.tail.split()) + 1  # +1 for final held word

    min_budget = int(total_budget * 0.8)  # -20%
    max_budget = int(total_budget * 1.2)  # +20%

    if not (min_budget <= total_words <= max_budget):
        raise ValueError(
            f"Total words {total_words} outside acceptable range {min_budget}-{max_budget}"
        )

    print(f"✓ Validation passed: {len(output.bars)} bars, {total_words} total words")
```

### Change 3: Update Prompt
**File:** `prompts/agent_one_prompt.py`

```markdown
# Current
- Each full bar = **EXACTLY 8 words** (4 beats × 2 words/beat)

# Proposed
- Each full bar = **6-10 words** (approximately 2 words per beat)
- Total response = **~29 words** (primary constraint)
```

## Options Analysis

### Option A: Use GPT-4
- No code changes required
- Maintains strict 8-word validation
- Uses GPT-4 model (higher cost per call)

### Option B: Flexible Validation
- Requires code modifications (3 files)
- Changes validation to 6-10 words per bar
- Continues using GPT-4o-mini
- Less strict validation rules

## Implementation Timeline (Option B)

- Code changes: 30 minutes
- Testing: 1 hour (10+ test cases)
- Deployment: Immediate (no API breaking changes)

## Measurement Criteria

Post-implementation metrics to track:
1. Success rate
2. Average total word count vs budget
3. API cost per successful generation
4. TTS output quality (subjective)

---

**Date:** 2026-01-01
**Status:** Pending Decision
