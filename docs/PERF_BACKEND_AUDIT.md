# Backend responsiveness audit, 9 September 2026

The backend had synchronous CPU work after the already-cooperative feed normaliser. A large sensor batch could block the API event loop during store insertion and contextual grading. Broad geographic requests also filtered, globally sorted and converted thousands of DTOs on that loop. Concurrent map refreshes amplified this work.

## Measurement

`uv run --directory backend python ../scripts/benchmark_backend.py` constructs an isolated, deterministic 56,000-record store: 20,000 FIRMS observations across two sensors, 20,000 maritime observations and 16,000 satellite observations. Each record includes twelve synthetic reported attributes. The store estimates 223.2 MiB. This is representative load, not a copy of private or provider data. The benchmark neither connects to upstream providers nor touches the running application.

A one-millisecond asyncio heartbeat measures the maximum scheduling gap during each operation. A controlled same-run comparison on the development machine produced:

| Operation | Synchronous maximum loop gap | Repaired maximum loop gap | Repaired total time |
| --- | ---: | ---: | ---: |
| Grade 20,000 sensor observations | 605.6 ms | 38.0 ms | 617.6 ms |
| Geographic query and 2,000 DTOs | 127.7 ms | 31.4 ms | 166.2 ms |
| Insert 56,000 observations | Initial separate baseline 800.5 ms | 16.1 ms | 283.4 ms |

The insertion baseline was collected under different machine load and is not a controlled speedup comparison. An earlier contended measurement recorded 2.8 seconds of synchronous grading. CPU competition, garbage collection and Python's GIL affect absolute timings. These changes reduce uninterrupted API blocking; they do not eliminate computation or establish a production throughput guarantee. The final JSON serializer remains on FastAPI's response path.

## Repairs

- Large upserts yield every 250 observations, with the original final memory and geographic retention rules. Cancellation also enforces the budget.
- Instrument grading uses independent bounded batches. Narrative contextual grading still sees the full bounded narrative pool. Pure analysis runs outside the API loop; writes remain on it. Grading admission stays held until a cancelled worker finishes.
- Grade updates check that a record is still retained with the same content hash. A delayed grading result cannot restore a pruned record or overwrite newer source content.
- Geographic paging sorts within cells and categories, then their leading records. It preserves the previous newest-first, category-aware round-robin ordering and antimeridian handling.
- Event reads capture immutable references only after admission and perform filtering, ranking and DTO conversion outside the API loop. There is one active reader and at most eight admitted reads per store. Excess demand receives the existing rate-limit response. Cancelled requests keep their slot until their worker actually finishes, including repeated cancellation.
- Event-list responses recheck session validity and token expiry after asynchronous work.
- Repeated statistics reads reuse the result until a store mutation invalidates it.

The bus already bounds each subscriber queue and converts oversized sensor messages into resynchronisation notices. This audit preserves those backpressure rules and alert authorisation. It does not add a new event archive, raise observation caps or disable source provenance.

## Validation

Focused offline regressions cover parity with synchronous retention and grades, cancellation budgets, immutable read snapshots, single-worker admission, repeated cancellation, stale-grade rejection, geographic paging, source indexing, memory accounting and post-worker session revocation. Run the current targeted tests rather than interpreting these local measurements as a guarantee that every browser/GPU configuration is stable.
