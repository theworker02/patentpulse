# Hub viewer fix

The published dataset card still advertises an `unspecified` split:

```yaml
  - split: unspecified
    path: data/unspecified/*.parquet
```

There are **zero** unspecified rows in this snapshot, and no files under `data/unspecified/`. Hugging Face Dataset Viewer then fails with:

```text
Couldn't infer the same data file format for all splits.
Got {'train': ('parquet', {}), 'validation': ('parquet', {}),
     'test': ('parquet', {}), 'unspecified': (None, {})}
```

`load_dataset("theworker02/patentpulse")` can still work for clients that only bind the splits that exist. The Viewer, search, and statistics endpoints do not.

## Pipeline fix (this packet)

`patentpulse.hf_release.dataset_card_data_files` now emits globs only for splits with records. New exports will not regress.

## Live Hub patch (operator)

Replace the `configs:` block in the Hub `README.md` with:

```yaml
configs:
- config_name: default
  data_files:
  - split: train
    path: data/train/*.parquet
  - split: validation
    path: data/validation/*.parquet
  - split: test
    path: data/test/*.parquet
```

Do not add `unspecified` until a release actually writes that directory.
