---
slug: the-eval-set-is-the-product
title: "The eval set is the product"
date: 2026-05-02
read: "6 min read"
excerpt: >-
  If you cannot say what "correct" means in numbers, you do not have an AI
  feature — you have a vibe that occasionally embarrasses you.
---

On the clinical summarisation engine, the artefact that took the longest was not the pipeline. It was twelve hundred de-identified charts scored by clinicians, with disagreements adjudicated and documented. That set is why the feature shipped into a regulated environment at all.

An eval set does three things a demo cannot. It converts taste into a number you can regress against in CI. It makes model swaps a measurement rather than an argument. And it gives the people who must sign off — compliance, clinical safety, legal — something to inspect other than your confidence.

Building one is unglamorous. Sample from real data, including the ugly tail. Get domain experts to score, not engineers. Write down the rubric, then check inter-rater agreement before you trust any of it. Version it, because the definition of correct will move as the product does.

The payoff is that improvement stops being anecdotal. When we routed cheaper models for the easy 70% of cases, we could show the quality change was inside noise. Without the set, that decision would have taken a month of meetings and shipped anyway on a hunch.

If a project has no budget for evaluation, that is useful information about how seriously the outcome is taken. I now scope the eval set as a deliverable in week two, before any model work, and I have never regretted the sequencing.
