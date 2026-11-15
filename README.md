# Agent Brief

Agent Brief is a small evidence-first research agent. Give it a question and a list of public webpages; it plans keywords, reads the supplied sources, selects relevant sentences, records failed sources, and writes a cited Markdown brief plus a machine-readable run record.

It does not invent uncited findings or silently ignore source failures. It deliberately only uses the URLs you provide.

## Run

```bash
python -m pip install -e .
agent-brief "What changed in the project?" \
  --source https://example.com/announcement \
  --source https://example.com/changelog \
  --out briefing
```

The output directory must not already exist. It contains `brief.md` and `run.json`.

## Test

```bash
python -m pip install -e .
python -m pytest
```

## Design

The workflow is explicit: plan → gather → extract → cite → write. Source fetching is bounded to 1.5 MB per HTTP(S) page, supports HTML and plain text, and records any per-source failure in the result. Extraction is keyword based so the output stays inspectable and deterministic; it is a simple agentic workflow rather than a model-backed autonomous system.

## License

MIT

