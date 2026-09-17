# PatentPulse data rights and reuse notice

PatentPulse distributes a normalized, machine-readable representation of public
USPTO patent grants and published patent applications. This notice applies to
published PatentPulse dataset snapshots (for example, the Parquet files in a
Hugging Face dataset repository). It does **not** replace the USPTO's terms or
grant rights in material owned by another party.

## Dataset label

Published snapshots must use Hugging Face's `other` license label. They must
link to this notice and to the [USPTO Terms of Use](https://www.uspto.gov/terms-use-uspto-websites).
The repository-level [MIT License](LICENSE) applies only to PatentPulse source
code and its original documentation.

## What PatentPulse permits

PatentPulse does not impose an additional non-commercial, no-derivatives, or
no-training restriction on a snapshot. In the United States, the USPTO says
that most government-produced material is public domain and may be copied and
distributed with appropriate acknowledgement. Subject to applicable law and
third-party rights, users may copy, transform, redistribute, index, analyze,
and use the dataset for machine-learning research and training.

## Important limits

- Patent documents can contain applicant-authored text, figures, incorporated
  material, and other content that may be protected by copyright or other
  rights. PatentPulse cannot grant those rights.
- The USPTO reserves the right to assert copyright protection internationally.
  Rights and text-and-data-mining exceptions vary by jurisdiction.
- The dataset is not legal advice and must not be treated as proof of validity,
  infringement, freedom to operate, patentability, ownership, or enforceability.
- Do not imply USPTO endorsement or use its seal, logo, or branding.

## Required acknowledgement

When redistributing a PatentPulse snapshot or publishing work materially based
on it, retain this notice and acknowledge the source as:

> Source: United States Patent and Trademark Office (USPTO), processed by
> PatentPulse.

Also preserve the release's `release_manifest.json` where practical so users
can identify the exact snapshot and its upstream provenance.

## No warranty

The data is provided as-is. Extraction can omit or normalize XML content, and
weekly releases can contain corrections or changes. Users are responsible for
independent rights review and for validating records against official USPTO
sources when accuracy matters.
