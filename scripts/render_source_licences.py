"""Render the licence register from reviewed metadata, without contacting providers.

Run from any directory. --check detects stale documentation without writing files.
This command never discovers sources or assigns rights; review the JSON explicitly.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "backend/src/ase/resources"
TARGET = ROOT / "docs/SOURCE_LICENCES.md"

INTRO = """# Source licences and attribution register

KAN-194 records source rights and current code defaults at revision
`13efceef48efbc6d5f2895e60c55076db5d40e3f`, inspected on 9 October 2026.
This is a due-diligence register, not legal advice, a signed provider agreement,
or approval to enable a source. Contentious interpretations require legal review.
KAN-194 changed no runtime configuration or provider permission. KAN-195 adds
the opt-in runtime controls and the `map:os_maps` catalogue entry described below;
provider permission is still a separate requirement.
The KAN-184 YouTube embed-host inventory and its provider evidence were reconciled
on 10 October 2026. Other policy rows retain their individual review dates.

## Coverage and evidence limits

Every backend catalogue identity is listed below, including optional/keyed feeds,
on-demand research, all camera providers, map layers and packaged reference assets.
The completeness test takes the union of supported credential configurations so
that missing keys cannot hide a source. A row is not proof of licensing clearance.

The machine-readable inputs are packaged with the backend:
[source_licences.json](../backend/src/ase/resources/source_licences.json) and
[source_licence_policies.json](../backend/src/ase/resources/source_licence_policies.json).
Join a source's `policy` to `policies[policy]` for terms, dates, commercial and
hosted status, attribution, redistribution, risk and action. `source_url` is a
discovery/provenance link, not a substitute for `terms_url`. Unknown terms remain
null. `additional_policies` links enrichment providers whose conditions also apply;
the primary row's status never overrides those additional conditions.
`upstream_licence_note` preserves an existing code claim as an unverified lead.
KAN-195 adds explicit `commercial_use`, `attribution_required` and `licence_ref`
fields to each source row. The runtime validates source classifications against
every primary and additional provider's `commercial_use_policy`. These are
deployment decisions, separate from the researched rights statuses below.
The metadata enforcement marker is `commercial_mode_opt_in`; the default setting
remains off. KAN-165 owns the public attribution presentation.
Consumers must not interpret unknown or
permission-required records as approved, or treat conditional records as proof
that this deployment satisfies the conditions.

`terms_checked` means the cited terms were inspected, not that an agreement exists.
`partial_review` identifies narrower evidence or unresolved product rights.
`lookup_blocked` dates an inaccessible lookup; `lookup_inconclusive` dates a
search that did not establish applicable terms. Neither has a verification date.
Their links identify the attempted terms page or provider discovery page, not a
verified grant. `not_reviewed` has no terms-check or attempted-lookup date.
All dates use UTC. The code inventory date is separate from all of these.
`per_item_required` is a mixed/user-supplied content boundary with no blanket
provider grant. Each item's original rights and owner must be assessed separately.
For unchecked rows the missing primary terms link and date are outstanding work,
not a fabricated verification. Review the linked provider and exact product.

## Priority decisions for Alex

1. Obtain permission or replace EOX 2024 for a commercial offering. `hybrid` is
   the initial basemap outside commercial mode and includes this imagery. Commercial
   mode blocks it in selection, saved-map previews and image exports. The image-export declaration
   does not grant browser display or downstream image rights.
2. Resolve Cloudflare Radar and OONI non-commercial restrictions. Radar's token-only
   live/attack paths differ from its acknowledgement-gated research paths.
3. Review Telegram collection and AI use urgently against its current content
   terms. Review YouTube's refresh/deletion rules against frozen evidence and exports.
4. Obtain publisher rights for The Independent and CNA; audit other RSS publishers
   separately. RSS availability, a link or an excerpt limit does not grant reuse.
5. Keep DeepState API permission separate from the visual-content licence. Review
   ACLED's actual account agreement and permitted external transformations.
6. Complete per-camera owner/host rights and the remaining unverified products
   before treating any of them as commercially cleared. IODA's unverified terms must
   be resolved; its existing live feeds have different gates from research.
7. Obtain ISW's written permission for analytical/map/dataset integration. Check
   purpose restrictions as well as commercial status: Pennsylvania's documented
   camera programme is for current traffic information, which does not establish
   permission for an OSINT evidence archive.

[Unsent permission requests](source-audit/KAN-194-permission-requests.md) are for
Alex to review and send. [Replacement candidates](source-audit/KAN-194-replacements.md)
describe commercially usable options and their remaining conditions. adsb.fi,
Reddit, Open-Meteo, Global Fishing Watch and OpenSanctions have supplementary
records because they are not backend catalogue entries at this revision.

## Current defaults and row key

Defaults describe clean code configuration, not the running deployment or a
licensing decision. `scheduled` feeds also depend on `ASE_FEEDS_ENABLED`,
`ASE_FEEDS_DISABLED`, credentials where shown, and administrator source controls.
`on_demand` means an available request path, not background collection or default
display. `available_asset` means a packaged/reference asset is available; this does
not imply that its map overlay is selected. `off_until_configured` identifies a
missing prerequisite; `off_until_selected` is an initially unselected layer.
Optional credentials can raise limits without disabling public access. The
initial hybrid base map uses EOX imagery and OpenFreeMap labels. User preferences
can change that choice. Uploads and combined reports retain per-item restrictions.

In the rights column, **C** is commercial use and **H** is hosted/multi-user use:
`conditional` requires the cited conditions and deployment review;
`permission_required` has no verified project-specific grant; `unknown` is
unresolved. The linked policy supplies the row's attribution and redistribution
requirements. Actions are recommendations, not changes already made. A setting,
API key, login, paid plan or acknowledgement alone is not a copyright licence.

"""


def cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def render() -> str:
    metadata = json.loads((RESOURCES / "source_licences.json").read_text(encoding="utf-8"))
    policies = json.loads((RESOURCES / "source_licence_policies.json").read_text(encoding="utf-8"))[
        "policies"
    ]
    sources = metadata["sources"]
    counts = Counter(policies[row["policy"]]["review_status"] for row in sources)
    out = [
        INTRO,
        f"Inventory: **{len(sources)} source identities**. Terms status by source: ",
    ]
    out += [
        ", ".join(f"{name}: {count}" for name, count in sorted(counts.items())),
        ".\n",
    ]
    for family in sorted({row["family"] for row in sources}):
        out += [
            f"\n## {family.replace('_', ' ').capitalize()}\n\n",
            "| Source ID and discovery link | Terms and check | C / H | "
            "Attribution / redistribution | Current default and gates | Risk and action |\n",
            "| --- | --- | --- | --- | --- | --- |\n",
        ]
        for row in sources:
            if row["family"] != family:
                continue
            policy = policies[row["policy"]]
            name = cell(row["name"])
            link = f"[{name}]({row['source_url']})" if row["source_url"] else name + " (per-item)"
            if row["source_url_kind"] == "catalogue_provenance_only":
                link += " (catalogue provenance only)"
            check = policy["terms_checked_on"] or (
                "attempt " + policy["lookup_attempted_on"]
                if policy["lookup_attempted_on"]
                else "not checked"
            )
            evidence_label = "terms/evidence" if policy["terms_checked_on"] else "attempted page"
            terms = (
                f"[{evidence_label}]({policy['terms_url']})"
                if policy["terms_url"]
                else "terms unverified"
            )
            gate = "; ".join(row["gating_flags"]) or "No source-specific prerequisite recorded"
            policy_links = "; ".join(
                f"[{key}](#policy-{key})" for key in [row["policy"], *row["additional_policies"]]
            )
            out += [
                (
                    f'| <a id="source-{row["id"]}"></a>`{row["id"]}` {link} | '
                    f"{terms}; {policy['review_status']}; {check} | "
                    f"{policy['commercial_use']} / {policy['hosted_multi_user_use']} | "
                    f"{policy_links}; deployment: {row['commercial_use']} | "
                    f"{row['current_default']}; {cell(gate)} | {policy['risk']}; "
                    f"{', '.join(policy['actions'])}; {cell(row['source_specific_action'])} |\n"
                )
            ]
    out += [
        "\n## Supplementary sources\n\n",
        "These are reviewed historical/candidate providers, "
        "not extra active catalogue entries.\n\n",
        "| Provider | Status | Policy |\n| --- | --- | --- |\n",
    ]
    for row in metadata["supplementary_sources"]:
        out += [f"| {row['id']} | {row['status']} | [{row['policy']}](#policy-{row['policy']}) |\n"]
    out += [
        "\n## Policy details\n\n",
        "Policy text is shared to keep repeated source rows consistent. "
        "Inspect each exact product and deployment before relying on it.\n",
    ]
    for key, policy in sorted(policies.items()):
        out += [
            f"\n### Policy {key}\n\n",
            f"**{policy['name']}**: {policy['licence']}.\n\n",
        ]
        if policy["terms_url"]:
            label = "Primary terms/evidence" if policy["terms_checked_on"] else "Attempted page"
            out += [f"[{label}]({policy['terms_url']}). "]
        out += [
            f"Status: `{policy['review_status']}`. "
            f"Checked: {policy['terms_checked_on'] or 'not verified'}. ",
            f"Attempted: {policy['lookup_attempted_on'] or 'not attempted'}.\n\n",
            f"Commercial: `{policy['commercial_use']}`. "
            f"Hosted/multi-user: `{policy['hosted_multi_user_use']}`.\n\n",
            f"Commercial deployment policy: `{policy['commercial_use_policy']}`.\n\n",
            f"Attribution: {policy['attribution']}\n\n"
            f"Redistribution: {policy['redistribution']}\n\n",
            f"{policy['notes']}\n\nRisk: {policy['risk']}. "
            f"Action: {', '.join(policy['actions'])}.\n",
        ]
        if policy["additional_terms_urls"]:
            out += [
                "\nRelated evidence: ",
                "; ".join(
                    f"[reference {n}]({url})"
                    for n, url in enumerate(policy["additional_terms_urls"], 1)
                ),
                ". These links are not separate verification dates.\n",
            ]
    out += [
        "\n## Camera host review queue\n\n",
        f"All {len(metadata['camera_hosts'])} configured media/frame/legacy-frame hosts "
        "retain the ",
        "[camera-owner-rights](#policy-camera-owner-rights) policy. "
        "This is an allowlist inventory, ",
        "not evidence that every camera on a host is authorised. No live stream was fetched. ",
        "Provider-policy evidence is a separate reference "
        "and does not clear every camera owner or delivery method. ",
        "Confirm embedding, proxying, recording, export and commercial terms separately. ",
        "`legacyFrames` identifies recognised input URLs normalised to a current embed host; ",
        "it does not authorise an additional iframe destination.\n\n",
        "| Host | Configured use | Owner rights | Provider-policy evidence |\n"
        "| --- | --- | --- | --- |\n",
    ]
    out += [
        f"| `{row['host']}` | {', '.join(row['uses'])} | unknown | "
        + (
            f"[{row['provider_policy']}](#policy-{row['provider_policy']})"
            if row["provider_policy"]
            else "Owner-specific review required"
        )
        + " |\n"
        for row in metadata["camera_hosts"]
    ]
    out += [
        "\n## Maintenance\n\n",
        "Review JSON changes by source ID; never copy a permissive policy "
        "solely because another product uses the same provider. ",
        "Keep grants and correspondence in controlled records, "
        "with a non-sensitive reference if needed. ",
        "Recheck terms before a commercial release "
        "and when a provider, product, endpoint or licence changes.\n\n",
        "Regenerate this file with `python scripts/render_source_licences.py`; "
        "verify it with `--check`. ",
        "Run `uv run pytest tests/test_source_licences.py --no-cov` in `backend`. ",
        "Adding a catalogue ID without an explicit row must fail. "
        "No network lookup occurs during these checks.\n",
    ]
    return "".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != rendered:
            raise SystemExit(
                "Source licence documentation is stale; run this script without --check."
            )
    else:
        TARGET.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
