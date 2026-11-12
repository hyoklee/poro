# poro

An [LLM wiki](llm-wiki.md) for the **PoroTomo** distributed acoustic sensing dataset
(Brady Hot Springs, Nevada; [GDR submission 980](https://gdr.openei.org/submissions/980),
DOI 10.15121/1778858, CC BY 4.0) and for how IOWarp's Context Assimilation Engine ingests it.

- `wiki/` — the LLM-maintained knowledge base; start at [wiki/index.md](wiki/index.md).
- `cae/` — the OMNI files, runtime configs and drivers for the CAE experiments; see [cae/README.md](cae/README.md).
- `wiki/CLAUDE.md` — the schema the maintaining agent follows.
- `claude.md` — standing instructions for the agent working in this repo.
- `llm-wiki.md` — the pattern this repo instantiates.

Structure follows [hyoklee/NeuroFAIR](https://github.com/hyoklee/NeuroFAIR).
