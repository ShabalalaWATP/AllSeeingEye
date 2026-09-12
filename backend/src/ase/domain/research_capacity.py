"""Catalogue metadata is bounded separately from operator choices and outbound work."""

MAX_COLLECTION_PROVIDERS = 128
MAX_SELECTED_SOURCES = 64
MAX_PLANNED_TASKS = 8
MAX_RESEARCH_CANDIDATES = 8
MAX_PLAN_TASKS = MAX_COLLECTION_PROVIDERS + MAX_PLANNED_TASKS
# Unsupported and budget-exhausted rows are coverage metadata, not extra requests.
# Retained input receipts share this total with selected collection tasks.
MAX_COLLECTION_RECEIPTS = MAX_PLAN_TASKS
MAX_SEED_RECEIPTS = 64
MAX_COLLECTION_REQUESTS = 32
MAX_COLLECTION_ITEMS = 1000
