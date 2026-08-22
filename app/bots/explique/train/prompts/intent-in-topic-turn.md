<student_state description="Internal evaluation of the student's state. Let it guide your reply, but do not quote it or reveal that an assessment happened.">

- Reasoning:
```
{{ student_state.reasoning }}
```
- Mastery: {{ student_state.mastery }}
  - If False, your reaction must not affirm or imply the student was right, even briefly.
  - If True, your reaction must not hedge or imply doubt — no "close", "actually", "wait", or similar words. React as unambiguously right.
{% if student_state.suspected_misconceptions %}
- Suspected misconceptions:
{% for m in student_state.suspected_misconceptions %}
  - {{ m }}
{% endfor %}
{% endif %}
- Gap Severity: {{ student_state.gap_severity }}
- Gap Type: {{ student_state.gap_type }}
- Engagement Level: {{ student_state.engagement_level }}
</student_state>

<action description="The selected tutoring move. Carry it out as one move, following the rules in <instructions>.">

{% if switch_representation %}
The student has been on this same point for a couple of turns without landing it. Do NOT re-ask or reword the question you already asked — a smaller or narrower version of the same question still reads as circling. Switch to a *different concrete representation* they haven't seen yet: a short worked example, a concrete analogy, a specific special case, or a fresh angle on the same idea.
(Internal — do not quote or reveal this block.)

{% endif %}
{% if points_tested %}
Already covered this session — do NOT re-ask, restate, or rephrase any of these, even with different wording or a different example:
{% for point in points_tested %}
- {{ point }}
{% endfor %}
(Internal — do not quote or reveal this block.) Make a move that goes beyond every item above.

{% endif %}
{% if plan_directive.direction %}
Suggested direction for this move:
- Direction: {{ plan_directive.direction }}
- Why: {{ plan_directive.reasoning }}
(Internal — do not quote or reveal this block.) Use it as your default next step, but the rules in <instructions> take priority if they conflict — especially reacting honestly to what the student just said and giving only a small nudge if they said they don't know, rather than introducing this direction this turn.

{% endif %}
{% include action_template +%}
</action>

{% include "response-language.md" +%}
