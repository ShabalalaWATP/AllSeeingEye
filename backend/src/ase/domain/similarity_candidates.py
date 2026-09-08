"""Bounded candidate joins for approximate topic/copy navigation.

Frequent tokens cannot allocate quadratic pair tables. Exact token sets retain
linear adjacent links; near matches use rare postings with a fixed work budget.
Saturated topics may remain separate, never implying verified agreement.
"""

from collections.abc import Iterator, Sequence

MAX_TOKEN_POSTINGS = 128
MAX_CANDIDATES = 128


def token_candidate_pairs(tokens: Sequence[frozenset[str]]) -> Iterator[tuple[int, int]]:
    postings: dict[str, list[int]] = {}
    for index, words in enumerate(tokens):
        for word in words:
            bucket = postings.setdefault(word, [])
            if len(bucket) <= MAX_TOKEN_POSTINGS:
                bucket.append(index)
    exact: dict[frozenset[str], int] = {}
    for right, words in enumerate(tokens):
        if words:
            previous = exact.get(words)
            if previous is not None:
                yield previous, right
            exact[words] = right
        yield from ((left, right) for left in _rare_candidates(right, words, tokens, postings))


def _rare_candidates(
    right: int,
    words: frozenset[str],
    tokens: Sequence[frozenset[str]],
    postings: dict[str, list[int]],
) -> list[int]:
    candidates: set[int] = set()
    for word in sorted(words, key=lambda word: (len(postings[word]), word)):
        bucket = postings[word]
        if len(bucket) > MAX_TOKEN_POSTINGS:
            continue
        for left in bucket:
            if left >= right:
                break
            if tokens[left] != words:
                candidates.add(left)
            if len(candidates) >= MAX_CANDIDATES:
                break
        if len(candidates) >= MAX_CANDIDATES:
            break
    return sorted(candidates)
