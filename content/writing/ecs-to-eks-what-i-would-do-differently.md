---
slug: ecs-to-eks-what-i-would-do-differently
title: "ECS to EKS: what I would do differently"
date: 2026-06-26
read: "11 min read"
excerpt: >-
  A migration that carried 50M requests a day without an outage, and the four
  decisions I would reverse if I ran it again.
---

We moved a production healthcare platform from ECS to EKS over several months without a customer-visible outage. That is the headline. The more useful content is the parts I got wrong and paid for later.

First: I let teams bring their own Helm charts. It felt respectful of autonomy and it produced nine incompatible ways to express the same Deployment. A single generated chart with a small values contract would have cost two weeks up front and saved months of drift.

Second: resource requests were set from staging observations, which meant they were wrong for every service under real load. Requests without load-shaped data are guesses, and guesses in Kubernetes become either evictions or a bill.

Third: we migrated services in dependency order, which sounds obviously right and left the noisiest, least-understood service for last — the point at which everyone had lost patience. Migrating one high-traffic service early, deliberately, buys you the operational knowledge you actually need.

Fourth, and the one I would change first: we treated observability as a follow-up. Traces, cluster-level dashboards and per-namespace cost attribution should exist before the first workload moves, because every argument during a migration is a question about numbers nobody has.

What I would keep: dual-running with shadow traffic comparison, a hard rule that rollback stays one command away for two weeks after each cut, and a weekly written update to the whole organisation. The technical work was not the hard part. Keeping four hundred people confident during six months of change was.
