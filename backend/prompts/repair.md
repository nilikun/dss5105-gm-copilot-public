---
name: repair
version: 1
purpose: Sent back to the agent when the verifier rejects a reply (one repair attempt).
---
REJECTED by the verifier — the reply was not sent. Problems:
${violations}

Every number, date and id in the reply must appear in a tool result from this turn. Either call the tool that
produces the missing figure, or remove the unsupported figures and use only ones from the tool results.
Then call respond again.
