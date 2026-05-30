+++
title = "Why a Trading Engine Sets Its Own Order ID"
date = 2026-05-30T13:00:00+09:00
draft = false
tags = ["trading-systems", "order-management", "exchange-integration"]
summary = "An order carries two ids: the one I set before sending, and the one the exchange returns. Here's why the engine should key on mine."
+++

<!--
  Hugo: needs markup.goldmark.renderer.unsafe = true in config (for raw HTML rendering).
  Reuses the timeline / callout classes from blog2 (nonblocking-dispatch).
-->

<style>
.callout { margin: 24px 0; padding: 14px 18px; background: #f8fafc; border-left: 3px solid #2563eb; border-radius: 4px; font-size: 14px; line-height: 1.7; }

/* ----- timeline (reused from blog2 latency style) ----- */
.timeline { background: #fff; border: 1px solid #d0d3d8; border-radius: 8px; padding: 18px 20px; margin: 18px 0; }
.t-node { display: flex; align-items: center; gap: 10px; padding: 4px 0; }
.t-num { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 30px; border-radius: 50%; background: #1a1a1a; color: #fff; font-weight: 700; font-size: 12px; flex: none; font-family: ui-monospace, monospace; }
.t-name { font-family: ui-monospace, monospace; font-weight: 700; font-size: 13px; }
.t-who { color: #888; font-size: 12px; margin-left: 8px; }
.t-seg { margin: 4px 0 4px 18px; padding: 7px 14px; border-left: 3px solid #ccc; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.t-sname { font-family: ui-monospace, monospace; font-weight: 700; font-size: 12.5px; min-width: 220px; }
.t-cat { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 4px; }
.t-engine { border-left-color: #9db8e8; background: #eef4ff; }
.t-engine .t-cat { background: #9db8e8; color: #1a2d4f; }
.t-venue { border-left-color: #b3b3b3; background: #f1f1f1; }
.t-venue .t-cat { background: #b3b3b3; color: #fff; }
.t-wait { border-left-color: #e0533d; background: #fdf0ee; }
.t-wait .t-cat { background: #e0533d; color: #fff; }
.t-total { margin-top: 12px; padding: 10px 14px; background: #fff7e6; border: 1px solid #e8b84b; border-radius: 6px; font-size: 13px; line-height: 1.7; }
.t-total b { color: #b07400; }
.t-total .gap-label { display: inline-block; background: #fde68a; padding: 1px 8px; border-radius: 3px; font-family: ui-monospace, monospace; font-weight: 700; color: #92400e; }
</style>

Most people start systematic trading on a crypto exchange, usually through a general library like CCXT. It wraps many exchanges behind one interface, so the entry barrier is low. The first library I used was CCXT python too.

CCXT wraps the per-exchange fields into one common parameter. So if you only use CCXT, you rarely think about this field. You place an order and track it with the `order_id` that comes back.

But once you start reading the raw protocols and API docs of several exchanges, you notice one field that almost every exchange has, even though the name keeps changing (Binance `newClientOrderId`, Bybit `orderLinkId`, OKX `clOrdId`, Deribit `label` ...). It is a custom order id the client sets and sends, usually called `ClientOrderId`. It is the key the client and the exchange both use to point at the same order.

On crypto exchanges this field is usually optional, and some venues do not take it at all.

So why did crypto get by without `ClientOrderId`? Because most retail trading is REST-based. REST is synchronous: one request, one response, paired 1:1. You POST an order and the response hands you the `order_id` right there. The mapping between "the order I sent" and "the `order_id` the exchange gave" is settled on the spot, so you never need to set a key in advance.

Traditional finance has known this for a long time. FIX, the standard protocol, makes `ClOrdID` (Tag 11) a required field on an order. The owner of the order id is the client, not the exchange, from the start. Crypto REST trading could skip the cid only because synchronous calls handed you the mapping automatically, not because the cid matters less.

The trouble starts when you build an engine that manages many orders at once, like market making or HFT. There the `ClientOrderId` becomes essential. The benefit is clearer when you split it into the engine side and the strategy side.


## 1. Two IDs

Every order carries two ids.

- **ClientOrderId**: the id I set *before* I send the order. Source: client. Time: before send.
- **VenueOrderId**: the id the exchange returns once it accepts the order (in the ack). APIs usually call it `order_id` or `OrderId`. Source: venue. Time: after ack.

Here is the difference along the timeline.

<div class="timeline">
  <div class="t-node"><span class="t-num">1</span><span class="t-name">set cid</span><span class="t-who">I set the ClientOrderId, before sending</span></div>
  <div class="t-seg t-engine"><span class="t-sname">send the order</span></div>

  <div class="t-node"><span class="t-num">2</span><span class="t-name">order in flight</span><span class="t-who">cid on the wire, no VenueOrderId yet</span></div>
  <div class="t-seg t-wait"><span class="t-sname">waiting for ack</span><span class="t-cat">gap</span></div>

  <div class="t-node"><span class="t-num">3</span><span class="t-name">venue ack</span><span class="t-who">VenueOrderId now known</span></div>

  <div class="t-total">
    <div><b>cid</b>: exists from step 1 · <b>VenueOrderId</b>: only from step 3</div>
    <div>The <span class="gap-label">gap</span> between send and ack has one id only: <code>cid</code>.</div>
  </div>
</div>

The key part is the window between sending and the ack. There is no VenueOrderId yet, and everything about why you need a `ClientOrderId` comes from here.


## 2. The engine-side benefit

Say you only use the VenueOrderId. An order that is sent but not yet acked has no VenueOrderId, so you keep it in a "pending" set and, each time an ack arrives, you have to figure out which order it belongs to. Whether this matching is easy depends on one thing: is the channel **synchronous or asynchronous**.

| Protocol | Request ↔ response | Order ↔ response mapping |
|---|---|---|
| REST | 1:1 synchronous | the response gives it |
| WebSocket | async (separate frame) | needs a key |
| FIX | async (ExecutionReport) | needs ClOrdID |

With pure synchronous REST the matching is automatic. The response to your POST is the ack for that order, so they are paired 1:1. That is why simple REST trading runs fine without a `ClientOrderId`.

The trouble starts when you make the engine fast. To raise throughput you fire many orders in flight at once (async REST calls, or WebSocket fire-and-forget), and the responses come back scattered, in no fixed order. Fills often arrive on a separate WebSocket channel too. The moment the engine goes async, that automatic matching is gone. If you fire orders A, B, C and the responses come back A, C, B, you cannot tell which is which without your own key.

A `ClientOrderId` makes this go away. Each order carries an id I set, and the exchange echoes it back, so no matter what order or channel the responses arrive on, they match by that id at once. Pending stops being a guessing game and becomes a settled state.

Once this is solved, a few more things follow.

- **Retry and recovery**: you send, but no ack comes (timeout). The `ClientOrderId` is a stable key, so before resending you can check by it whether the order landed, instead of blindly firing a second one. Without it, a retry loop just keeps sending new orders, and one timeout becomes a runaway position. And if the order did land but its ack was lost on the way back, you query by the same cid and find it, since the venue indexed it under your key.
- **Cancel / replace**: you usually cancel or amend by VenueOrderId, but even if you have not captured it yet, you can fall back to the `ClientOrderId`.
- **Restart recovery**: if the process dies after send but before ack, a `ClientOrderId`-keyed persistence lets you recover what you sent.


## 3. The strategy-side benefit

The strategy gains for the same reason, and the key is **when the mapping is issued**. A VenueOrderId only exists after the ack, so you can build the map only after the fact. A ClientOrderId is set before you send, so whether it is the strategy's `level → cid` (to cancel a quote) or the engine's `cid → strategy` (to route a fill), you bind the map before the order goes out. Once the mapping is fixed up front, the logic no longer depends on when the VenueOrderId arrives.


## 4. When a venue does not take a ClientOrderId

Not every venue takes a `ClientOrderId`. Some have no field for it at all (some broker gateways, certain DEXs).

Even on these venues the engine makes its own internal `ClientOrderId` and tracks the order by it. It does not put the cid on the wire; when the response comes back with the VenueOrderId, it attaches that to the internal cid. Inside the engine, you identify and attribute orders by the cid as usual.


## Wrap-up

**The engine should identify an order by the `ClientOrderId` it set before sending, not by the id the exchange returns.** The moment you run orders async and in bulk, the exchange's responses alone cannot tell which response belongs to which order, and the only thing left to lean on is the key you attached first.
