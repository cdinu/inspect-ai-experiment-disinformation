# Advanced scenarios (real sources)

These scenarios are generated from published real-world misinformation datasets by
`scripts/fetch_advanced.py` and frozen here as one Markdown file per scenario, in the
same structure as `data/scenarios`. They are read by the same loader. Regenerate with:

```sh
just fetch-advanced            # all sources, 3 per label
just fetch-advanced liar 5     # one source, 5 per label
```

## How the source label becomes a rubric

Each source labels a different thing. The fetch script translates that label into the
project's epistemic-discipline rubric and records the original label in `## About`:

| Source | Native label | What the scenario tests |
| --- | --- | --- |
| CLIMATE-FEVER | claim vs. evidence (supported / refuted / not enough info / disputed) | conveying support, flagging refutation, preserving uncertainty |
| LIAR | PolitiFact rating (pants-fire … true) | not laundering unverified political claims as fact |
| EUvsDisinfo | article class (disinformation / trustworthy) | provenance discipline from metadata alone (no article text) |
| ConspirED | CONSPIR cognitive trait | not amplifying conspiratorial framing |

## Neutrality of the scenario

The `## Scenario` shown to the model carries only the raw material. The source's
verdict, the LIAR party affiliation, and all provenance live in `## About`
(grader-only — the loader never puts it in the prompt) and in the `source_*` front
matter. This keeps the model from being told the answer or primed for a side.

## Provenance and licensing

This material references real people, outlets, and geopolitical topics, so it crosses
the "no real parties/politicians/elections" boundary that the synthetic set in
`data/scenarios` keeps. That is intentional and is why the advanced set is separate.

| Source | Reference | License | Notes |
| --- | --- | --- | --- |
| CLIMATE-FEVER | [arXiv:2012.00614](https://arxiv.org/abs/2012.00614), [HF `tdiggelm/climate_fever`](https://huggingface.co/datasets/tdiggelm/climate_fever) | Evidence quoted from Wikipedia, CC BY-SA 3.0 | Scientific claims; non-partisan |
| LIAR | [arXiv:1705.00648](https://arxiv.org/abs/1705.00648), [HF `ucsbnlp/liar`](https://huggingface.co/datasets/ucsbnlp/liar) | Research use | Real US politicians; party affiliation withheld from the scenario |
| EUvsDisinfo | [arXiv:2406.12614](https://arxiv.org/abs/2406.12614), [Zenodo 10514307](https://doi.org/10.5281/zenodo.10514307) | CC BY-4.0 | Metadata only (no article body); pro-Kremlin disinformation topics |
| ConspirED | [arXiv:2508.20468](https://arxiv.org/abs/2508.20468), [github.com/UKPLab/conspired](https://github.com/UKPLab/conspired) | Data CC BY-4.0 | Excerpts may reference real figures/events |

If you publish Inspect logs from these scenarios, review them first: they contain real
names and topics, and the grader target includes the withheld source verdict.
