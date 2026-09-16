"""When one reading pass stops being enough for the evidence pool.

A pool wider than this is layered: each theme is read in its own bounded pass and the
passes are then synthesised. The thresholds are shared so the flat drafting path can
say plainly that it did not layer, rather than implying even coverage it did not give.
"""

WIDE_POOL_ITEMS = 48
MAX_TOPIC_EVIDENCE = 12
