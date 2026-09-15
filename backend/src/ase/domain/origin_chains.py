"""Conservative origin groups; uncertainty never creates independent corroboration.

Groups are counting constraints, not proof that sources are dependent or true.
Model proposals can reduce apparent independence but remain labelled proposals.
No title, nationality or publisher reputation is used to guess an original author.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from ase.domain.origin_records import (
    AssessedOriginEdge,
    OriginEdge,
    OriginGroup,
    OriginNode,
    OriginObservation,
    OriginRelation,
    OriginRole,
    OriginStatus,
)
from ase.domain.source_provenance import DisjointGroups

ORIGIN_POLICY_VERSION = "ase-origin-chains-v1"
MAX_ORIGIN_NODES = 512
MAX_ORIGIN_EDGES = 1024


@dataclass(frozen=True, slots=True)
class OriginAnalysis:
    nodes: tuple[OriginNode, ...]
    groups: tuple[OriginGroup, ...]
    relationships: tuple[AssessedOriginEdge, ...]
    observations: tuple[OriginObservation, ...]
    policy_version: str = ORIGIN_POLICY_VERSION


def _edge_status(
    edge: OriginEdge,
    observations: dict[str, OriginObservation],
    child: OriginNode,
    parent: OriginNode,
) -> OriginStatus:
    if any(key not in observations for key in edge.observation_ids):
        raise ValueError("Origin relationships cannot invent retained observation IDs.")
    if edge.rejected:
        return OriginStatus.REJECTED
    if edge.reviewer_id is not None:
        return OriginStatus.REVIEWED
    supported = any(
        observations[key].evidence_id == child.evidence_id
        and observations[key].claim_id == child.claim_id
        and observations[key].target_evidence_id == parent.evidence_id
        and observations[key].relation is edge.relation
        for key in edge.observation_ids
    )
    return OriginStatus.OBSERVED if supported else OriginStatus.PROPOSAL


def _record_indices(
    nodes: Sequence[OriginNode],
    edges: Sequence[OriginEdge],
    observations: Sequence[OriginObservation],
) -> tuple[dict[str, OriginNode], dict[str, OriginObservation]]:
    if (
        len(nodes) > MAX_ORIGIN_NODES
        or len(edges) > MAX_ORIGIN_EDGES
        or len(observations) > MAX_ORIGIN_EDGES
        or any(not isinstance(node, OriginNode) for node in nodes)
        or any(not isinstance(edge, OriginEdge) for edge in edges)
        or any(not isinstance(row, OriginObservation) for row in observations)
    ):
        raise ValueError("Origin analysis requires bounded typed records.")
    node_index = {node.id: node for node in nodes}
    observation_index = {row.id: row for row in observations}
    if (
        len(node_index) != len(nodes)
        or len({edge.id for edge in edges}) != len(edges)
        or len(observation_index) != len(observations)
        or len({(node.evidence_id, node.claim_id) for node in nodes}) != len(nodes)
    ):
        raise ValueError("Origin records and evidence-claim pairs must be unique.")
    evidence_ids = {node.evidence_id for node in nodes}
    if any(
        row.evidence_id not in evidence_ids
        or (row.target_evidence_id is not None and row.target_evidence_id not in evidence_ids)
        for row in observations
    ):
        raise ValueError("An observed relationship must belong to the frozen evidence.")
    return node_index, observation_index


def _reviewed_decisions(edges: Sequence[OriginEdge]) -> dict[tuple[str, str, OriginRelation], str]:
    decisions: dict[tuple[str, str, OriginRelation], OriginEdge] = {}
    reviewed_times: set[tuple[str, str, OriginRelation, datetime]] = set()
    for edge in edges:
        if edge.reviewed_at is None:
            continue
        key = edge.child_id, edge.parent_id, edge.relation
        previous = decisions.get(key)
        stamp = (*key, edge.reviewed_at)
        if stamp in reviewed_times:
            raise ValueError("Tied origin-review decisions require an explicit later review.")
        reviewed_times.add(stamp)
        if previous is None or (
            previous.reviewed_at is not None and previous.reviewed_at < edge.reviewed_at
        ):
            decisions[key] = edge
    return {key: edge.id for key, edge in decisions.items()}


def _unresolved_cycles(ids: Sequence[str], relationships: Sequence[AssessedOriginEdge]) -> set[str]:
    outgoing: dict[str, set[str]] = {key: set() for key in ids}
    incoming = dict.fromkeys(ids, 0)
    for row in relationships:
        edge = row.edge
        if (
            row.status is not OriginStatus.REJECTED
            and row.effective
            and edge.parent_id not in outgoing[edge.child_id]
        ):
            outgoing[edge.child_id].add(edge.parent_id)
            incoming[edge.parent_id] += 1
    ready = [key for key in ids if incoming[key] == 0]
    while ready:
        for parent in outgoing[ready.pop()]:
            incoming[parent] -= 1
            if incoming[parent] == 0:
                ready.append(parent)
    return {key for key, count in incoming.items() if count}


def analyse_origin_chains(
    nodes: Sequence[OriginNode],
    edges: Sequence[OriginEdge] = (),
    *,
    observations: Sequence[OriginObservation] = (),
) -> OriginAnalysis:
    """Validate declared relations against frozen observation membership, then group.

    Original identity and shared organisation group only within the same claim.
    Unknown origins are conservatively pooled within that claim; they cannot
    acquire known provenance from a well-known outlet copying their assertion.
    """
    node_index, observation_index = _record_indices(nodes, edges, observations)
    decisions = _reviewed_decisions(edges)
    groups = DisjointGroups(node_index)
    seen: dict[tuple[str, str, str], str] = {}
    for node in sorted(nodes, key=lambda node: node.id):
        keys = []
        if node.organisation is not None:
            keys.append((node.claim_id, "organisation", node.organisation))
        keys.append((node.claim_id, "origin", node.original_identity or ""))
        for key in keys:
            if key in seen:
                groups.union(node.id, seen[key])
            seen[key] = node.id
    assessed = []
    for edge in sorted(edges, key=lambda edge: edge.id):
        if edge.child_id not in node_index or edge.parent_id not in node_index:
            raise ValueError("Origin relationships require both retained endpoints.")
        child, parent = node_index[edge.child_id], node_index[edge.parent_id]
        if child.claim_id != parent.claim_id:
            raise ValueError("An origin relationship must address the same declared claim.")
        status = _edge_status(edge, observation_index, child, parent)
        if any(
            observation_index[key].evidence_id not in (child.evidence_id, parent.evidence_id)
            or (
                observation_index[key].target_evidence_id is not None
                and observation_index[key].target_evidence_id
                not in (child.evidence_id, parent.evidence_id)
            )
            or (
                observation_index[key].claim_id is not None
                and observation_index[key].claim_id != child.claim_id
            )
            for key in edge.observation_ids
        ):
            raise ValueError("An origin observation must belong to this claim and its endpoints.")
        effective = (
            decisions.get((edge.child_id, edge.parent_id, edge.relation), edge.id) == edge.id
        )
        assessed.append(AssessedOriginEdge(edge, status, effective))
        if effective and status is not OriginStatus.REJECTED:
            groups.union(child.id, parent.id)
    members: dict[str, list[OriginNode]] = {}
    for node in sorted(nodes, key=lambda node: node.id):
        members.setdefault(groups.find(node.id), []).append(node)
    frozen_groups = []
    cyclic = _unresolved_cycles(tuple(node_index), assessed)
    for values in members.values():
        frozen_groups.append(_freeze_group(values, assessed, cyclic))
    return OriginAnalysis(
        tuple(sorted(nodes, key=lambda node: node.id)),
        tuple(sorted(frozen_groups, key=lambda group: group.id)),
        tuple(assessed),
        tuple(sorted(observations, key=lambda observation: observation.id)),
    )


def _freeze_group(
    values: Sequence[OriginNode], assessed: Sequence[AssessedOriginEdge], cyclic: set[str]
) -> OriginGroup:
    ids = tuple(node.id for node in values)
    related = [row for row in assessed if row.effective and row.edge.child_id in ids]
    uncertain = any(
        row.status is OriginStatus.PROPOSAL
        or (
            row.status is not OriginStatus.REJECTED
            and row.edge.relation is OriginRelation.POSSIBLE_SHARED_ANONYMOUS_ORIGIN
        )
        for row in related
    )
    unknown = any(node.original_identity is None for node in values)
    cycle = bool(set(ids) & cyclic)
    reasons = ["A group limits corroboration counts; it does not establish source independence."]
    if uncertain:
        reasons.append("Unresolved origin proposals reduce apparent independence pending review.")
    if unknown:
        reasons.append(
            "Some original identities are unknown; publisher identity does not resolve them."
        )
    if cycle:
        reasons.append("Proposed or declared origin links contain a cycle requiring review.")
    return OriginGroup(
        f"OG:{min(ids)}",
        values[0].claim_id,
        ids,
        tuple(
            node.id
            for node in values
            if node.original_identity
            and node.organisation
            and node.role
            in (
                OriginRole.ORIGINAL_DOCUMENT,
                OriginRole.ORIGINAL_STATEMENT,
                OriginRole.DIRECT_WITNESS,
            )
        ),
        uncertain or unknown or cycle,
        tuple(reasons),
    )
