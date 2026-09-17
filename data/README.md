# Local corpus layout

This directory holds the growing PatentPulse dataset. Git tracks the layout, not the bulk files.

```text
data/
├── manifest.json     # Authority for which weekly USPTO archives were ingested
├── raw/
│   ├── grants/       # Temporary `ipg*.zip` grant archives
│   └── applications/ # Temporary `ipa*.zip` application archives
└── processed/
    ├── patents.db    # Normalized SQLite corpus
    └── patents.jsonl # Hugging Face-friendly JSON Lines
```

`python -m patentpulse.ingest status` reports how far the backfill has progressed.
Do not delete `manifest.json` if you intend to resume a download.
