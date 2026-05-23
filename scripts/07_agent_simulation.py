#!/usr/bin/env python3
"""
07_agent_simulation.py — Minimal inspectable agent simulation pilot
=======================================================================
Event   : NVDA_Q3FY26 (earnings 2025-11-19 21:00 UTC)
Agents  : 9 archetypes × 3 agents = 27 agents
Rounds  : 5  (pre-event → immediate → digest → follow-up → wind-down)
Text    : Template-based (no LLM API)  — documented in AGENT_OBSERVABILITY_AUDIT.md
Stance  : Rule-based updates           — documented in AGENT_OBSERVABILITY_AUDIT.md

Outputs
-------
data/processed/sim_agent_trace.csv
data/processed/sim_comments.csv
"""

import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
random.seed(SEED)
np.random.seed(SEED)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"

# ---------------------------------------------------------------------------
# Event constants  (tied to real NVDA_Q3FY26 filing)
# ---------------------------------------------------------------------------
EVENT_ID   = "NVDA_Q3FY26"
TICKER     = "NVDA"
EVENT_TIME = datetime(2025, 11, 19, 21, 0, 0, tzinfo=timezone.utc)

# Factual context from real data (comment: "NVDA Quarterly Revenue $57 billion")
CTX = {
    "ticker":   "NVDA",
    "revenue":  "$57B",          # as observed in real data headline comment
    "product":  "Blackwell",     # NVDA's actual AI GPU product line in FY26
    "ceo":      "Jensen Huang",
    "guidance": "raised guidance for Q4",
    "segment":  "data center",
}

# ---------------------------------------------------------------------------
# Archetype definitions  (from CLAUDE.md locked spec)
# ---------------------------------------------------------------------------
ARCHETYPES = {
    "valuation-focused":    "long-horizon",
    "fundamentals-focused": "long-horizon",
    "buy-the-dip":          "long-horizon",
    "momentum-following":   "short-horizon",
    "event-reactive":       "short-horizon",
    "profit-taking":        "short-horizon",
    "uncertain":            "info-seeking",
    "evidence-seeking":     "info-seeking",
    "wait-and-see":         "info-seeking",
}

# Initial stance sampling weights  [bullish, bearish, neutral]
INIT_STANCE_W = {
    "valuation-focused":    (0.40, 0.25, 0.35),
    "fundamentals-focused": (0.50, 0.15, 0.35),
    "buy-the-dip":          (0.55, 0.10, 0.35),
    "momentum-following":   (0.50, 0.20, 0.30),
    "event-reactive":       (0.40, 0.30, 0.30),
    "profit-taking":        (0.30, 0.30, 0.40),
    "uncertain":            (0.20, 0.20, 0.60),
    "evidence-seeking":     (0.25, 0.25, 0.50),
    "wait-and-see":         (0.20, 0.15, 0.65),
}

# Probability agent is active in each round  [R0, R1, R2, R3, R4]
ACTIVITY = {
    "valuation-focused":    (0.40, 0.55, 0.65, 0.50, 0.30),
    "fundamentals-focused": (0.20, 0.55, 0.70, 0.60, 0.40),
    "buy-the-dip":          (0.30, 0.70, 0.50, 0.40, 0.20),
    "momentum-following":   (0.20, 0.90, 0.70, 0.40, 0.20),
    "event-reactive":       (0.10, 0.95, 0.80, 0.50, 0.20),
    "profit-taking":        (0.20, 0.75, 0.65, 0.50, 0.30),
    "uncertain":            (0.30, 0.50, 0.40, 0.30, 0.20),
    "evidence-seeking":     (0.10, 0.35, 0.65, 0.65, 0.40),
    "wait-and-see":         (0.10, 0.20, 0.45, 0.65, 0.55),
}

# Prob of replying vs posting new  (rule-based choice documented in audit)
REPLY_BIAS = {
    "valuation-focused":    0.30,
    "fundamentals-focused": 0.25,
    "buy-the-dip":          0.20,
    "momentum-following":   0.35,
    "event-reactive":       0.45,
    "profit-taking":        0.30,
    "uncertain":            0.50,
    "evidence-seeking":     0.40,
    "wait-and-see":         0.35,
}

# Higher = less likely to update stance per round
STUBBORNNESS = {
    "valuation-focused":    0.75,
    "fundamentals-focused": 0.70,
    "buy-the-dip":          0.60,
    "momentum-following":   0.40,
    "event-reactive":       0.35,
    "profit-taking":        0.55,
    "uncertain":            0.30,
    "evidence-seeking":     0.55,
    "wait-and-see":         0.60,
}

# Round bounds (hours from event) and descriptive context
ROUND_DEFS = [
    (-2.0,   0.0,  "pre-event: speculation, NVDA earnings imminent"),
    ( 0.0,   6.0,  "immediate reaction: NVDA Q3 results just released"),
    ( 6.0,  12.0,  "digest: analysts and press coverage flowing in"),
    (12.0,  24.0,  "follow-up: price action settling, longer views form"),
    (24.0,  48.0,  "wind-down: lingering debate, late participants weigh in"),
]

AGENTS_PER_ARCHETYPE = 3

# ---------------------------------------------------------------------------
# Post templates  (per archetype × stance)
# ---------------------------------------------------------------------------
POST_TEMPLATES: dict[str, dict[str, list[str]]] = {
    "valuation-focused": {
        "bullish": [
            "Updated my NVDA DCF with the {revenue} quarterly print. Even at conservative assumptions, intrinsic value is above current prices. Long.",
            "Market is underpricing the {product} cycle. {ticker} screens cheap on a PEG basis at these growth rates. Adding here.",
            "{ceo} delivered again. {revenue} with ~56% gross margins. The P/E looks optically high but EV/FCF is reasonable for this growth trajectory.",
            "Re-ran valuation after earnings. {ticker} at current multiples prices in a slowdown that isn't in the data. The {revenue} beat confirms the thesis.",
        ],
        "bearish": [
            "Even after a {revenue} quarter, {ticker} is priced for perfection. Any hyperscaler capex softening and this multiple compresses 30%. Risk/reward is unfavorable.",
            "DCF doesn't support current price. 25x forward revenue. {product} hype is baked in. AMD and custom silicon headwinds ignored by the market.",
            "{revenue} is impressive but you're paying for 5 more years of peak growth. Mean reversion comes for all high-multiple stocks eventually.",
            "Valuation math doesn't work for me here. {ticker} needs to execute flawlessly for another 3 years just to justify today's price.",
        ],
        "neutral": [
            "Good quarter from {ticker}. {revenue} revenue. Updating model now — need to settle on the right multiple before adding.",
            "Strong {revenue} print but I'm cautious about chasing at all-time highs. Fair value somewhere between the bulls and bears. Watching.",
            "Trying to reconcile {revenue} beat with current valuation. {product} is real, multiple is stretched. Holding.",
            "NVDA beat on revenue and EPS. Need more time to update model with {guidance} before forming a strong view.",
        ],
    },
    "fundamentals-focused": {
        "bullish": [
            "Breaking down NVDA Q3: {revenue} revenue, data center dominant, {product} ramp ahead of schedule. This is a fundamentals story, not hype.",
            "Gross margin expansion at {ticker} is the real story. {revenue} top-line with improving margins = massive FCF generation. Adding.",
            "{ceo} said {product} demand exceeds supply on the call. Pricing power AND volume growth simultaneously — textbook bull case.",
            "Data center revenue growth rate is extraordinary. NVDA moat in AI compute widening. {product} provides another 2-3 year runway. {revenue} confirms.",
        ],
        "bearish": [
            "NVDA Q3 solid but fundamentals have a ceiling. Hyperscalers building custom chips. Top-3 customer concentration >35% is structural risk.",
            "{revenue} is big but ASICs from Google, Amazon, MSFT will pressure margins. Durable moat is questionable at current scale.",
            "Revenue beat but Q4 guidance was only in-line. When priced for +20% beats every quarter, in-line guidance is effectively a miss on fundamentals.",
            "Compelling story but unsustainable. {revenue} requires hyperscalers to spend at this pace indefinitely. They will optimize capex.",
        ],
        "neutral": [
            "Solid Q3. Revenue {revenue}, {product} ramp contributing, margins stable. No red flags but not screaming buy either. Holding.",
            "NVDA fundamentals remain strong. Question is how much is priced in. {revenue} is a big number but the bar was set high.",
            "Earnings call notes: {ceo} on {product} supply/demand. Data center growth intact. Need to model Q4 guidance assumptions.",
            "Good quarter. {revenue}, {guidance}. Watching how stock reacts before deciding whether to add.",
        ],
    },
    "buy-the-dip": {
        "bullish": [
            "If {ticker} pulls back 10-15% from here I'm loading up. {product} cycle is early innings. Any dip is a gift.",
            "Been waiting for a dip entry on {ticker}. {revenue} quarter confirms the story. If we get sell-the-news drop, I'm buying aggressively.",
            "Long {ticker} with dip-buying strategy. Earnings beat confirms fundamental story. Any profit-taking I treat as an entry point.",
            "Already setting limit orders 8% below current {ticker} levels. {revenue} quarter proves the thesis. Dips are buying opportunities here.",
        ],
        "bearish": [
            "Even dip-buying has limits. {ticker} has run too far. {revenue} is priced in and more. Waiting for a much deeper correction.",
            "Risk asymmetry is bad here. Any real dip signals structural issues, not temporary profit-taking. Sitting on sidelines after {revenue} print.",
            "I love dip-buying but {ticker} at this valuation — even after a {revenue} quarter — is not where I want to deploy capital.",
        ],
        "neutral": [
            "Monitoring {ticker} post-earnings. Strong {revenue} print. Setting buy alerts at -8% and -15% from current levels. Not chasing.",
            "Strong quarter from {ticker}. Not buying at all-time highs. Watching for a dip. {product} ramp is real but need better risk/reward.",
            "After {revenue} quarter, {ticker} might sell off on good-news-priced-in. That is the dip I am watching for. Patience.",
        ],
    },
    "momentum-following": {
        "bullish": [
            "{ticker} breaking out above pre-earnings consolidation range on huge volume. Momentum is clearly bullish post-{revenue} print. Riding this.",
            "RSI was 65 going into earnings. After {revenue} beat? Momentum players are in. Trend intact. Long.",
            "Technical picture for {ticker} is clean post-earnings. Broke out on volume. {revenue} was the fundamental trigger. Momentum green.",
            "{ticker} trend intact: higher highs, higher lows, massive revenue beat {revenue}. {product} is the momentum catalyst.",
        ],
        "bearish": [
            "{ticker} rejected at all-time highs on big volume post-earnings. Classic exhaustion. Even with {revenue}, couldn't hold the breakout. Fading.",
            "Divergence on the hourly chart. Price made new high but momentum indicators rolling over after {revenue} spike. Shorting the rip.",
            "The post-earnings move looks like a blow-off top. Everyone positioned for the beat. {revenue} was good but reaction was muted. Red flag.",
        ],
        "neutral": [
            "{ticker} trading choppy after {revenue} print. No clear momentum direction yet. Waiting for first hour to close.",
            "Mixed signals on charts after earnings. Revenue beat {revenue} but price action unclear. Watching for trend confirmation.",
            "Watching {ticker} post-earnings. {revenue} strong but the reaction is the real tell. Momentum players watching the same levels.",
        ],
    },
    "event-reactive": {
        "bullish": [
            "NVDA just reported {revenue} revenue!! {product} is everything they said it would be. {ceo} delivered. Huge position here.",
            "{ticker} earnings: beat on revenue {revenue}, beat on EPS, {guidance}. The AI trade is alive. All in.",
            "{revenue}!! This is what the bulls have been waiting for. {product} ramp is REAL. Massive.",
            "NVDA crushed it. {revenue} quarterly revenue, {guidance}. {ceo} is executing perfectly.",
        ],
        "bearish": [
            "{ticker} beats but stock barely moved. Priced in. The {revenue} print was good but not good enough for this valuation. Selling.",
            "Sell the news on {ticker}. Everyone expected {revenue} beat. Now what? Easy money is made. Getting out.",
            "Stock up 3% on {revenue} beat? For a stock at these multiples that reaction is WEAK. Demand is peaking.",
            "{ticker} guided in-line for Q4. After {revenue} you'd expect bigger upside. Disappointed. Trimming.",
        ],
        "neutral": [
            "{ticker} beat {revenue} revenue. Stock up a few percent. Watching for direction. Sell-the-news or new leg up?",
            "NVDA earnings done. {revenue} revenue beat. Waiting to see if buyers step in or profit-takers dominate.",
            "Just watching {ticker} trade after {revenue} print. Initial reaction positive but now fading. What is everyone else doing?",
        ],
    },
    "profit-taking": {
        "bullish": [
            "Trimmed 20% of {ticker} into earnings pop but still holding core position for {product} cycle. Taking some gains, staying long.",
            "Sold some {ticker} into earnings pop. Will re-enter on pullback. {revenue} quarter is great, {product} story still intact.",
            "Locked in gains on part of {ticker} position. Not calling a top — just disciplined risk management. Still long overall after {revenue}.",
        ],
        "bearish": [
            "Been in {ticker} since $200. After {revenue} quarter with the stock this high, I'm out entirely. Taking the win.",
            "Got out of {ticker} completely. Even with {revenue}, risk/reward post-earnings is unfavorable. Moving on.",
            "Locked in profits on {ticker} pre-earnings. Glad I did. {revenue} was priced in. Crowded trade going down.",
        ],
        "neutral": [
            "Reduced {ticker} position by 30% into earnings strength. Not bearish on {product} story but want to lock in gains. May add back lower.",
            "Partial profit taking on {ticker} after {revenue} beat. Not calling a top, just disciplined. Keeping core position.",
            "Took some {ticker} off table at earnings peak. Cautious near-term but still long overall after {revenue}.",
        ],
    },
    "uncertain": {
        "bullish": [
            "I think NVDA earnings were good? {revenue} seems huge. Is this a buy? Cautiously leaning bullish but not sure.",
            "Considering buying {ticker} after earnings beat {revenue}. {product} sounds promising. Newbie here — is this a good entry?",
            "Cautiously bullish on {ticker} after {revenue} print. Anyone want to help me understand the {product} competitive dynamics?",
        ],
        "bearish": [
            "Not sure about {ticker} here. {revenue} was impressive but the stock seems really expensive. Am I missing something?",
            "Feeling uneasy about {ticker} even after {revenue} beat. Valuation seems stretched. Anyone else nervous?",
            "Maybe I am wrong but {ticker} at these levels after {revenue} quarter feels risky. What is the downside scenario?",
        ],
        "neutral": [
            "Can someone explain NVDA earnings? {revenue} in revenue — is that a beat vs expectations? Confused about the reaction.",
            "Trying to understand {ticker} results. {revenue}, {product} ramp mentioned. What does this mean for price going forward?",
            "NVDA earnings confusing me. {revenue} seems incredible but stock barely moved. Is this good or bad?",
            "Help me understand {ticker} post-earnings. What does {product} ramp mean for long-term holders? Concerned or excited?",
        ],
    },
    "evidence-seeking": {
        "bullish": [
            "Pulled the {ticker} 10-Q. Data center segment grew 112% YoY. {revenue} total with improving margins. Evidence supports being long.",
            "Transcript review: {ceo} gave specific color on {product} supply/demand. Revenue {revenue}. The evidence is solid — adding.",
            "Ran through the earnings model. Revenue {revenue}, EPS beat by 8%, Q4 guidance implies continued growth. Data supports being long.",
        ],
        "bearish": [
            "Checked the {ticker} 8-K. {revenue} is strong but customer concentration 35%+ in top 3. Structural risk bulls are ignoring.",
            "Beat margins narrowing vs last 4 quarters. {revenue} is big but growth deceleration trend worth watching closely.",
            "Dug into segment data. {product} ASPs are flat. {revenue} growth is volume not pricing power. That is different from bull thesis.",
        ],
        "neutral": [
            "Going through {ticker} earnings release now. {revenue} top-line. Need to parse segment detail before forming a view. Will post analysis later.",
            "Reading {ceo} remarks on the {ticker} call. {revenue} revenue, {product} color. Forming view based on data not sentiment. Give me an hour.",
            "Has anyone seen full {ticker} earnings breakdown? {revenue} total revenue but I want segment-level data before deciding.",
            "Analyzing NVDA Q3 systematically: Revenue {revenue}, EPS beat, margins stable, guidance raised. Need to check FCF and customer concentration.",
        ],
    },
    "wait-and-see": {
        "bullish": [
            "After watching {ticker} trade for a few days post-earnings, becoming more confident. {revenue} print is holding up and {product} narrative confirmed.",
            "Waited to see how {ticker} digested {revenue} earnings. Price action bullish. Getting in now with more conviction than chasing initial pop.",
            "Was wait-and-see on {ticker} but after seeing price stability post-{revenue}, comfortable adding here.",
        ],
        "bearish": [
            "Watched {ticker} for a week after {revenue} earnings. Initial pop has faded. Distribution pattern forming. Wait was right call — now bearish.",
            "Held off on {ticker} post-earnings. {revenue} was fine but reaction faded. Better entry points coming lower.",
            "My patient approach on {ticker} paying off. {revenue} quarter good but post-earnings drift concerning. Waiting for lower levels.",
        ],
        "neutral": [
            "Still watching {ticker} post-earnings. {revenue} was strong but want to see how stock behaves over next few days before acting.",
            "Taking my time with {ticker}. {revenue} print solid. Watching price action, volume, any follow-up from {ceo}.",
            "Not in a rush on {ticker}. {revenue} earnings were good but patient — waiting for cleaner risk/reward before committing.",
            "{ticker} has had a big move. {revenue} supports bulls but disciplined — waiting for either dip or breakout confirmation.",
        ],
    },
}

# Reply templates (shorter, reactive)
REPLY_TEMPLATES: dict[str, list[str]] = {
    "agree": [
        "Completely agree. {ticker} at these levels makes sense given the {revenue} quarter.",
        "Yes, exactly. The {revenue} beat validates the thesis. Strong hands.",
        "This is the correct read. {product} cycle is just beginning.",
        "100%. The data speaks for itself here.",
        "Spot on. Fundamentals are clear after {revenue} quarter.",
    ],
    "disagree_bear_to_bull": [
        "Respectfully disagree. Even with {revenue}, the valuation is stretched. Pricing in perfection.",
        "The beat is good but you are ignoring valuation risk. {ticker} is not cheap here.",
        "Counter-point: {revenue} is strong but guidance was not spectacular. Easy money made.",
        "Not convinced. Custom silicon from hyperscalers is a real threat bulls keep dismissing.",
        "I have heard this bull thesis before. Downside risk at these multiples is real.",
    ],
    "disagree_bull_to_bear": [
        "The bear case keeps getting proven wrong. {revenue} quarterly is not a coincidence.",
        "You are fighting the AI capex cycle. {product} demand is structural, not cyclical.",
        "Short sellers have been calling {ticker} overvalued for years. Outcome?",
        "Respectfully, the bear thesis ignores the {product} super-cycle.",
        "Valuation argument ignores the growth rate. {revenue} quarterly and accelerating.",
    ],
    "question": [
        "Genuine question: what is your price target on {ticker} given {revenue} beat?",
        "Can you explain which metrics you are using to value {ticker}? {revenue} seems undeniable.",
        "How are you thinking about {product} ramp in your model? That is the key variable.",
        "What would change your view? {revenue} quarter seems hard to argue with.",
        "Are you in the stock? I am deciding whether to add after {revenue} beat.",
    ],
    "add_context": [
        "Adding: {ceo} said {product} is supply-constrained not demand-constrained on the call.",
        "Worth noting: data center is now dominant segment. {revenue} total quarterly.",
        "One more point: gross margins held despite rapid {product} ramp. That is impressive.",
        "Also: {ticker} announced expanded production. The {revenue} number should grow.",
        "Context: this is the fourth consecutive beat for {ticker}. Trend is clear.",
    ],
}


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class Agent:
    """A single simulated investor agent."""

    def __init__(self, agent_id: str, archetype: str):
        self.agent_id  = agent_id
        self.archetype = archetype
        self.cohort    = ARCHETYPES[archetype]

        # Sample initial stance
        stances  = ["bullish", "bearish", "neutral"]
        weights  = INIT_STANCE_W[archetype]
        self.stance     = random.choices(stances, weights=weights, k=1)[0]
        self.confidence = round(random.uniform(0.45, 0.90), 2)

    def activity_prob(self, round_id: int) -> float:
        return ACTIVITY[self.archetype][round_id]

    def decide_action(self, round_id: int, available_comments: list[dict]) -> str:
        """
        Rule: if round has existing comments AND random < reply_bias → 'reply'
        Otherwise → 'post'
        Also: small chance of 'observe' (agent active but silent)
        """
        if not self.is_active(round_id):
            return "observe"
        if available_comments and random.random() < REPLY_BIAS[self.archetype]:
            return "reply"
        if random.random() < 0.10:  # 10% chance of silent observation even if active
            return "observe"
        return "post"

    def is_active(self, round_id: int) -> bool:
        return random.random() < self.activity_prob(round_id)

    def pick_reply_target(self, available_comments: list[dict]) -> dict | None:
        """
        Reply selection rule (documented in audit):
        - Event-reactive & momentum agents prefer opposing stance (more reactive/argumentative)
        - Info-seeking agents prefer questions / neutral posts
        - Otherwise: weak preference for opposing stance to generate debate
        """
        if not available_comments:
            return None

        if self.archetype in ("event-reactive", "momentum-following"):
            # Prefer opposing stance for debate
            opposing = [c for c in available_comments if c["stance"] != self.stance]
            if opposing and random.random() < 0.55:
                return random.choice(opposing)

        if self.archetype in ("uncertain", "evidence-seeking", "wait-and-see"):
            # Prefer neutral or same cohort
            neutral_posts = [c for c in available_comments if c["stance"] == "neutral"]
            if neutral_posts and random.random() < 0.50:
                return random.choice(neutral_posts)

        return random.choice(available_comments)

    def generate_text(self, action_type: str, reply_target: dict | None) -> str:
        """Template fill with event context. No LLM API used."""
        c = CTX  # shorthand

        if action_type == "observe":
            return ""

        if action_type == "post":
            templates = POST_TEMPLATES[self.archetype][self.stance]
            tmpl = random.choice(templates)
            return tmpl.format(**c)

        # reply
        if reply_target is None:
            templates = POST_TEMPLATES[self.archetype][self.stance]
            return random.choice(templates).format(**c)

        target_stance = reply_target["stance"]
        if target_stance == self.stance:
            key = "agree"
        elif self.stance == "bearish" and target_stance == "bullish":
            key = "disagree_bear_to_bull"
        elif self.stance == "bullish" and target_stance == "bearish":
            key = "disagree_bull_to_bear"
        else:
            key = random.choice(["question", "add_context"])

        tmpl = random.choice(REPLY_TEMPLATES[key])
        return tmpl.format(**c)

    def update_stance(self, round_id: int, round_comments: list[dict]) -> str:
        """
        Rule-based stance update (NOT Bayesian, documented in audit).
        - Compute social pressure from round comments
        - If pressure exceeds threshold and agent is not stubborn, update stance
        - Event-reactive agents also respond to event shock in round 1
        """
        prev_stance = self.stance

        if not round_comments:
            return prev_stance

        bull = sum(1 for c in round_comments if c["stance"] == "bullish")
        bear = sum(1 for c in round_comments if c["stance"] == "bearish")
        total = len(round_comments)
        pressure = (bull - bear) / total  # range [-1, 1]

        stub = STUBBORNNESS[self.archetype]

        # Event shock: in round 1, earnings beat pushes toward bullish
        if round_id == 1:
            event_shock = 0.30  # NVDA beat → positive shock
            pressure += event_shock

        # Probability of updating scales with pressure magnitude and inverse stubbornness
        update_prob = (1 - stub) * min(abs(pressure), 1.0) * 0.40

        if random.random() < update_prob:
            if pressure > 0.20 and self.stance != "bullish":
                self.stance = "neutral" if self.stance == "bearish" else "bullish"
            elif pressure < -0.20 and self.stance != "bearish":
                self.stance = "neutral" if self.stance == "bullish" else "bearish"

        # Update confidence
        self.confidence = min(0.97, max(0.30,
            self.confidence + random.gauss(0.0, 0.05)))

        return self.stance


# ---------------------------------------------------------------------------
# Simulation runner
# ---------------------------------------------------------------------------

def make_agent_id(archetype: str, n: int) -> str:
    short = {
        "valuation-focused":    "val",
        "fundamentals-focused": "fun",
        "buy-the-dip":          "btd",
        "momentum-following":   "mom",
        "event-reactive":       "evt",
        "profit-taking":        "pft",
        "uncertain":            "unc",
        "evidence-seeking":     "evi",
        "wait-and-see":         "was",
    }
    return f"A_{short[archetype]}_{n}"


def random_hour(lo: float, hi: float) -> float:
    return round(random.uniform(lo, hi), 4)


def hour_to_timestamp(h: float) -> str:
    ts = EVENT_TIME + timedelta(hours=float(h))
    return ts.isoformat()


def make_comment_id(round_id: int, agent_id: str, seq: int) -> str:
    return f"SC{round_id}_{agent_id}_{seq:03d}"


def run_simulation():
    print("=" * 60)
    print("07_agent_simulation.py — NVDA_Q3FY26 Pilot")
    print("=" * 60)

    # Build agent roster
    agents: list[Agent] = []
    for archetype in ARCHETYPES:
        for n in range(1, AGENTS_PER_ARCHETYPE + 1):
            agents.append(Agent(make_agent_id(archetype, n), archetype))

    print(f"  Agents created: {len(agents)} ({AGENTS_PER_ARCHETYPE} per archetype)")

    trace_rows: list[dict]   = []
    comment_rows: list[dict] = []
    comment_seq              = 0  # global comment counter

    # All comments produced so far (for reply targeting)
    all_comments: list[dict] = []

    for round_id, (lo_h, hi_h, round_ctx) in enumerate(ROUND_DEFS):
        print(f"\n  Round {round_id}: {round_ctx}")
        round_comments: list[dict] = []  # comments produced this round

        for agent in agents:
            prior_stance = agent.stance
            prior_conf   = round(agent.confidence, 3)

            # Choose action
            action_type = agent.decide_action(round_id, all_comments)

            # Pick reply target (None if posting new)
            reply_target = None
            reply_to_id  = ""
            if action_type == "reply":
                reply_target = agent.pick_reply_target(all_comments)
                if reply_target is None:
                    action_type = "post"
                else:
                    reply_to_id = reply_target["comment_id"]

            # Generate text
            text = agent.generate_text(action_type, reply_target)

            # Assign output comment id (even for observe, record trace row)
            comment_id = ""
            if action_type != "observe":
                comment_seq += 1
                comment_id = make_comment_id(round_id, agent.agent_id, comment_seq)

            hours = random_hour(lo_h, hi_h) if action_type != "observe" else round_h_center(lo_h, hi_h)
            sim_ts = hour_to_timestamp(hours)

            # Observed context description (what agent "sees")
            visible_bull = sum(1 for c in all_comments if c["stance"] == "bullish")
            visible_bear = sum(1 for c in all_comments if c["stance"] == "bearish")
            observed_ctx = (
                f"Round {round_id} ({round_ctx}). "
                f"Visible comments: {len(all_comments)} total, "
                f"{visible_bull} bullish, {visible_bear} bearish."
            )

            # Record trace row
            trace_rows.append({
                "event_id":                 EVENT_ID,
                "round_id":                 round_id,
                "agent_id":                 agent.agent_id,
                "archetype":                agent.archetype,
                "broad_cohort":             agent.cohort,
                "prior_stance_or_belief":   prior_stance,
                "observed_context":         observed_ctx,
                "action_type":              action_type,
                "generated_text":           text,
                "reply_to_comment_id":      reply_to_id,
                "output_comment_id":        comment_id,
                "posterior_stance_or_belief": prior_stance,  # filled after stance update
                "simulated_timestamp":      sim_ts,
                "confidence_or_intensity":  prior_conf,
            })

            # Record comment row (only for post/reply)
            if action_type != "observe":
                cmt = {
                    "event_id":         EVENT_ID,
                    "ticker":           TICKER,
                    "event_time":       EVENT_TIME.isoformat(),
                    "round_id":         round_id,
                    "agent_id":         agent.agent_id,
                    "archetype":        agent.archetype,
                    "broad_cohort":     agent.cohort,
                    "comment_id":       comment_id,
                    "parent_id":        reply_to_id if reply_to_id else comment_id,
                    "hours_from_event": hours,
                    "text":             text,
                    "stance":           agent.stance,
                    "source_type":      "sim_agent",
                    "simulated_timestamp": sim_ts,
                    "depth":            0 if action_type == "post" else 1,
                }
                round_comments.append(cmt)
                all_comments.append(cmt)
                comment_rows.append(cmt)

        # Update stances after round (social influence step)
        for agent in agents:
            posterior = agent.update_stance(round_id, round_comments)
            # Back-fill posterior in trace rows for this round
            for row in trace_rows:
                if row["round_id"] == round_id and row["agent_id"] == agent.agent_id:
                    row["posterior_stance_or_belief"] = posterior

        n_posts   = sum(1 for c in round_comments if c["depth"] == 0)
        n_replies = sum(1 for c in round_comments if c["depth"] == 1)
        print(f"    -> {len(round_comments)} comments ({n_posts} posts, {n_replies} replies)")

    # Build DataFrames
    trace_df   = pd.DataFrame(trace_rows)
    comment_df = pd.DataFrame(comment_rows)

    # Save
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    trace_path   = DATA_DIR / "sim_agent_trace.csv"
    comment_path = DATA_DIR / "sim_comments.csv"
    trace_df.to_csv(trace_path, index=False)
    comment_df.to_csv(comment_path, index=False)

    print(f"\n  Saved {len(trace_df)} trace rows  -> {trace_path}")
    print(f"  Saved {len(comment_df)} comment rows -> {comment_path}")

    # Quick summary
    print("\n  Stance distribution in sim comments:")
    print(comment_df["stance"].value_counts().to_string())
    print("\n  Actions breakdown:")
    print(trace_df["action_type"].value_counts().to_string())
    print("\n  Activity by archetype:")
    act = trace_df[trace_df["action_type"] != "observe"].groupby("archetype").size()
    print(act.sort_values(ascending=False).to_string())

    return trace_df, comment_df


def round_h_center(lo: float, hi: float) -> float:
    return round((lo + hi) / 2.0, 4)


if __name__ == "__main__":
    run_simulation()
    print("\nDone.")
