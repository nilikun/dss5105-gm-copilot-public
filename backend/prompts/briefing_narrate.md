---
name: briefing_narrate
version: 1
purpose: Turns the structured morning briefing into a short paragraph. Facts come only from the JSON.
---
Write the general manager's morning briefing for ${date} as 3 to 5 short sentences of plain English.
Order: what happened yesterday, what is at risk, what needs a decision today. Lead with the most important item.
Use ONLY facts and numbers that appear in the JSON below — do not compute, round differently, or add anything.
Do not mention scores, tiers, evidence ids or tool names.

${structured}
