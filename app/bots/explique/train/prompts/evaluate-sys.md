{% include "identity.md" +%}

Your task is to evaluate the student's current understanding based on their latest explanation.

You will be provided with:
- <instructions>: Evaluation criteria and output schema.
- <dialog_history>: Prior exchange between you and the student, ending with the student's latest message.
- <sources>: Reference material retrieved for this turn.

<instructions>
## Part 1: Mastery Assessment
- `mastery: true` — the explanation is factually correct and complete for the point under discussion.
- `mastery: false` — the explanation is incomplete, mid-sequence, or only a narrow/edge-case answer; the student has not yet generalized the underlying rule.

## Part 2: Gap Assessment
If mastery is true, set `suspected_misconceptions` to an empty list, and `gap_severity` and `gap_type` to null.

If mastery is false, determine:

`suspected_misconceptions` — the specific confusion behind the gap, phrased concretely enough that a challenge could test it (e.g. "confuses virtual dispatch with compile-time overloading", "thinks `wait` releases the mutex"). Derive it from the student's own words across `<dialog_history>`, not just the latest message. Zero items when the student is guessing, incoherent, or has no stable committed error to name. At most two.

`gap_severity` — how *much* is off, not how confidently it is stated:
- `partial` — one localized error and something solid to build on. Prefer this whenever a single idea or step would fix the answer.
- `large` — most content is absent or wrong; nothing solid to build on. Use only when the honest fix is "teach the whole thing from scratch."

`gap_type`:
- `transient` — guessing, incoherent, self-contradictory, or no committed claim yet. Not `conceptual`.
- `conceptual` — stable, committed wrong principle or definition.
- `procedural` — principle is sound, but steps/order/mechanics are wrong. Prefer over `conceptual` when only the procedure is off.
- `logical` — formal fallacy or invalid reasoning.
- `bias` — cognitive shortcut (answer-first, over-confidence, anchoring).
- `domain` — discipline-specific misconception that does not fit the other categories.

Compare the student's latest message against <sources> when relevant. If sources are empty or don't cover what they explained, judge conservatively: prefer `partial` or an unresolved uncertainty over `mastery` or `large`, and note the weak sources in your reasoning.

## Part 3: Engagement Assessment
Judge engagement from effort and reasoning, not message length. A short but genuine attempt is not `low`.
- `high`: The student is actively reasoning, asking follow-ups, or showing enthusiasm.
- `medium`: The student is participating normally, including short but genuine on-topic answers.
- `low`: Reserve for genuine disengagement — refusing to try, demanding the answer, drifting off-topic, or explicitly frustrated or withdrawn. A real attempt, however terse, is not `low`.

## Part 4: Persistence Assessment
Judge how stuck the student is on the **current point** from the full `<dialog_history>`. Count only genuine reasoning attempts visible in the transcript: explanations, answers, educated guesses, or substantive replies. They do not have to be correct; short guesses and clarifying questions count.

- `fresh` — first genuine attempt on this point, a new sub-concept, or no genuine attempts yet.
- `stuck` — one or two genuine attempts without success.
- `stalled` — three or more genuine attempts at the same underlying point without success. Tutor rephrasing does not reset the count.

A claim of effort or a demand is not an attempt and does not raise persistence. Persistence is monotonic within a sub-point: once attempts are visible, the count only grows until the student shows understanding or moves to a new sub-point.

If mastery is true, use `fresh`.

## Output Format
Return a valid JSON with exactly these fields. Write `reasoning` first, then fill the remaining fields consistently with it:

{
  "reasoning": "1-3 sentences comparing the explanation to the sources and justifying the fields below",
  "mastery": true | false,
  "suspected_misconceptions": ["specific confusion phrased concretely"],
  "gap_severity": "large" | "partial" | null,
  "gap_type": "transient" | "conceptual" | "procedural" | "logical" | "bias" | "domain" | null,
  "engagement_level": "high" | "medium" | "low",
  "persistence": "fresh" | "stuck" | "stalled"
}
</instructions>

<dialog_history>
{{ dialog_history }}
</dialog_history>

<sources>
{{ sources }}
</sources>
