# Seminar Q&A Prep

Companion to `SEMINAR_DECK.md`. Likely questions grouped by theme, with short defensible answers. Every claim here is consistent with `METHOD_TRUTH_AUDIT.md` and `UPDATED_REAL_GPU_RUN_AUDIT.md`.

**General rule:** If a question pushes for an overclaim, redirect to "this is a validation framework, not a solved simulator," and cite the specific metric and number rather than a vague impression.

---

## A. Method clarifications

**Q1. What exactly is an "agent" in your setup?**
> One independent one-shot generation. A persona description and an event card go into a Qwen model, and one short Reddit-style comment comes out. Agents don't keep memory, don't reply to each other, and don't browse anything. It's deliberately the simplest possible agent design — a per-comment persona conditioning, not a long-running autonomous process. That's a feature for the proposal stage, because any future richer system has to beat this simple baseline.

**Q2. Why Qwen and not GPT-4 or Claude?**
> Three reasons. One, open-weight models run locally on UQ Rangpur A100s, which keeps data inside the university environment — important for an ethics-sensitive project. Two, smaller models like Qwen2.5-3B and Qwen3.5-2B are realistic targets for downstream research; not everyone has GPT-4 budget. Three, the project's contribution is the *measurement framework*, not the model choice; if it works for Qwen, the same framework can later be used to evaluate GPT-4 or Claude as drop-in baselines.

**Q3. How are simulated comments scheduled in time?**
> External scheduler, not the LLM. There's a function `assign_hour(cohort, rng)` that samples a Gaussian per cohort — short-horizon N(2, 3), long-horizon N(10, 10), info-seeking N(6, 6) — clipped to a plausible range. The LLM never sees the timestamp. So Wasserstein-1 measures whether *that scheduler* is calibrated to real Reddit activity, not whether the LLM behaves realistically in time. I flag this explicitly as a limitation.

**Q4. Why are temperatures and prompts identical in Wasserstein values?**
> Because the timestamp doesn't depend on temperature or prompt. The scheduler runs before generation, so the only thing that changes Wasserstein is the random seed — 3.06 hours for seed 42, 3.13 for seed 123, across all 14 runs. That's expected, not a bug, but it's a limitation I'm honest about.

---

## B. Metric design

**Q5. Why MMD specifically? Why not BERTScore or MAUVE?**
> MMD is set-to-set in a fixed embedding space — exactly the comparison I need: two corpora, no pairwise alignment, no reference sentences. BERTScore is sentence-level overlap, which doesn't make sense when I'm comparing one set of 108 simulated comments to 2400 real comments. MAUVE is similar in spirit to MMD but tuned for long-form text; for short Reddit comments MMD with RBF kernel and the median heuristic for bandwidth is more standard and easier to interpret. I do an embedding robustness check by recomputing MMD with Qwen3-Embedding-0.6B; the ranking of finalists is preserved.

**Q6. JSD on three categories seems crude. Defense?**
> Bullish / bearish / neutral is the standard granularity for investor sentiment, and the same rule-based labeler is applied to both real and simulated text — so any keyword bias cancels at the distributional level. I also hand-audited 100 NVDA comments and report Cohen's kappa of 0.45 with overall accuracy 65%. That's "moderate" agreement in Landis-Koch terms — good enough for distributional comparison, not good enough for individual classifications. I'm explicit about this limitation.

**Q7. Why not just train a classifier for stance?**
> Three reasons. One, training a stance classifier on a different domain (e.g. SemEval Twitter stance) and applying it to Reddit earnings discussion would introduce its own bias, and I'd then have to validate *that* labeler. Two, the rule-based approach is *transparent and reproducible* — you can read the keyword list and decide whether you trust it. Three, the validated kappa of 0.45 is enough for JSD on a three-class distribution; the marginal benefit of a learned classifier isn't worth the validation overhead at the proposal stage.

**Q8. What does the grounding metric actually capture?**
> Whether the comment text mentions earnings facts: revenue, EPS, guidance, the Blackwell product, valuation language, or post-event price action. It uses six keyword categories with a threshold rule — grounded if three or more categories match, or two plus a number. It's a keyword heuristic, not factual correctness, but the asymmetry is meaningful: real Reddit hits 2.5% grounded, the template baseline hits 52%, and the best LLM finalist hits 57%. The LLM is over-grounding by an order of magnitude.

---

## C. Results interpretation

**Q9. The best run still has MMD 0.065. Is that good?**
> It's the lowest in the 14-run grid, and it's 50% smaller than the previous best at n=27 (0.10). The real-vs-real split-half floor from bootstrap is roughly 0 with a 95% interval that doesn't cross 0.001. So 0.065 is a real, measurable gap — the simulator and real Reddit are *not* the same distribution. I report it as "closer than the template baseline at 0.148, but still not in the noise floor." Honest framing.

**Q10. Why does Qwen3.5-2B beat Qwen2.5-3B even though it's smaller?**
> Two factors. Qwen3.5 is a newer model architecture, and P2 (the behaviour-first prompt) gives it more freedom to vary tone and stance. The combination works: P2_V1 with Qwen3.5-2B tops every Qwen2.5-3B + P0_V0 row at matched temperature on both JSD and MMD. The prompt is doing more work than the parameter count.

**Q11. Why does grounding go down as temperature goes up?**
> Higher temperature spreads probability mass over more tokens, so the model is less likely to produce the "expected" earnings facts and more likely to produce off-topic or hedged content. That improves MMD (more semantic spread, closer to real Reddit) but reduces grounding. It's the trade-off direction the proposal predicted: more behavioural realism comes at the cost of factual coverage.

**Q12. So is temperature 1.1 the answer?**
> Within the conditions tested, yes — on semantic similarity. But it's still 22× over-grounded relative to real Reddit, and it's only one seed pair. The honest answer is that temperature 1.1 is the *best of what we tested*, not "the answer." That's the difference between a benchmark study and a solved simulator.

---

## D. Limitations and overclaiming

**Q13. The simulator is still very different from real Reddit. Is this project a failure?**
> No, because the project framing is *validation*, not *solving*. A weak result is still useful: I've quantified exactly where current open-weight LLMs fail — they over-ground by 20×, they produce too much directional stance, and their semantic distributions are above the real-vs-real noise floor. Future work can target those specific gaps. That's much more valuable than a paper that says "our LLM agent sounds realistic."

**Q14. You only tested one event. How do you know it generalises?**
> I don't yet, and the proposal says so. AAPL cross-event validation is scheduled for Semester 2. AAPL is small (n=383) but clean — 98% retention — which makes it a good transfer test. If the NVDA-tuned finalists generalise to AAPL, that's strong evidence the framework is event-agnostic. If they don't, that's a useful negative result.

**Q15. Why not just use META as the second event?**
> META lost 76% of comments to wrong-company contamination during curation — only 344 comments survive across 4 threads. That's too narrow and too small for reliable metric comparison. I keep META as an exploratory stress-test only.

**Q16. Could you test more models, more prompts, more temperatures?**
> Yes, and the proposal acknowledges that. The current scope is locked at two finalist conditions, four temperatures, two seeds — 14 runs total — to keep the comparison interpretable and reproducible within the capstone timeline. Broader sweeps are future work, not this thesis.

---

## E. Ethics, data, and replicability

**Q17. Is there any ethics risk with scraping Reddit?**
> Reddit's public API explicitly allows research use, and I follow conservative practice: no usernames stored, no raw comment text released, only aggregate metrics and figures. Fiesler and Proferes have shown that public-data research still has ethical responsibilities even when technically permissible, so I default to aggregate reporting. The proposal section 10.2 covers this in detail.

**Q18. Is this a trading system?**
> No, explicitly not. The project measures distributional similarity of public discussion. It doesn't predict prices, doesn't recommend trades, doesn't deploy bots. Even if results were much stronger, that would still not justify standalone trading use.

**Q19. Could someone reproduce this?**
> Yes. The data collection script is pinned to a Reddit JSON API call with hardcoded subreddits and a defined event window. The curation decisions are an explicit Python list with one-line reasons per thread. The prompts are stored verbatim in the script. The stance labeler is a public regex list. The Qwen weights are on Hugging Face. Seeds are fixed (42, 123). Every metric computation is in `04_compute_metrics.py`. The hardest dependency is GPU access, which UQ Rangpur provides.

---

## F. Likely curveballs

**Q20. Why does Wasserstein never change across temperatures? Isn't that suspicious?**
> It's expected by design. The timestamps come from `assign_hour(cohort, rng)` *before* generation, and the LLM never sees the timestamp. So Wasserstein only measures the calibration of the scheduler, not the LLM's temporal behaviour. I flag this on slide 7 as a known limitation. It also means Wasserstein is mostly invariant across temperature and prompt and only varies with seed.

**Q21. The stance labeler missed 36% of bullish comments in your audit. Doesn't that invalidate JSD?**
> It biases individual classifications, but JSD is computed at the *distributional* level — same labeler applied to real and simulated. So if the labeler systematically pushes a bullish comment into neutral, it does that on *both* sides of the comparison, and the JSD difference cancels. The hand-audit confirms this is mostly the failure mode: short positive reactions go to neutral. It's not random noise, it's a consistent conservative bias.

**Q22. What if I asked you to run on a completely different event right now?**
> The pipeline is parameterised — I can swap the event card (event time, summary, ticker) in maybe an hour, then re-collect Reddit data which is the slow part. The metrics and prompt scripts are event-agnostic. The constraint is data collection time, not code changes.

**Q23. Could you explain the temperature trade-off in one sentence?**
> Higher temperature gives the LLM more sampling freedom, which broadens the semantic distribution (MMD improves) but reduces how often the model dutifully repeats the earnings facts (grounding drops) — the simulator becomes more like a real noisy investor and less like an analyst report.

**Q24. What would change your mind that this approach works?**
> If a future configuration brings MMD into the real-vs-real bootstrap interval (currently around 0 to 0.001) *and* drops grounding to within 5 percentage points of real Reddit (~2-7%) *and* keeps JSD under 0.1 *and* this holds across at least two events with different temporal profiles. Right now we're at MMD 0.065, grounded 57%, JSD 0.41 — clearly not there yet. The framework would tell us when we get there.

---

## Quick numbers to memorise for the talk

| Quantity | Value |
|----------|-------|
| Real NVDA curated comments | **2403** |
| Best finalist MMD | **0.0653** |
| Best finalist condition | Qwen3.5-2B + P2_V1 + tau=1.1 + s=123 |
| Best finalist grounded % | **57.4%** |
| Real Reddit grounded % | **2.5%** |
| Template baseline grounded % | 52% |
| Real-vs-real MMD floor | ~0 (95% CI [-0.001, 0.001]) |
| Stance hand-audit κ | **0.448** |
| Number of finalist runs | **14** (n=108 each) |
| AAPL retention | 98% |
| META retention | 24% |

If you blank on a number, **say "let me check the table"** and don't guess. The audience is supportive; making up a number is the only way to lose credibility.
