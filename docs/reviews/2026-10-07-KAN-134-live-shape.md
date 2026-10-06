# KAN-134: bounded HDX HAPI live shape acceptance

The approved live probe completed on 7 October 2026 BST, from
6 October 23:34:20.587 to 23:34:24.894 UTC. It used the actual `HapiProvider`,
feed HTTP client and frozen `EvidenceItem` codec with the fixed Sudan subject,
2025-01-01 to 2026-10-06 period and a maximum of 20 rows per topic.

| Topic | HTTP | Response bytes | Valid frozen rows |
| --- | --- | --- | --- |
| Internally displaced people | 200 | 8,440 | 20 |
| Food security | 200 | 8,340 | 20 |
| Operational presence | 200 | 9,751 | 20 |

All 60 typed round trips preserved quantity/unit, reference period,
administrative level, dataset/resource and provenance. Exactly three bounded
requests were made, with no redirects, retries, pagination or conflict/ACLED
endpoint. The child exited 0, clients closed and the owned process was reaped.
The parent took 48.093 seconds including its source/runtime checks.

The reviewed runner was prepared against `218ce580`. All 72 application files
it loaded and its dependency lock are unchanged at deployed main `33990205`.
The only intervening backend source change was API router ordering, outside
the runner's imports. This is live shape evidence for the current provider,
not proof of complete geographic coverage, research accuracy or independent
corroboration of a redistributed source.

Existing fixture validation distinguishes empty, failed and unavailable outcomes
and excludes ACLED-derived rows as independent conflict corroboration. This
live check completes the outstanding KAN-134 validation; KAN-134 and its
coordinating KAN-107 epic are Done. No production configuration was changed.

Private evidence references:

- Result SHA-256:
  `0bff77d85889a2d969240170cd27d1dc3ed6581a5f86b4d51f3f9b2453b87c29`.
- Safe summary SHA-256:
  `a51dbd11632523034cbf930880cfaac2317d64ddc97d37d641b7c7d7db395926`.
- Reviewed runner manifest:
  `c5cebfbcb0ae442e2d403651fa4f0b5e503b97f30ff6cee6b92ffd04fca52498`.

The identifier, contact transmission and raw responses are absent from published
evidence. Official source semantics are documented by HDX for
[affected people](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/affected_people/),
[food security](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/food_security_nutrition_and_poverty/)
and [operational presence](https://hdx-hapi.readthedocs.io/en/latest/data_usage_guides/coordination_and_context/).
