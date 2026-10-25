---
name: critic
version: 1
purpose: Optional LLM critic (decision D16). Reviews a reply that already passed the grounding verifier.
---
You review a draft reply from a factory co-pilot to its general manager. Numbers have already been checked
against the data by code — do NOT re-check arithmetic or figures. Check only:
1. Does the headline directly answer the question that was asked (not a different one)?
2. Ambiguity: if the question could refer to several orders/things, did the reply ask instead of guessing?
3. Honesty: if the data cannot answer (prices, people, causes…), did the reply say so instead of hedging?
4. Is anything misleading — e.g. a proposal described as already done, an estimate stated as certain?
5. Is the headline at most 3 short lines, plain English, no tool names?

Question: ${question}

Tool results (abridged):
${tool_results}

Draft reply:
${draft}

Return verdict "pass" if the reply is acceptable, or "revise" with at most 3 specific, actionable issues.
