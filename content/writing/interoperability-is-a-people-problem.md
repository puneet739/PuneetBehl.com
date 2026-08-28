---
slug: interoperability-is-a-people-problem
title: "FHIR is fine. Interoperability is a people problem"
date: 2026-03-18
read: "7 min read"
excerpt: >-
  Connecting to Cerner, CommonWell and CareQuality taught me that the standard
  was rarely the obstacle.
---

HL7 FHIR is a reasonable standard. SMART on FHIR is a reasonable authorisation model. Neither explains why an integration that should take three weeks takes seven months.

The delays came from elsewhere: which organisation is the record custodian, what the data-sharing agreement permits, whose privacy officer must approve a field, and what happens when two source systems disagree about a patient's allergy list. These are governance questions wearing technical clothes.

The engineering response that worked was to make disagreement visible instead of resolving it silently. When three systems assert different problem lists, the interface shows provenance and lets the clinician decide. Reconciling in code would have been faster to build and impossible to defend.

The other lesson is sequencing. We spent the first month writing the data-flow document that compliance, product and the partner's team could all mark up. It felt slow. It removed almost every late surprise, and provider adoption went up 23% once the integrations landed because clinicians trusted what they saw.

If you are starting one of these: budget half your timeline for the conversations, name a single accountable owner on each side, and write down every mapping decision with the reason. Six months later the reason is the only part anyone needs.
