# Performance Analysis: Two-Agent vs Single-Agent Approach

**Date:** 2026-01-21
**Branch:** test/improving-response-time

## Executive Summary

Both approaches produce **valid, structured outputs** that pass all validation checks. Performance varies by run, with single-agent showing **0-20% improvement** in some runs, but **no consistent advantage**.

### Key Findings

✅ **Quality:** Both approaches produce valid outputs
✅ **Structure:** Both pass validation (beat count, grid structure, formatting)
⚠️ **Performance:** Highly variable, no consistent winner
⚠️ **Reliability:** Two-agent has built-in error recovery, single-agent fails completely if one step fails

---

## Test Results Summary

### Validated Comprehensive Tests

| Test Run | Two-Agent | Single-Agent | Winner | Speedup | Time Saved |
|----------|-----------|--------------|---------|---------|------------|
| Run 1    | 21.43s    | 21.85s       | Two-Agent | 0.98x | -0.42s |
| Run 2    | 23.47s    | 19.57s       | Single-Agent | 1.20x | +3.90s |

**Average:** ~0% improvement (within margin of error)

### Earlier Quick Tests (No validation)

| Test Run | Two-Agent | Single-Agent | Speedup | Time Saved |
|----------|-----------|--------------|---------|------------|
| Run 1    | 22.09s    | 18.76s       | 1.18x   | +3.33s |
| Run 2    | 22.09s    | 20.71s       | 1.07x   | +1.38s |
| Run 3    | 22.09s    | 17.46s       | 1.26x   | +4.63s |

---

## Detailed Analysis

### Two-Agent Approach (Current System)

**Architecture:**
```
User Input → Lyricist Agent → Grid Builder Agent → Output
```

**Timing Breakdown:**
- Lyricist: 6-9 seconds (35-40%)
- Grid Builder: 12-15 seconds (60-65%)
- **Total: 18-24 seconds**

**Pros:**
- ✅ Separation of concerns (creative vs formatting)
- ✅ Can validate intermediate outputs
- ✅ Partial recovery possible (if lyricist succeeds but grid builder fails)
- ✅ Easier to debug which agent has issues

**Cons:**
- ❌ Two API calls (network latency)
- ❌ Grid Builder surprisingly slow for formatting task
- ❌ More complex pipeline

### Single-Agent Approach (Experimental)

**Architecture:**
```
User Input → Unified Agent → Output
```

**Timing:**
- Unified: 17-22 seconds
- **Total: 17-22 seconds**

**Pros:**
- ✅ Single API call
- ✅ Slightly simpler code
- ✅ Sometimes faster (10-20% in some runs)

**Cons:**
- ❌ All-or-nothing (if it fails, everything fails)
- ❌ Harder to debug (can't see intermediate lyric output)
- ❌ Performance not consistently better
- ❌ More complex prompt (longer token count)

---

## Quality Comparison

### Sample Output Comparison (Run 1)

**Two-Agent Output:**
```
I hear your noise talk loud sound weak mince meat no heat
I cook with verbs blade lines slice deep street talk street walk
flip scripts crowns drop REIGN
```

**Single-Agent Output:**
```
Bow down nah watch how I flip scripts You spit paper flames
no heat just smoke Street talk but I'm street proof grown rules
Mince meat? I feast Check
```

**Analysis:**
- Both are valid battle rap responses
- Both reference opponent's bars appropriately
- Both maintain proper beat structure (15 beats)
- Quality is subjective but comparable

### Validation Results

**Two-Agent:**
- ✅ Lyricist validation: PASS
- ✅ Grid Builder validation: PASS
- ✅ Beat count: Correct (15 beats)
- ✅ Grid structure: Valid
- ✅ ms_per_beat: Correct
- ✅ Bar/beat numbering: Correct

**Single-Agent:**
- ✅ Unified validation: PASS
- ✅ Beat count: Correct (15 beats)
- ✅ Grid structure: Valid
- ✅ ms_per_beat: Correct
- ✅ Bar/beat numbering: Correct

---

## Performance Variability Analysis

### Why is Grid Builder So Slow?

The Grid Builder is doing simple formatting work (taking existing beats and creating a grid), yet it takes 60-65% of the total time. Possible reasons:

1. **Model overhead:** Even simple tasks have baseline API latency
2. **JSON parsing:** LLM needs to parse input JSON and generate output JSON
3. **Prompt length:** The prompt with embedded lyricist JSON is long
4. **Temperature=0:** Deterministic mode might be slower

### Why is Single-Agent Timing Variable?

The single-agent approach shows high variability (17s to 22s):

1. **Combined complexity:** Doing both tasks means more "thinking" time
2. **Reasoning model:** GPT-5-mini uses reasoning, which can vary
3. **Network latency:** Single longer call vs two shorter calls
4. **Token count:** Larger output to generate

---

## Recommendations

### Option 1: Keep Two-Agent (Recommended)

**Reasoning:**
- No proven performance benefit from single-agent
- Better error handling and debugging
- Easier to improve individual agents
- More maintainable architecture

### Option 2: Optimize Grid Builder

Since Grid Builder takes 60-65% of time for simple formatting:

1. **Increase temperature** (currently 0, could try 0.3)
2. **Simplify prompt** (it's very verbose)
3. **Use cheaper model** (grid building doesn't need gpt-5-mini)
4. **Consider rule-based formatting** (Python code instead of LLM)

### Option 3: Switch to Single-Agent

Only if:
- Further testing shows consistent 15%+ improvement
- Error recovery is not critical
- Debugging complexity is acceptable

---

## Next Steps

1. **Test with cheaper model for Grid Builder** (gpt-4o-mini instead of gpt-5-mini)
2. **Simplify Grid Builder prompt** (reduce token count)
3. **Run 10+ test iterations** to get statistical significance
4. **Test with real battles** (multi-turn scenarios)
5. **Measure token costs** (single-agent uses more tokens in prompt)

---

## Conclusion

**Current verdict:** Insufficient evidence to switch to single-agent approach.

- Performance gains are inconsistent (0-20%, average ~5%)
- Two-agent provides better error handling and maintainability
- Grid Builder optimization could provide similar speed gains without architectural changes

**Recommendation:** Focus on optimizing the Grid Builder agent rather than switching to single-agent architecture.
