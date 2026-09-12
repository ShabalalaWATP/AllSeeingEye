# MITRE ATT&CK actor reference

`enterprise_actors.json` is a generated projection of the official Enterprise
ATT&CK v19.2 STIX release, dated 5 August 2026 and retrieved on 12 September 2026.
It contains 176 non-revoked, non-deprecated intrusion-set records and 4,628 unique
group-to-technique references. These are historical records, not assertions that
the groups are currently active. Associated names describe source-reported
overlaps, not exact identity equivalence.

Source: [pinned Enterprise release](https://raw.githubusercontent.com/mitre-attack/attack-stix-data/6cda5ad8462c79e14fbb872f4e09059b18e0cfc4/enterprise-attack/enterprise-attack-19.2.json).
Source SHA-256: `dc1639caa5501d720e280cf1cbd8fbe009884a0c9b3e6e9ed9d0c25166c3d8f4`.

The loader performs no network requests. The source admission identifier is
`mitre_attack`. Source controls must be checked when releasing reference data or
derived mentions. Descriptions preserve shortened source wording with presentation
and citation markup removed. Official group links provide the full context and
citations. Technique counts include directly linked, non-revoked, non-deprecated
techniques and sub-techniques only. Matching detects explicit long names or
numbered actor designators, excluding shared aliases. It never confirms attribution.

To update, download a release and its licence from the same full upstream commit,
then run `scripts/import_cyber_actors.py` through the backend uv environment with
the source file, `--commit` and `--retrieved-at`. Review the generated diff and
update this provenance note and release-specific tests. The importer is offline
and fails when byte, object or actor limits are exceeded.

MITRE's copyright notice and complete reuse licence are preserved in
[LICENSE.txt](LICENSE.txt), with attribution embedded in the catalogue.
