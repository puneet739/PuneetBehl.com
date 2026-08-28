---
slug: agents-are-distributed-systems
title: "Your agent is a distributed system wearing a prompt"
date: 2026-08-12
read: "8 min read"
excerpt: >-
  Every hard problem teams hit with agents in production is a problem
  distributed systems solved twenty years ago — and mostly forgot to tell the
  AI crowd about.
---

The demo works because the demo runs in one process, on one machine, with one user, and finishes in eight seconds. Production is none of those things. The moment a run waits on a human, calls a vendor API that times out, or spans a deploy, you are no longer prompting a model — you are operating a long-lived, partially-failed, concurrent workflow.

Which means the useful questions stop being about prompts. What is the unit of work, and is it idempotent? If a tool call succeeds but the response is lost, does a retry double-charge the customer? When step four of seven fails, what compensates for steps one to three? Who owns the state between steps, and does it survive a rolling restart?

The industry has answers to all of these. Idempotency keys, transactional outbox, saga compensation, durable execution, at-least-once delivery with exactly-once effects. None of it is new. The mistake is treating an agent framework as a substitute for that architecture instead of a layer on top of it.

Practically, this changes what I build first on an agentic engagement. Not the prompt. The state machine, the tool contracts with timeouts and compensations, and the trace that lets someone answer "what did run 4a91 actually do" six weeks later. The prompt is the easiest thing to change afterwards; the execution model is the hardest.

One test I use before anything ships: kill a worker mid-run, deliberately, in staging. If the run resumes and the side effects stay correct, the architecture is real. If it needs a human to clean up, you have a demo with a bigger bill.
