#!/usr/bin/env python3
"""
08_observability.py — Agent behaviour visualisation & audit
=============================================================
Reads sim_agent_trace.csv and sim_comments.csv produced by 07_agent_simulation.py
and generates all observability artefacts.

Outputs
-------
outputs/AGENT_OBSERVABILITY_AUDIT.md
outputs/agent_behaviour_summary.txt
outputs/agent_activity_timeline.png
outputs/agent_interaction_graph.png
outputs/agent_stance_trajectories.png
outputs/sample_agent_dialogues.md
"""

from pathlib import Path
from textwrap import shorten, wrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

ROOT    = Path(__file__).resolve().parent.parent
DATA    = ROOT / "data" / "processed"
OUT     = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

# Colour palette per cohort
COHORT_COLOURS = {
    "long-horizon":  "#2196F3",  # blue
    "short-horizon": "#F44336",  # red
    "info-seeking":  "#4CAF50",  # green
}

ARCHETYPE_SHORT = {
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

STANCE_COLOURS = {
    "bullish": "#4CAF50",
    "bearish": "#F44336",
    "neutral": "#9E9E9E",
}

ROUND_LABELS = [
    "R0\n(-2h→0h)\npre",
    "R1\n(0h→6h)\nimmediate",
    "R2\n(6h→12h)\ndigest",
    "R3\n(12h→24h)\nfollow-up",
    "R4\n(24h→48h)\nwind-down",
]


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def load_data():
    trace   = pd.read_csv(DATA / "sim_agent_trace.csv")
    comments = pd.read_csv(DATA / "sim_comments.csv")
    return trace, comments


# ---------------------------------------------------------------------------
# 1. Agent activity timeline heatmap
# ---------------------------------------------------------------------------

def plot_activity_timeline(trace: pd.DataFrame):
    """Heatmap: agents (y) × rounds (x), colour = action_type."""
    agents = trace["agent_id"].unique()
    # Sort by archetype
    agent_meta = trace[["agent_id", "archetype", "broad_cohort"]].drop_duplicates()
    agent_meta = agent_meta.sort_values(["broad_cohort", "archetype", "agent_id"])
    agents_sorted = agent_meta["agent_id"].tolist()

    n_agents = len(agents_sorted)
    n_rounds = trace["round_id"].max() + 1

    # Matrix: count of non-observe actions per agent per round
    act_matrix = np.zeros((n_agents, n_rounds))
    for i, aid in enumerate(agents_sorted):
        sub = trace[(trace["agent_id"] == aid) & (trace["action_type"] != "observe")]
        for _, row in sub.iterrows():
            act_matrix[i, int(row["round_id"])] += 1

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(act_matrix, aspect="auto", cmap="YlOrRd",
                   vmin=0, vmax=max(act_matrix.max(), 1))

    ax.set_xticks(range(n_rounds))
    ax.set_xticklabels(ROUND_LABELS, fontsize=8)
    ax.set_yticks(range(n_agents))
    ax.set_yticklabels(agents_sorted, fontsize=7)

    plt.colorbar(im, ax=ax, label="# posts / replies")
    ax.set_title("Agent Activity Timeline — NVDA_Q3FY26 Pilot\n"
                 "(colour intensity = number of posts+replies per round)", fontsize=11)
    ax.set_xlabel("Simulation Round")
    ax.set_ylabel("Agent")

    # Cohort dividers
    cohort_order = ["long-horizon", "short-horizon", "info-seeking"]
    for cohort in cohort_order:
        idxs = [i for i, aid in enumerate(agents_sorted)
                if agent_meta.loc[agent_meta["agent_id"] == aid, "broad_cohort"].values[0] == cohort]
        if idxs:
            # Colour y-tick labels
            for idx in idxs:
                ax.get_yticklabels()[idx].set_color(COHORT_COLOURS[cohort])

    # Legend
    patches = [mpatches.Patch(color=c, label=l) for l, c in COHORT_COLOURS.items()]
    ax.legend(handles=patches, loc="upper right", fontsize=8,
              title="Cohort", title_fontsize=8)

    plt.tight_layout()
    path = OUT / "agent_activity_timeline.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 2. Agent interaction graph
# ---------------------------------------------------------------------------

def plot_interaction_graph(comments: pd.DataFrame, trace: pd.DataFrame):
    """Directed graph: nodes = agents, edges = reply-to relationships."""
    try:
        import networkx as nx
    except ImportError:
        print("  WARNING: networkx not installed, skipping interaction graph.")
        _plot_interaction_fallback(comments, trace)
        return

    agent_meta = trace[["agent_id", "archetype", "broad_cohort"]].drop_duplicates()
    agent_cohort = dict(zip(agent_meta["agent_id"], agent_meta["broad_cohort"]))
    agent_arch   = dict(zip(agent_meta["agent_id"], agent_meta["archetype"]))

    # Build comment-id → agent-id lookup
    cid_to_agent = dict(zip(comments["comment_id"], comments["agent_id"]))

    G = nx.DiGraph()
    # Add all agents as nodes
    for aid in agent_meta["agent_id"]:
        G.add_node(aid, cohort=agent_cohort.get(aid, "unknown"))

    # Add edges from reply relationships
    reply_rows = comments[comments["parent_id"] != comments["comment_id"]]
    for _, row in reply_rows.iterrows():
        target_agent = cid_to_agent.get(row["parent_id"])
        if target_agent and target_agent != row["agent_id"]:
            if G.has_edge(row["agent_id"], target_agent):
                G[row["agent_id"]][target_agent]["weight"] += 1
            else:
                G.add_edge(row["agent_id"], target_agent, weight=1)

    fig, ax = plt.subplots(figsize=(12, 10))

    if len(G.edges()) == 0:
        ax.text(0.5, 0.5, "No inter-agent replies recorded\n(all posts were new threads)",
                ha="center", va="center", fontsize=12, transform=ax.transAxes)
    else:
        pos = nx.spring_layout(G, seed=42, k=2.0)
        node_colours = [COHORT_COLOURS.get(agent_cohort.get(n, ""), "#888888") for n in G.nodes()]
        edge_weights = [G[u][v]["weight"] for u, v in G.edges()]

        nx.draw_networkx_nodes(G, pos, node_color=node_colours, node_size=300, ax=ax, alpha=0.85)
        nx.draw_networkx_labels(G, pos, font_size=6, ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color="#555555", arrows=True,
                               width=[0.5 + w * 0.5 for w in edge_weights],
                               alpha=0.6, ax=ax,
                               arrowstyle="-|>", arrowsize=12,
                               connectionstyle="arc3,rad=0.1")

    # Legend
    patches = [mpatches.Patch(color=c, label=l) for l, c in COHORT_COLOURS.items()]
    ax.legend(handles=patches, loc="lower right", fontsize=9, title="Cohort")

    ax.set_title("Agent Interaction Graph — NVDA_Q3FY26 Pilot\n"
                 "(directed edges = reply-to; edge thickness = reply count)", fontsize=11)
    ax.axis("off")

    plt.tight_layout()
    path = OUT / "agent_interaction_graph.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def _plot_interaction_fallback(comments: pd.DataFrame, trace: pd.DataFrame):
    """Fallback if networkx not available: bar chart of reply counts per agent."""
    fig, ax = plt.subplots(figsize=(10, 5))
    replies = comments[comments["parent_id"] != comments["comment_id"]]
    reply_counts = replies["agent_id"].value_counts()
    agent_meta = trace[["agent_id", "broad_cohort"]].drop_duplicates()
    colours = [COHORT_COLOURS.get(
        agent_meta.loc[agent_meta["agent_id"] == aid, "broad_cohort"].values[0]
        if len(agent_meta.loc[agent_meta["agent_id"] == aid]) > 0 else "", "#888")
        for aid in reply_counts.index]
    ax.bar(reply_counts.index, reply_counts.values, color=colours)
    ax.set_title("Reply Counts per Agent (interaction graph fallback)")
    ax.set_xlabel("Agent")
    ax.set_ylabel("Replies made")
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    path = OUT / "agent_interaction_graph.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 3. Stance trajectories
# ---------------------------------------------------------------------------

def plot_stance_trajectories(trace: pd.DataFrame):
    """Per-cohort stance distribution across rounds."""
    cohorts = ["long-horizon", "short-horizon", "info-seeking"]
    rounds  = sorted(trace["round_id"].unique())
    stances = ["bullish", "neutral", "bearish"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)

    for ax, cohort in zip(axes, cohorts):
        sub = trace[trace["broad_cohort"] == cohort]
        # Use posterior_stance_or_belief for end-of-round state
        bull_pct, neut_pct, bear_pct = [], [], []
        for r in rounds:
            r_sub = sub[sub["round_id"] == r]
            total = len(r_sub)
            if total == 0:
                bull_pct.append(0); neut_pct.append(0); bear_pct.append(0)
                continue
            bull_pct.append(100 * (r_sub["posterior_stance_or_belief"] == "bullish").sum() / total)
            neut_pct.append(100 * (r_sub["posterior_stance_or_belief"] == "neutral").sum() / total)
            bear_pct.append(100 * (r_sub["posterior_stance_or_belief"] == "bearish").sum() / total)

        ax.stackplot(rounds, bull_pct, neut_pct, bear_pct,
                     labels=["bullish", "neutral", "bearish"],
                     colors=[STANCE_COLOURS["bullish"],
                             STANCE_COLOURS["neutral"],
                             STANCE_COLOURS["bearish"]],
                     alpha=0.75)
        ax.set_title(cohort, fontsize=10, color=COHORT_COLOURS[cohort], fontweight="bold")
        ax.set_xlabel("Round")
        ax.set_xticks(rounds)
        ax.set_xticklabels([f"R{r}" for r in rounds], fontsize=8)
        ax.set_ylim(0, 100)

    axes[0].set_ylabel("% of agents with stance")
    handles = [mpatches.Patch(color=STANCE_COLOURS[s], label=s) for s in stances]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=9, title="Stance")
    fig.suptitle("Agent Stance Trajectories by Cohort — NVDA_Q3FY26 Pilot\n"
                 "(posterior stance at end of each round)", fontsize=12)
    plt.tight_layout(rect=[0, 0.08, 1, 1])
    path = OUT / "agent_stance_trajectories.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 4. Sample dialogues
# ---------------------------------------------------------------------------

def extract_sample_dialogues(comments: pd.DataFrame, n_threads: int = 5) -> str:
    """Find n_threads reply chains with at least 2 agents and format as readable dialogues."""
    lines = []
    lines.append("# Sample Agent Dialogues — NVDA_Q3FY26 Pilot\n")
    lines.append("> Generated by 08_observability.py from sim_comments.csv\n")
    lines.append("> Text is template-based (no LLM API). See AGENT_OBSERVABILITY_AUDIT.md.\n\n")

    cid_to_row = {row["comment_id"]: row for _, row in comments.iterrows()}

    # Find root posts that have at least one reply
    reply_rows = comments[comments["parent_id"] != comments["comment_id"]]
    roots_with_replies = set(reply_rows["parent_id"].unique())

    root_posts = comments[
        (comments["parent_id"] == comments["comment_id"]) &
        (comments["comment_id"].isin(roots_with_replies))
    ]

    # Pick diverse roots: prefer different archetypes and rounds
    chosen_roots = []
    seen_archetypes: set[str] = set()
    for _, root in root_posts.sort_values("round_id").iterrows():
        arch = root["archetype"]
        if arch not in seen_archetypes or len(chosen_roots) < n_threads:
            chosen_roots.append(root)
            seen_archetypes.add(arch)
        if len(chosen_roots) >= n_threads:
            break

    if len(chosen_roots) < n_threads:
        # Fill remaining with whatever is available
        remaining = root_posts[~root_posts["comment_id"].isin(
            [r["comment_id"] for r in chosen_roots])]
        for _, root in remaining.iterrows():
            chosen_roots.append(root)
            if len(chosen_roots) >= n_threads:
                break

    for idx, root in enumerate(chosen_roots[:n_threads]):
        lines.append(f"---\n\n## Dialogue {idx + 1}\n")
        lines.append(f"**Round:** {root['round_id']}  |  "
                     f"**Hours from event:** {root['hours_from_event']:.2f}h\n\n")

        # Show root post
        root_text = root["text"].strip()
        lines.append(f"**{root['agent_id']}** ({root['archetype']}, "
                     f"cohort: {root['broad_cohort']}, stance: `{root['stance']}`)\n\n")
        lines.append(f"> {root_text}\n\n")

        # Show replies (direct replies to this root)
        direct_replies = comments[
            (comments["parent_id"] == root["comment_id"]) &
            (comments["comment_id"] != root["comment_id"])
        ].sort_values("hours_from_event")

        for _, reply in direct_replies.iterrows():
            reply_text = reply["text"].strip()
            lines.append(f"**{reply['agent_id']}** ({reply['archetype']}, "
                         f"stance: `{reply['stance']}`) replies:\n\n")
            lines.append(f"> {reply_text}\n\n")

    lines.append("---\n\n*Note: All text is template-generated. "
                 "Agents do not read each other's actual text — "
                 "reply stance selection is rule-based. "
                 "See AGENT_OBSERVABILITY_AUDIT.md for full methodology.*\n")
    return "".join(lines)


# ---------------------------------------------------------------------------
# 5. Behaviour summary text
# ---------------------------------------------------------------------------

def write_behaviour_summary(trace: pd.DataFrame, comments: pd.DataFrame):
    lines = []
    lines.append("AGENT BEHAVIOUR SUMMARY — NVDA_Q3FY26 Pilot\n")
    lines.append("=" * 55 + "\n")
    lines.append(f"Generated by 08_observability.py\n\n")

    # Overall activity
    n_agents  = trace["agent_id"].nunique()
    n_actions = len(trace)
    n_posts   = len(comments[comments["depth"] == 0])
    n_replies = len(comments[comments["depth"] == 1])
    n_obs     = (trace["action_type"] == "observe").sum()

    lines.append(f"OVERALL\n-------\n")
    lines.append(f"  Agents:          {n_agents}\n")
    lines.append(f"  Trace rows:      {n_actions}\n")
    lines.append(f"  Posts (new):     {n_posts}\n")
    lines.append(f"  Replies:         {n_replies}\n")
    lines.append(f"  Observe (silent):{n_obs}\n\n")

    # Most active agents
    lines.append("MOST ACTIVE AGENTS (posts + replies)\n-------------------------------------\n")
    active = comments.groupby("agent_id").size().sort_values(ascending=False)
    for aid, cnt in active.head(10).items():
        arch = trace.loc[trace["agent_id"] == aid, "archetype"].iloc[0]
        cohort = trace.loc[trace["agent_id"] == aid, "broad_cohort"].iloc[0]
        lines.append(f"  {aid:15s}  {cnt:3d} comments  [{arch}, {cohort}]\n")
    lines.append("\n")

    # Stance distribution
    lines.append("STANCE DISTRIBUTION (sim comments)\n-----------------------------------\n")
    stance_counts = comments["stance"].value_counts()
    total = len(comments)
    for s, c in stance_counts.items():
        lines.append(f"  {s:8s}: {c:4d} ({100*c/total:.1f}%)\n")
    lines.append("\n")

    # Activity by round
    lines.append("ACTIVITY BY ROUND\n-----------------\n")
    round_labels = ["pre-event", "immediate", "digest", "follow-up", "wind-down"]
    for r in sorted(comments["round_id"].unique()):
        sub = comments[comments["round_id"] == r]
        label = round_labels[r] if r < len(round_labels) else ""
        bull = (sub["stance"] == "bullish").sum()
        bear = (sub["stance"] == "bearish").sum()
        neut = (sub["stance"] == "neutral").sum()
        lines.append(f"  R{r} ({label:10s}): {len(sub):3d} comments "
                     f"[bull:{bull} bear:{bear} neut:{neut}]\n")
    lines.append("\n")

    # Stance change summary
    lines.append("STANCE CHANGES OVER SIMULATION\n------------------------------\n")
    changed = trace[trace["prior_stance_or_belief"] != trace["posterior_stance_or_belief"]]
    if len(changed) > 0:
        change_summary = changed.groupby(
            ["prior_stance_or_belief", "posterior_stance_or_belief"]).size()
        for (p, q), cnt in change_summary.items():
            lines.append(f"  {p:8s} → {q:8s}: {cnt} times\n")
    else:
        lines.append("  No stance changes recorded.\n")
    lines.append("\n")

    # Archetype breakdown
    lines.append("ARCHETYPE BREAKDOWN\n-------------------\n")
    arch_stats = comments.groupby(["archetype", "stance"]).size().unstack(fill_value=0)
    for arch, row in arch_stats.iterrows():
        parts = ", ".join(f"{s}:{row.get(s, 0)}" for s in ["bullish", "bearish", "neutral"])
        lines.append(f"  {arch:22s}: {parts}\n")
    lines.append("\n")

    path = OUT / "agent_behaviour_summary.txt"
    path.write_text("".join(lines), encoding="utf-8")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# 6. AGENT_OBSERVABILITY_AUDIT.md
# ---------------------------------------------------------------------------

def write_observability_audit(trace: pd.DataFrame, comments: pd.DataFrame):
    n_agents   = trace["agent_id"].nunique()
    n_comments = len(comments)
    n_stances_changed = (
        trace["prior_stance_or_belief"] != trace["posterior_stance_or_belief"]
    ).sum()

    md = f"""# AGENT OBSERVABILITY AUDIT
## NVDA_Q3FY26 Pilot Simulation

*Generated by `08_observability.py`*

---

## 1. What this simulation IS and IS NOT

| Claim | Status |
|-------|--------|
| Full validated multi-agent simulation | ❌ NO |
| Structured generation pilot | ✅ YES |
| LLM-driven text generation | ❌ NO — template-based |
| Real Bayesian belief updates | ❌ NO — rule-based heuristics |
| Learned reply strategies | ❌ NO — rule-based with archetype biases |
| Tied to a real curated event | ✅ YES — NVDA_Q3FY26 (2025-11-19) |
| Uses synthetic/toy data from old pipeline | ❌ NO — only NVDA_Q3FY26 curated data used as ground truth |

**Honest summary:** This is a structured generation pilot where agents follow
deterministic rules with stochastic sampling. Behaviour is inspectable and
reproducible (seed=42). It is NOT a simulation where agents learn, reason,
or genuinely read each other's posts.

---

## 2. Simulation parameters

| Parameter | Value |
|-----------|-------|
| Event | NVDA_Q3FY26 (earnings 2025-11-19 21:00 UTC) |
| Archetypes | 9 (3 cohorts × 3 subtypes) |
| Agents | {n_agents} (3 per archetype) |
| Rounds | 5 |
| Total sim comments | {n_comments} |
| Stance changes recorded | {n_stances_changed} |
| Random seed | 42 |

---

## 3. Archetype and cohort design

Cohorts match the CLAUDE.md locked spec:

| Cohort | Archetypes |
|--------|-----------|
| long-horizon | valuation-focused, fundamentals-focused, buy-the-dip |
| short-horizon | momentum-following, event-reactive, profit-taking |
| info-seeking | uncertain, evidence-seeking, wait-and-see |

Each archetype has distinct:
- Initial stance probability weights (biased toward archetype's natural disposition)
- Activity schedule across rounds (e.g., event-reactive peaks in Round 1)
- Reply bias (probability of replying vs posting new content)
- Stubbornness parameter (resistance to stance update)

---

## 4. Text generation mechanism

**Method:** Template substitution. No LLM API calls.

Each archetype has 3–4 post templates per stance (bullish/bearish/neutral).
Template placeholders (`{{ticker}}`, `{{revenue}}`, `{{product}}`, `{{ceo}}`) are filled
with real NVDA_Q3FY26 context:
- `ticker` = NVDA
- `revenue` = $57B (from real data headline comment: "NVDA Quarterly Revenue $57 billion")
- `product` = Blackwell (NVIDIA's actual AI GPU product line for FY26)
- `ceo` = Jensen Huang

Reply templates are similarly structured: agree / disagree / question / add-context variants.

**Implication:** All text is structurally realistic but lexically repetitive.
MMD semantic metric will be adversely affected by template repetition.
JSD stance metric is more meaningful since stances are genuinely varied.

---

## 5. Belief/stance update mechanism

**Method:** Rule-based social pressure heuristic. NOT Bayesian inference.

Algorithm (per round, per agent):
```
1. Count bullish and bearish comments produced in the round
2. Compute pressure = (bull_count - bear_count) / total_count
3. Add event_shock = +0.30 in Round 1 (NVDA beat → positive shock)
4. update_probability = (1 - stubbornness) × |pressure| × 0.40
5. If random() < update_probability:
     - If pressure > 0.20: shift stance one step toward bullish
     - If pressure < -0.20: shift stance one step toward bearish
```

**What this does NOT do:**
- Agents do NOT read other agents' actual text
- There is no Bayesian prior updating
- There is no memory across rounds beyond the stance state
- Stance shifts are bounded (only one step per round: bearish→neutral or neutral→bullish)

---

## 6. Reply selection mechanism

**Method:** Rule-based with archetype-specific biases.

Rules (in priority order):
1. If no existing comments → always post new
2. If random() < `reply_bias` (archetype parameter) → attempt a reply
3. Reply target selection:
   - Event-reactive & momentum: prefer opposing stance (55% chance) for debate
   - Info-seeking archetypes: prefer neutral posts (50% chance)
   - Otherwise: random selection from all existing comments

**What this does NOT do:**
- Agents do NOT read the content of the target post
- Reply text is chosen based on agent's own stance vs target's stance tag
- No coherent conversational threading beyond stance-matching

---

## 7. Round structure

| Round | Hours from event | Context | Activity pattern |
|-------|-----------------|---------|-----------------|
| R0 | -2h to 0h | Pre-event speculation | Low–moderate |
| R1 | 0h to +6h | Immediate reaction | Highest (event-reactive peaks here) |
| R2 | +6h to +12h | Post-announcement digest | Moderate–high |
| R3 | +12h to +24h | Follow-up discussion | Moderate |
| R4 | +24h to +48h | Wind-down | Low (wait-and-see peaks here) |

---

## 8. Known weaknesses

1. **Template repetition:** With 3–4 templates per stance per archetype, agents of the
   same archetype will post near-identical text. This inflates MMD (real comments
   are lexically diverse; sim comments cluster tightly in embedding space).

2. **No genuine reading:** Agents do not process the semantic content of other posts.
   Reply coherence is simulated only by stance-tag matching, not argument comprehension.

3. **No memory:** Each round is independent. An agent cannot reference a previous round's
   discussion or track which specific agents they replied to.

4. **Hardcoded event shock:** The Round 1 bullish shock (+0.30) is manually set to
   reflect the NVDA earnings beat. This is an assumption, not a learned signal.

5. **Stance labels are provisional:** Simulated stance labels are ground truth by
   construction; real stance labels are keyword-based (see STANCE_LABEL_AUDIT.md).
   The JSD metric compares two imperfect label sources.

6. **No heterogeneous information:** All agents receive the same context template.
   Real investors see different news sources, have different entry prices, and
   process information differently.

7. **Small scale:** 27 agents producing ~100–150 comments is deliberately small
   for inspectability. Scaling may change distributional properties significantly.

8. **Reply tree is shallow:** Most replies are depth-1. Real Reddit threads can
   reach depth 5+. Structural metrics (if added later) would highlight this gap.

---

## 9. What the metrics can and cannot tell you

| Metric | What it measures here | Caveat |
|--------|-----------------------|--------|
| JSD stance | Distributional similarity of stance labels | Affected by provisional real labels |
| Wasserstein time | How closely sim matches real posting-volume profile | Sim uses 5 discrete rounds; real is continuous |
| MMD semantic | How close sim embeddings are to real embeddings | Template repetition artificially inflates MMD |

A small JSD is attainable by construction (sim stance weights seeded from real distribution).
MMD is the most honest discriminator: template text will always be semantically distinct
from real Reddit language.

---

## 10. Files produced

| File | Description |
|------|-------------|
| `data/processed/sim_agent_trace.csv` | One row per agent per round (all actions) |
| `data/processed/sim_comments.csv` | Comment-centric view (posts + replies only) |
| `outputs/agent_activity_timeline.png` | Heatmap of agent activity per round |
| `outputs/agent_interaction_graph.png` | Directed reply-to graph |
| `outputs/agent_stance_trajectories.png` | Stance evolution by cohort across rounds |
| `outputs/sample_agent_dialogues.md` | 3–5 readable example threads |
| `outputs/agent_behaviour_summary.txt` | Numerical summary statistics |
| `outputs/real_vs_sim_metrics.json` | JSD / Wasserstein / MMD scores |
| `outputs/real_vs_sim_summary.png` | Visual comparison chart |

---

*This document is part of the pilot transparency requirements.*
*Do not cite this simulation as a validated behavioural model.*
"""

    path = OUT / "AGENT_OBSERVABILITY_AUDIT.md"
    path.write_text(md, encoding="utf-8")
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("08_observability.py — Generating observability artefacts")
    print("=" * 60)

    trace, comments = load_data()
    print(f"  Loaded trace: {len(trace)} rows, comments: {len(comments)} rows")

    print("\n  [1/6] Activity timeline...")
    plot_activity_timeline(trace)

    print("  [2/6] Interaction graph...")
    plot_interaction_graph(comments, trace)

    print("  [3/6] Stance trajectories...")
    plot_stance_trajectories(trace)

    print("  [4/6] Sample dialogues...")
    dialogues_md = extract_sample_dialogues(comments, n_threads=5)
    path = OUT / "sample_agent_dialogues.md"
    path.write_text(dialogues_md, encoding="utf-8")
    print(f"  Saved: {path}")

    print("  [5/6] Behaviour summary...")
    write_behaviour_summary(trace, comments)

    print("  [6/6] Observability audit...")
    write_observability_audit(trace, comments)

    print("\nDone.")


if __name__ == "__main__":
    main()
