+++
title = "What I needed to build a trading engine with AI"
date = 2026-05-20T13:00:00+09:00
draft = false
math = true
tags = ["trading-systems", "ai-native"]
summary = "I'm building a trading engine where AI writes the code. Here's what that took."
+++

I'm building a systematic trading engine, and the code is 100% written by AI.
It's a general CLOB-based engine. But I don't just want it built. I want AI to
extend it on its own and keep it running once it's live. If AI is going to
maintain and improve it anyway, I figure the code structure should be AI-built
from the start, too.

Once the system is built, here's the work I plan to keep giving AI:

- adding new exchanges
- watching for errors, reporting them, and filing tickets
- fixing those errors
- analyzing latency and reporting anything unusual

Adding exchanges and fixing errors happen when something comes up. The watching
and analysis need to run on a schedule.

## Cron jobs

The engine isn't finished yet, but once it is, I plan to run these as cron jobs:

- **Log Scanner**: scans the logs on a schedule. If something it didn't handle
  shows up, it files a ticket.
- **Venue Latency Watcher**: watches latency for each venue.
- **Exchange Spec Poller**: checks exchange API docs and reports any updates.
  This one is ad hoc enough that it probably isn't worth the cost.
- **Docs Auditor**: keeps the docs and the code in sync.

## Working with AI

All of it is a back-and-forth with Claude. The architecture we work through
directly, and the implementation detail goes through grill, one PR at a time.
Working that way, I found I needed a few things first.

### Type-driven design

Give AI too much freedom and it writes ad hoc code, so I let the type system
drive the design.
Unlike a standard protocol like FIX, most exchanges are each built differently,
and if you get the mapping wrong early, you usually end up with code you can't
reuse.

### TDD

On my own, I don't really use TDD. I write tests only where something needs
checking. But I couldn't keep up with how fast AI writes code, so reviewing it
became almost impossible. So I switched to a strict TDD-based workflow.

### Context Map

I split the engine into bounded contexts and defined a context map. Each context
defines its own vocabulary. It also lists the similar terms that are easy to mix
up, which keeps the code from fragmenting.

### Grill

Grill makes the AI ask hard questions about my plan before it starts working.
grill-me digs into the plan like an interview, and grill-with-docs checks it
against the domain docs.

There's too much to review, and I'm writing code faster than I can fully
understand it, so I have to rely on the PR plan and the tests. That's where
grill-me and grill-with-docs really helped. If you build with AI, I'd recommend
giving them a try.

Reference: [Matt Pocock's skills repo](https://github.com/mattpocock/skills)

## What's next

I'll write about the problems I worked through while building this engine.
