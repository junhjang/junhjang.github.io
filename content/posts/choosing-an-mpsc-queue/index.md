+++
title = "Choosing an MPSC Queue for a Centralized Trading Engine"
date = 2026-05-24T13:00:00+09:00
draft = false
tags = ["trading-systems", "concurrency", "rust", "lock-free"]
summary = "I needed to pick an MPSC queue for a trading engine's contended hot path. Here's the benchmark across four candidates."
+++

<!--
  Hugo: needs markup.goldmark.renderer.unsafe = true in config (for raw HTML rendering).
-->

<style>
.diag { margin: 28px 0; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 13px; color: #1e293b; }
.diag-row { display: flex; align-items: center; justify-content: center; gap: 14px; flex-wrap: wrap; }
.diag-col { display: flex; flex-direction: column; gap: 6px; }
.diag-box { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 6px; background: #ffffff; text-align: center; min-width: 110px; }
.diag-box-emph { padding: 22px 18px; border: 1.5px solid #1e293b; border-radius: 6px; background: #f8fafc; text-align: center; font-weight: 600; min-width: 130px; }
.diag-arr { text-align: center; color: #64748b; min-width: 90px; }
.diag-arr .a { font-size: 20px; line-height: 1; }
.diag-arr .lbl { font-size: 11px; margin-top: 4px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color: #475569; }
.diag-arr-pair { text-align: center; }
.diag-engine { border: 1.5px dashed #94a3b8; border-radius: 8px; padding: 22px 18px 16px; position: relative; background: rgba(248, 250, 252, 0.4); }
.diag-engine-label { position: absolute; top: -10px; left: 18px; background: #ffffff; padding: 0 8px; font-size: 11px; color: #475569; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-weight: 500; }
.diag-engine-inner { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; justify-content: center; }
.tbl-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 18px 0; }
.tbl-scroll table { white-space: nowrap; margin: 0; }
.diag { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.svg-scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; margin: 24px 0; }
.tbl-scroll::-webkit-scrollbar, .diag-panel::-webkit-scrollbar, .diag::-webkit-scrollbar, .svg-scroll::-webkit-scrollbar { height: 8px; }
.tbl-scroll::-webkit-scrollbar-track, .diag-panel::-webkit-scrollbar-track, .diag::-webkit-scrollbar-track, .svg-scroll::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 4px; }
.tbl-scroll::-webkit-scrollbar-thumb, .diag-panel::-webkit-scrollbar-thumb, .diag::-webkit-scrollbar-thumb, .svg-scroll::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 4px; }
.tbl-scroll, .diag-panel, .diag, .svg-scroll { scrollbar-width: thin; scrollbar-color: #94a3b8 #f1f5f9; }
/* CSS scroll-shadow: edge gradient hints that content is swipe-able. Works on mobile WebKit where scrollbars are hidden. */
.tbl-scroll, .diag, .diag-panel, .svg-scroll {
  background-color: #ffffff;
  background-image:
    linear-gradient(to right, #ffffff 30%, rgba(255,255,255,0)),
    linear-gradient(to left, #ffffff 30%, rgba(255,255,255,0)),
    radial-gradient(farthest-side at 0% 50%, rgba(71,85,105,0.45), rgba(0,0,0,0)),
    radial-gradient(farthest-side at 100% 50%, rgba(71,85,105,0.45), rgba(0,0,0,0));
  background-position: left center, right center, left center, right center;
  background-repeat: no-repeat;
  background-size: 30px 100%, 30px 100%, 14px 100%, 14px 100%;
  background-attachment: local, local, scroll, scroll;
}
.diag-dots { text-align: center; color: #94a3b8; padding: 2px 0; }
.diag-grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.diag-panel { border: 1px solid #cbd5e1; border-radius: 8px; padding: 18px; background: #ffffff; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.diag-panel-title { font-weight: 600; font-size: 13px; margin-bottom: 4px; }
.diag-panel-sub { font-size: 11px; color: #64748b; margin-bottom: 16px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.diag-mini { padding: 4px 8px; border: 1px solid #cbd5e1; border-radius: 3px; background: #fff; font-family: ui-monospace, monospace; font-size: 11px; text-align: center; min-width: 22px; }
.diag-cell-filled { padding: 4px 8px; border: 1px solid #64748b; border-radius: 3px; background: #e2e8f0; font-family: ui-monospace, monospace; font-size: 11px; min-width: 14px; text-align: center; }
.diag-cell-empty { padding: 4px 8px; border: 1px dashed #cbd5e1; border-radius: 3px; background: #fff; font-family: ui-monospace, monospace; font-size: 11px; min-width: 14px; text-align: center; color: #cbd5e1; }
.diag-arr-sm { color: #94a3b8; font-size: 12px; }
.diag-note { padding: 10px 14px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; text-align: center; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 13px; }
.diag-note-warn { background: #fef3c7; border-color: #d97706; color: #92400e; }
.diag-scenario { margin: 16px 0; padding: 14px 16px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; }
.diag-scenario-label { font-size: 11px; color: #64748b; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin-bottom: 10px; text-align: center; }
.diag-scenario-row { display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; }
.diag-scenario-caption { font-size: 12px; color: #475569; margin-top: 12px; text-align: center; line-height: 1.55; }
.diag-steps { margin: 18px auto; max-width: 440px; }
.diag-step { display: flex; align-items: center; gap: 12px; padding: 10px 14px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 13px; color: #1e293b; }
.diag-step-num { width: 24px; height: 24px; border-radius: 50%; background: #1e293b; color: #ffffff; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; flex-shrink: 0; font-family: ui-sans-serif, system-ui, sans-serif; }
.diag-step-arr { text-align: center; color: #94a3b8; padding: 3px 0; font-size: 14px; line-height: 1; }
.timeline { background: #fff; border: 1px solid #d0d3d8; border-radius: 8px; padding: 18px 20px; margin: 18px 0; }
.t-node { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
.t-num { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 50%; background: #1a1a1a; color: #fff; font-weight: 700; font-size: 12px; flex: none; font-family: ui-monospace, monospace; }
.t-name { font-family: ui-monospace, monospace; font-weight: 700; font-size: 13px; }
.t-who { color: #888; font-size: 12px; }
.t-seg { margin: 4px 0 4px 14px; padding: 7px 14px; border-left: 3px solid #ccc; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.t-sname { font-family: ui-monospace, monospace; font-weight: 700; font-size: 12.5px; min-width: 188px; }
.t-cat { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 4px; }
.t-tech { border-left-color: #e0533d; background: #fdf0ee; }
.t-tech .t-cat { background: #e0533d; color: #fff; }
.t-engine { border-left-color: #9db8e8; background: #eef4ff; }
.t-engine .t-cat { background: #9db8e8; color: #1a2d4f; }
.t-venue { border-left-color: #b3b3b3; background: #f1f1f1; }
.t-venue .t-cat { background: #b3b3b3; color: #fff; }
.t-spsc { border-left-color: #94a3b8; background: #f8fafc; }
.t-spsc .t-cat { background: #94a3b8; color: #fff; }
.t-total { margin-top: 12px; padding: 10px 14px; background: #fff7e6; border: 1px solid #e8b84b; border-radius: 6px; font-size: 13px; }
.t-total b { color: #b07400; }

/* ----- mobile ----- */
@media (max-width: 640px) {
  .diag-row { flex-direction: column; gap: 8px; }
  .diag-arr { display: flex; flex-direction: row; gap: 28px; justify-content: center; align-items: flex-start; min-width: auto; margin: 6px 0; }
  .diag-arr-pair { margin-top: 0 !important; }
  .diag-arr .a { display: inline-block; transform: rotate(90deg); }
  .diag-engine-inner { flex-direction: column; }
  .diag-grid-2 { grid-template-columns: 1fr; }
  .diag-panel { padding: 14px; }
  .diag-box, .diag-box-emph { min-width: auto; }
  .diag-scenario { padding: 12px 14px; }
  .diag-scenario-row { gap: 6px; }
  .tbl-scroll table { white-space: nowrap; font-size: 11px; }
  .tbl-scroll th, .tbl-scroll td { padding: 5px 8px; }
  /* stack panel content vertically on mobile so nothing gets cut off */
  .diag-panel > div:not(.diag-panel-sub):not(.diag-panel-title) {
    flex-direction: column;
    align-items: center;
    gap: 8px;
    justify-content: center;
  }
  /* rotate ONLY direct-child arrows (not arrows inside nested rows like linked-list nodes) */
  .diag-panel > div > .diag-arr-sm { transform: rotate(90deg); display: inline-block; }
  /* turn P column horizontal only when it directly holds P1/P2/P3 minis (not ④ which holds nested rows) */
  .diag-panel .diag-col:has(> .diag-mini) { flex-direction: row; gap: 4px; }
}
</style>


I started this trading engine with three constraints in mind:

- A centralized engine
- Supports multiple strategies
- Low latency

<div style="margin: 24px 0; padding: 14px 18px; background: #f8fafc; border-left: 3px solid #2563eb; border-radius: 4px; font-size: 13px; line-height: 1.7;">
  <strong>Benchmark code repo</strong>: <a href="https://github.com/junhjang/nonblocking-dispatch-bench" style="font-family:ui-monospace,monospace;">github.com/junhjang/nonblocking-dispatch-bench</a>
</div>

Strategies run as separate processes so they stay isolated and observable. Each venue gateway also runs on its own thread, so a slow or broken venue does not block other venues.

<div class="svg-scroll">
<svg viewBox="0 0 900 220" xmlns="http://www.w3.org/2000/svg" style="display:block; margin:0 auto; width:900px; max-width:none; height:220px;" font-family="ui-sans-serif, system-ui, sans-serif">
  <defs>
    <marker id="arch-ar-r" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 Z" fill="#dc2626"/>
    </marker>
    <marker id="arch-ar-g" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 Z" fill="#94a3b8"/>
    </marker>
  </defs>
  <rect x="30" y="60" width="180" height="120" rx="8" fill="#d1fae5" stroke="#10b981" stroke-width="1" opacity="0.35"/>
  <rect x="20" y="50" width="180" height="120" rx="8" fill="#d1fae5" stroke="#10b981" stroke-width="1" opacity="0.6"/>
  <rect x="10" y="40" width="180" height="120" rx="8" fill="#ecfdf5" stroke="#10b981" stroke-width="2"/>
  <text x="100" y="95" text-anchor="middle" font-weight="700" font-size="22" fill="#065f46">strategy</text>
  <text x="100" y="125" text-anchor="middle" font-size="14" fill="#047857">× N</text>
  <rect x="350" y="40" width="200" height="120" rx="8" fill="#dbeafe" stroke="#3b82f6" stroke-width="2"/>
  <text x="450" y="95" text-anchor="middle" font-weight="700" font-size="22" fill="#1e40af">orchestrator</text>
  <text x="450" y="125" text-anchor="middle" font-size="14" fill="#2563eb">× 1</text>
  <rect x="730" y="60" width="160" height="120" rx="8" fill="#e2e8f0" stroke="#475569" stroke-width="1" opacity="0.35"/>
  <rect x="720" y="50" width="160" height="120" rx="8" fill="#e2e8f0" stroke="#475569" stroke-width="1" opacity="0.6"/>
  <rect x="710" y="40" width="160" height="120" rx="8" fill="#f8fafc" stroke="#475569" stroke-width="2"/>
  <text x="790" y="95" text-anchor="middle" font-weight="700" font-size="22" fill="#1e293b">gateway</text>
  <text x="790" y="125" text-anchor="middle" font-size="14" fill="#475569">× M</text>
  <line x1="195" y1="80" x2="348" y2="80" stroke="#dc2626" stroke-width="2" marker-end="url(#arch-ar-r)"/>
  <text x="270" y="68" text-anchor="middle" font-size="12" fill="#dc2626" font-weight="600">submit_q · N→1</text>
  <line x1="555" y1="80" x2="708" y2="80" stroke="#94a3b8" stroke-width="2" marker-end="url(#arch-ar-g)"/>
  <text x="630" y="68" text-anchor="middle" font-size="12" fill="#475569">gateway_inbox · 1→M</text>
  <line x1="708" y1="140" x2="555" y2="140" stroke="#dc2626" stroke-width="2" marker-end="url(#arch-ar-r)"/>
  <text x="630" y="160" text-anchor="middle" font-size="12" fill="#dc2626" font-weight="600">completion_q · M→1</text>
  <line x1="348" y1="140" x2="195" y2="140" stroke="#94a3b8" stroke-width="2" marker-end="url(#arch-ar-g)"/>
  <text x="270" y="160" text-anchor="middle" font-size="12" fill="#475569">return_q · 1→N</text>
  <g font-family="ui-monospace, monospace" font-weight="700" font-size="11">
    <circle cx="220" cy="80" r="11" fill="#1a1a1a"/><text x="220" y="84" text-anchor="middle" fill="#fff">t1</text>
    <circle cx="328" cy="80" r="11" fill="#1a1a1a"/><text x="328" y="84" text-anchor="middle" fill="#fff">t2</text>
    <circle cx="580" cy="80" r="11" fill="#1a1a1a"/><text x="580" y="84" text-anchor="middle" fill="#fff">t3</text>
    <circle cx="688" cy="80" r="11" fill="#1a1a1a"/><text x="688" y="84" text-anchor="middle" fill="#fff">t4</text>
    <circle cx="688" cy="140" r="11" fill="#1a1a1a"/><text x="688" y="144" text-anchor="middle" fill="#fff">t5</text>
    <circle cx="580" cy="140" r="11" fill="#1a1a1a"/><text x="580" y="144" text-anchor="middle" fill="#fff">t6</text>
    <circle cx="328" cy="140" r="11" fill="#1a1a1a"/><text x="328" y="144" text-anchor="middle" fill="#fff">t7</text>
    <circle cx="220" cy="140" r="11" fill="#1a1a1a"/><text x="220" y="144" text-anchor="middle" fill="#fff">t8</text>
  </g>
</svg>
</div>

The Order Engine, simplified, has two layers: Orchestrator and Gateway. The real engine has more layers, but by role they group into these two.
A gateway is created per (Venue, Credential). The Orchestrator is the central event loop every order passes through. Risk check, position tracking, and kill switch all sit in one place, and observability also ends there.

Strategies are isolated as processes. The Orchestrator and Gateways are threads in the same process, pinned to cores.

Following the pipeline, there are four hand-off points:

- `submit_q` (strategy → orchestrator): N → 1, **MPSC**
- `gateway_inbox` (orchestrator → gateway X): 1 → 1, **SPSC**. One per gateway (M total)
- `completion_q` (gateway → orchestrator): M → 1, **MPSC**
- `return_q` (orchestrator → strategy Y): 1 → 1, **SPSC**. One per strategy (N total)

Contention happens at #1 and #3, the two MPSC spots. These are what this benchmark measures.


## 1. Non-blocking candidates

I picked 4 candidates. They are the common choices for MPSC hand-off in Rust.

<div class="tbl-scroll"><table>
<thead><tr><th>Candidate</th><th>Structure</th><th>lock-free?</th><th>bounded?</th></tr></thead>
<tbody>
<tr><td>① std::sync::mpsc</td><td>linked list, MPSC</td><td><strong>both</strong></td><td>unbounded</td></tr>
<tr><td>② crossbeam-channel</td><td>array ring, MPMC</td><td><strong>both</strong></td><td>bounded</td></tr>
<tr><td>③ ArrayQueue</td><td>array ring, MPMC</td><td>YES</td><td>bounded</td></tr>
<tr><td>④ per-producer SPSC + mux</td><td>N SPSC rings</td><td>YES</td><td>bounded</td></tr>
</tbody>
</table></div>

<div style="margin:18px 0; padding:14px 18px; background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; font-size:13px; line-height:1.7;">
  <div style="font-weight:600; margin-bottom:8px;">Terms you will see often</div>
  <ul style="margin:0; padding-left:20px;">
    <li><strong>lock-free</strong>: many threads can touch the same data structure at once without locks, safely. Done with atomic ops.</li>
    <li><strong>atomic op</strong>: an op that cannot be cut in the middle. The CPU handles it in one shot.</li>
    <li><strong>CAS (Compare-And-Swap)</strong>: an atomic op that says "if memory holds X, change it to Y". If many threads try at once, only <em>one</em> wins; the rest see the failure.</li>
    <li><strong>park</strong>: the OS putting a thread to sleep. The thread uses no CPU time and waits to be woken up.</li>
    <li><strong>ring</strong>: a fixed-size array that wraps back to the start when it reaches the end. Marked as <code>↺</code> in the tables and figures.</li>
    <li><strong>both</strong> (in the table): supports a lock-free call (fails fast) and a blocking call (parks until a slot opens). <code>YES</code> means lock-free only.</li>
  </ul>
</div>

### ① std::sync::mpsc

<div class="diag-panel" style="max-width:540px; margin:14px auto;">
  <div class="diag-panel-sub">linked nodes (heap-allocated), unbounded</div>
  <div style="display:flex; align-items:center; gap:8px; justify-content:center;">
    <div class="diag-col" style="gap:4px;">
      <div class="diag-mini">P1</div>
      <div class="diag-mini">P2</div>
      <div class="diag-mini">P3</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div style="display:flex; align-items:center; gap:3px;">
      <div class="diag-cell-filled" style="border-radius:50%; width:18px; height:18px; padding:0; display:flex; align-items:center; justify-content:center;">●</div>
      <span class="diag-arr-sm">→</span>
      <div class="diag-cell-filled" style="border-radius:50%; width:18px; height:18px; padding:0; display:flex; align-items:center; justify-content:center;">●</div>
      <span class="diag-arr-sm">→</span>
      <div class="diag-cell-filled" style="border-radius:50%; width:18px; height:18px; padding:0; display:flex; align-items:center; justify-content:center;">●</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div class="diag-mini">C</div>
  </div>
</div>

- **Pros**: Rust standard library (no external crate), unbounded (push is never refused)
- **Cons (latency)**: allocates per block (not per push, but still a cost); pop chases pointers across the heap and hits cache misses

<div class="diag-steps">
  <div class="diag-step"><div class="diag-step-num">1</div><div>P calls <code>push</code></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">2</div><div>alloc new node from heap <span style="color:#94a3b8;">(per-block, amortized)</span></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">3</div><div>atomic link to list tail (CAS)</div></div>
</div>


### ② crossbeam-channel

<div class="diag-panel" style="max-width:540px; margin:14px auto;">
  <div class="diag-panel-sub">bounded ring <em>inside</em> channel wrapper</div>
  <div style="display:flex; align-items:center; gap:8px; justify-content:center;">
    <div class="diag-col" style="gap:4px;">
      <div class="diag-mini">P1</div>
      <div class="diag-mini">P2</div>
      <div class="diag-mini">P3</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div style="border:1.5px dashed #d97706; border-radius:6px; padding:8px 10px; background:#fef3c7;">
      <div style="font-size:9px; color:#92400e; text-align:center; margin-bottom:5px; font-family:ui-monospace,monospace;">channel wrapper</div>
      <div style="display:flex; align-items:center; gap:1px;">
        <div class="diag-cell-empty">·</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-empty">·</div>
        <div class="diag-cell-empty">·</div>
        <span style="color:#92400e; font-size:11px; margin-left:3px;">↺</span>
      </div>
      <div style="font-size:9px; color:#92400e; text-align:center; margin-top:5px; font-family:ui-monospace,monospace;">+ park / select / timeout</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div class="diag-mini">C</div>
  </div>
</div>

- **Pros**: supports blocking, select, and timeout. The inner ring is the same algorithm family as ③
- **Cons (latency)**: this bench uses only non-blocking push, but every call still goes through the wrapper machinery (notify, etc). You pay for features you do not use

<div class="diag-steps">
  <div class="diag-step"><div class="diag-step-num">1</div><div>P calls <code>push</code></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">2</div><div>CAS on ring tail (claim slot + write value)</div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">3</div><div>wrapper notify machinery <span style="color:#94a3b8;">(check sleeping receivers, unused but always traversed)</span></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">4</div><div>return Ok or <code>Err(Full)</code></div></div>
</div>


### ③ crossbeam_queue::ArrayQueue

<div class="diag-panel" style="max-width:540px; margin:14px auto;">
  <div class="diag-panel-sub">bare bounded ring (same shape, no wrapper)</div>
  <div style="display:flex; align-items:center; gap:8px; justify-content:center;">
    <div class="diag-col" style="gap:4px;">
      <div class="diag-mini">P1</div>
      <div class="diag-mini">P2</div>
      <div class="diag-mini">P3</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div style="display:flex; flex-direction:column; align-items:center; gap:5px;">
      <div style="display:flex; align-items:center; gap:1px;">
        <div class="diag-cell-empty">·</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-filled">●</div>
        <div class="diag-cell-empty">·</div>
        <div class="diag-cell-empty">·</div>
        <span style="color:#94a3b8; font-size:11px; margin-left:3px;">↺</span>
      </div>
      <div style="font-size:10px; color:#16a34a; font-family:ui-monospace,monospace;">CAS only, no park</div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div class="diag-mini">C</div>
  </div>
</div>

- **Pros (latency)**: one call = one CAS. No wrapper, so push/pop cost is minimal
- **Cons**: no blocking call. The caller has to handle backpressure

<div class="diag-steps">
  <div class="diag-step"><div class="diag-step-num">1</div><div>P calls <code>push</code></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">2</div><div>CAS on ring tail (claim slot + write value)</div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">3</div><div>return Ok or <code>Err(Full)</code></div></div>
</div>


### ④ per-producer SPSC + mux

<div class="diag-panel" style="max-width:540px; margin:14px auto;">
  <div class="diag-panel-sub">N bounded SPSC rings, consumer scans all</div>
  <div style="display:flex; align-items:center; gap:8px; justify-content:center;">
    <div class="diag-col" style="gap:6px;">
      <div style="display:flex; align-items:center; gap:4px;">
        <div class="diag-mini">P1</div>
        <span class="diag-arr-sm">→</span>
        <div class="diag-cell-filled" style="min-width:48px;">ring 1</div>
      </div>
      <div style="display:flex; align-items:center; gap:4px;">
        <div class="diag-mini">P2</div>
        <span class="diag-arr-sm">→</span>
        <div class="diag-cell-filled" style="min-width:48px;">ring 2</div>
      </div>
      <div style="display:flex; align-items:center; gap:4px;">
        <div class="diag-mini">P3</div>
        <span class="diag-arr-sm">→</span>
        <div class="diag-cell-filled" style="min-width:48px;">ring 3</div>
      </div>
    </div>
    <span class="diag-arr-sm">→</span>
    <div class="diag-mini" style="min-width:64px;">C scans N</div>
  </div>
</div>

- **Pros (latency)**: producers never touch the same atomic, so push contention is zero and latency is stable
- **Cons (latency)**: the consumer has to scan N queues each loop, so pop latency grows with N

<div class="diag-steps">
  <div class="diag-step"><div class="diag-step-num">1</div><div>each P does atomic store to <em>own</em> ring tail <span style="color:#94a3b8;">(no CAS needed, SPSC)</span></div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">2</div><div>isolated from other producers' atomics, so push contention is zero</div></div>
  <div class="diag-step-arr">↓</div>
  <div class="diag-step"><div class="diag-step-num">3</div><div>consumer peeks N rings sequentially (round-robin)</div></div>
</div>


## 2. Experiment setup

The bench mimics a real trading setup but does not talk to a real exchange. Each venue is **abstracted as a single delay D**. When an order arrives at a gateway, it is held for `D ~ Uniform(5ms, 500ms)` and then returned. This rolls the network and matching-engine round trip into one distribution.

To compare all 4 methods on the same input, I **pre-sampled** (per-strategy fire times + per-venue delays) once at the start and replayed it 4 times. Same effect as fixing the seed.

**Setup**: N (strategy) = 8, M (gateway) = 4, queue capacity = 8192, orders / run = 4M (= N × 500K), fire window = 10 s, `D ~ U(5ms, 500ms)`, W sweep = 0 / 500 / 1000 / 1500 ns, repeats R = 5.

<div class="diag" style="text-align:center;">
  <div style="display:inline-block; padding:14px 22px; border:1px solid #cbd5e1; border-radius:6px; background:#fff;">
    <div style="font-weight:600;">pre-sampled schedule</div>
    <div style="font-size:11px; color:#64748b; margin-top:4px; font-family:ui-monospace,monospace;">[ (fire_ts, strategy, venue, D), ... ]</div>
  </div>
  <div style="margin:10px 0; color:#94a3b8;">↓ replayed identically</div>
  <div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap;">
    <div class="diag-box" style="min-width:130px;">run 1<br><span style="font-size:11px; color:#64748b;">std::sync::mpsc</span></div>
    <div class="diag-box" style="min-width:130px;">run 2<br><span style="font-size:11px; color:#64748b;">crossbeam-channel</span></div>
    <div class="diag-box" style="min-width:130px;">run 3<br><span style="font-size:11px; color:#64748b;">ArrayQueue</span></div>
    <div class="diag-box" style="min-width:130px;">run 4<br><span style="font-size:11px; color:#64748b;">SPSC + mux</span></div>
  </div>
  <div style="margin-top:10px; font-size:11px; color:#64748b;">repeated R times (R = 5), reported as median</div>
</div>

All three thread types run sync code, busy-polling. The structure is almost the same: pop from input queue, do work, push to output queue.

Gateway has one difference. When an order arrives, it sets `release_at = now + D` and puts it in a **min-heap**. Each loop, if the heap top is at or before *now*, it pops and forwards.

```text
# Strategy thread (one per strategy)
for (fire_ts, dest_venue) in pre_sampled_schedule:
    while now() < fire_ts:
        spin_hint()
    order = build(fire_ts, dest_venue)
    submit_q.try_push(order)        # MPSC: contended hand-off (benchmark target)

# Orchestrator thread (single)
loop:
    # consume from strategies
    if order := submit_q.try_pop():
        simulate_work(orch_work)                          # CPU work per order (see section 5)
        gateway_inbox[order.venue].try_push(order)        # SPSC: routed fan-out

    # consume completions from gateways
    if completion := completion_q.try_pop():              # MPSC: contended hand-off (benchmark target)
        return_q[completion.owner].try_push(completion)   # SPSC

# Gateway thread (one per venue)
heap = MinHeap()       # ordered by release_at
loop:
    # accept new orders
    while order := gateway_inbox.try_pop():
        order.release_at = now() + D
        heap.push(order)                                  # O(log N)

    # release matured orders
    while not heap.empty() and heap.peek().release_at <= now():   # O(1) peek
        ready = heap.pop()                                # O(log N)
        completion_q.try_push(ready)                      # MPSC: benchmark target
```


## 3. Latency measurement

Each order carries 8 timestamps, splitting the round trip into 7 segments.

<div class="timeline">
  <div class="t-node"><span class="t-num">t1</span><span class="t-name">strategy_send</span></div>
  <div class="t-seg t-tech"><span class="t-sname">submit_latency</span><span class="t-cat">MPSC bench</span></div>

  <div class="t-node"><span class="t-num">t2</span><span class="t-name">orch_recv_submit</span></div>
  <div class="t-seg t-engine"><span class="t-sname">orch_pre_dispatch</span><span class="t-cat">internal</span></div>

  <div class="t-node"><span class="t-num">t3</span><span class="t-name">orch_dispatch</span></div>
  <div class="t-seg t-spsc"><span class="t-sname">dispatch_latency</span><span class="t-cat">fixed SPSC</span></div>

  <div class="t-node"><span class="t-num">t4</span><span class="t-name">gateway_recv</span></div>
  <div class="t-seg t-venue"><span class="t-sname">venue_service</span><span class="t-cat">venue D</span></div>

  <div class="t-node"><span class="t-num">t5</span><span class="t-name">gateway_done</span></div>
  <div class="t-seg t-tech"><span class="t-sname">completion_latency</span><span class="t-cat">MPSC bench</span></div>

  <div class="t-node"><span class="t-num">t6</span><span class="t-name">orch_recv_completion</span></div>
  <div class="t-seg t-engine"><span class="t-sname">orch_post_process</span><span class="t-cat">internal</span></div>

  <div class="t-node"><span class="t-num">t7</span><span class="t-name">orch_return</span></div>
  <div class="t-seg t-spsc"><span class="t-sname">return_latency</span><span class="t-cat">fixed SPSC</span></div>

  <div class="t-node"><span class="t-num">t8</span><span class="t-name">strategy_recv</span></div>

  <div class="t-total">
    <div><b>round_trip = t8 − t1</b></div>
    <div style="margin-top:4px;"><b>rt-venue = round_trip − venue_service = (t8 − t1) − (t5 − t4)</b></div>
  </div>
</div>



## 4. Baseline results (orch_work = 0)

Start with the baseline where the orchestrator does no work (W = 0). Unit is µs.

<div class="tbl-scroll"><table>
<thead><tr><th>Candidate</th><th>p50</th><th>p99</th><th>p99.9</th></tr></thead>
<tbody>
<tr><td>① std::sync::mpsc</td><td>1.2</td><td>2.4</td><td>4.1</td></tr>
<tr><td>② crossbeam-channel</td><td>1.3</td><td>2.3</td><td>3.7</td></tr>
<tr><td>③ <strong>ArrayQueue</strong></td><td><strong>1.1</strong></td><td><strong>1.8</strong></td><td><strong>3.1</strong></td></tr>
<tr><td>④ SPSC + mux</td><td>1.1</td><td>2.1</td><td>3.3</td></tr>
</tbody>
</table></div>

ArrayQueue is the lowest, but all 4 sit around 2µs at p99. Practically tied.

The reason: the orchestrator is idle. It does almost nothing per order (pop → push). So **queue depth** stays near 0, and every measurement is really "hand-off on an empty queue". The real difference between the 4 methods shows up *when queue depth builds up*.


## 5. orch_work sweep results

A real orchestrator does risk check, routing, and book updates per order. To mimic that cost, I added `orch_work` (W) and swept it over 0 / 500 / 1000 / 1500 ns. Look at `rt-venue` p99 by W (unit µs). *The table below shows raw `rt-venue p99`; the chart shows `rt-venue p99 − W`.*

<div class="tbl-scroll"><table>
<thead><tr><th>orch_work</th><th>① std::mpsc</th><th>② crossbeam</th><th>③ ArrayQueue</th><th>④ SPSC + mux</th></tr></thead>
<tbody>
<tr><td>0 ns</td><td>2.4</td><td>2.3</td><td><strong>1.8</strong></td><td>2.1</td></tr>
<tr><td>500 ns</td><td>6.1</td><td>6.1</td><td><strong>5.1</strong></td><td>6.0</td></tr>
<tr><td>1000 ns</td><td>19.5</td><td>20.5</td><td><strong>17.0</strong></td><td>19.8</td></tr>
<tr><td>1500 ns</td><td>94.9</td><td>108.7</td><td><strong>78.2</strong></td><td>89.2</td></tr>
</tbody>
</table></div>

Why look at `rt-venue − W`? By definition, `rt-venue` already includes W (the work the orchestrator did), so subtracting W leaves only hand-off + queueing cost.

<div class="svg-scroll">
<svg viewBox="0 0 700 400" xmlns="http://www.w3.org/2000/svg" style="display:block; margin:0 auto; width:700px; max-width:none; height:400px;">
  <style>
    .ax-grid { stroke:#e2e8f0; stroke-width:1; }
    .ax-main { stroke:#1e293b; stroke-width:1; }
    .lbl { font-family: ui-sans-serif, system-ui, sans-serif; font-size:11px; fill:#64748b; }
    .lbl-axis { font-family: ui-sans-serif, system-ui, sans-serif; font-size:11px; fill:#475569; }
    .lbl-title { font-family: ui-sans-serif, system-ui, sans-serif; font-size:14px; font-weight:600; fill:#0f172a; }
    .lbl-leg { font-family: ui-sans-serif, system-ui, sans-serif; font-size:11px; fill:#1e293b; }
  </style>
  <text x="350" y="18" text-anchor="middle" class="lbl-title">rt-venue p99 − W (handoff + queueing) vs orch_work</text>
  <g transform="translate(110, 38)">
    <line x1="0" y1="0" x2="22" y2="0" stroke="#3b82f6" stroke-width="2"/>
    <circle cx="11" cy="0" r="3.5" fill="#3b82f6"/>
    <text x="30" y="4" class="lbl-leg">std::sync::mpsc</text>
    <g transform="translate(140, 0)">
      <line x1="0" y1="0" x2="22" y2="0" stroke="#ef4444" stroke-width="2"/>
      <circle cx="11" cy="0" r="3.5" fill="#ef4444"/>
      <text x="30" y="4" class="lbl-leg">crossbeam-channel</text>
    </g>
    <g transform="translate(295, 0)">
      <line x1="0" y1="0" x2="22" y2="0" stroke="#16a34a" stroke-width="2.5"/>
      <circle cx="11" cy="0" r="4" fill="#16a34a"/>
      <text x="30" y="4" class="lbl-leg" font-weight="600">ArrayQueue</text>
    </g>
    <g transform="translate(400, 0)">
      <line x1="0" y1="0" x2="22" y2="0" stroke="#a855f7" stroke-width="2"/>
      <circle cx="11" cy="0" r="3.5" fill="#a855f7"/>
      <text x="30" y="4" class="lbl-leg">SPSC + mux</text>
    </g>
  </g>
  <line class="ax-grid" x1="60" y1="60"  x2="670" y2="60"/>
  <line class="ax-grid" x1="60" y1="108" x2="670" y2="108"/>
  <line class="ax-grid" x1="60" y1="157" x2="670" y2="157"/>
  <line class="ax-grid" x1="60" y1="205" x2="670" y2="205"/>
  <line class="ax-grid" x1="60" y1="253" x2="670" y2="253"/>
  <line class="ax-grid" x1="60" y1="302" x2="670" y2="302"/>
  <line class="ax-main" x1="60" y1="60" x2="60" y2="350"/>
  <line class="ax-main" x1="60" y1="350" x2="670" y2="350"/>
  <text x="55" y="350" text-anchor="end" dominant-baseline="middle" class="lbl">0</text>
  <text x="55" y="302" text-anchor="end" dominant-baseline="middle" class="lbl">20</text>
  <text x="55" y="253" text-anchor="end" dominant-baseline="middle" class="lbl">40</text>
  <text x="55" y="205" text-anchor="end" dominant-baseline="middle" class="lbl">60</text>
  <text x="55" y="157" text-anchor="end" dominant-baseline="middle" class="lbl">80</text>
  <text x="55" y="108" text-anchor="end" dominant-baseline="middle" class="lbl">100</text>
  <text x="55" y="60"  text-anchor="end" dominant-baseline="middle" class="lbl">120</text>
  <text x="22" y="205" text-anchor="middle" class="lbl-axis" transform="rotate(-90, 22, 205)">rt-venue p99 − W (µs)</text>
  <text x="60"  y="370" text-anchor="middle" class="lbl">0</text>
  <text x="263" y="370" text-anchor="middle" class="lbl">500</text>
  <text x="467" y="370" text-anchor="middle" class="lbl">1000</text>
  <text x="670" y="370" text-anchor="middle" class="lbl">1500</text>
  <text x="365" y="392" text-anchor="middle" class="lbl-axis">orch_work W (ns)</text>
  <polyline fill="none" stroke="#3b82f6" stroke-width="2" points="60,344 263,336 467,305 670,124"/>
  <circle cx="60"  cy="344" r="3.5" fill="#3b82f6"/>
  <circle cx="263" cy="336" r="3.5" fill="#3b82f6"/>
  <circle cx="467" cy="305" r="3.5" fill="#3b82f6"/>
  <circle cx="670" cy="124" r="3.5" fill="#3b82f6"/>
  <polyline fill="none" stroke="#ef4444" stroke-width="2" points="60,344 263,336 467,303 670,91"/>
  <circle cx="60"  cy="344" r="3.5" fill="#ef4444"/>
  <circle cx="263" cy="336" r="3.5" fill="#ef4444"/>
  <circle cx="467" cy="303" r="3.5" fill="#ef4444"/>
  <circle cx="670" cy="91"  r="3.5" fill="#ef4444"/>
  <polyline fill="none" stroke="#a855f7" stroke-width="2" points="60,345 263,337 467,305 670,138"/>
  <circle cx="60"  cy="345" r="3.5" fill="#a855f7"/>
  <circle cx="263" cy="337" r="3.5" fill="#a855f7"/>
  <circle cx="467" cy="305" r="3.5" fill="#a855f7"/>
  <circle cx="670" cy="138" r="3.5" fill="#a855f7"/>
  <polyline fill="none" stroke="#16a34a" stroke-width="2.5" points="60,346 263,339 467,311 670,165"/>
  <circle cx="60"  cy="346" r="4" fill="#16a34a"/>
  <circle cx="263" cy="339" r="4" fill="#16a34a"/>
  <circle cx="467" cy="311" r="4" fill="#16a34a"/>
  <circle cx="670" cy="165" r="4" fill="#16a34a"/>
</svg>
</div>

As W grows, the lines split. At W = 1500, the gap between ArrayQueue (~77 µs) and crossbeam (~107 µs) is around 30 µs.

**ArrayQueue is the lowest at every W.** No allocation (vs ①), no wrapper (vs ②), and the consumer reads only one ring (vs ④). When load rises, those small differences get amplified by queueing.

The tail explosion near W = 1500 is the M/M/1 knee: the orchestrator's service time gets close to the per-order arrival interval. ArrayQueue has a lower per-op cost, so it crosses the knee later.

Run-to-run p99 spread is ~7% across 5 repeats, and both contended MPSC sites (submit_q, completion_q) returned Full = 0 up to W = 1500. In-flight count matched Little's law, so no run was overloaded. The ranking is not luck, not backpressure noise.



## 6. Conclusion

On AWS c7g.4xlarge (16 vCPU Graviton3, Linux, threads pinned to cores), comparing the 4 methods showed: **as orchestrator service time grows, queue depth at submit_q rises, and ArrayQueue's lower per-op cost compounds.**

Based on this, I built the OE Engine's *busy-polled contended hot path* (submit_q, completion_q) with **ArrayQueue**.
