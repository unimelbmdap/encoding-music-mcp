# Scope

## Current scope

- Provide an MCP server for discovering, inspecting, analyzing, and displaying MEI-encoded musical scores.
- Provide typed Python processing for complete MEI scores and music21 streams.
- Standardize complete scores without mutating caller-owned streams.
- Export standardized scores exclusively as `.xml` MusicXML documents.
- Reparse exported XML and compare musical events with the source representation.
- Set up and reuse a pinned, integrity-checked CLaMP 3 runtime through an explicit operation.
- Extract and L2-normalize one global CLaMP 3 embedding per complete score.
- Preserve deterministic score-to-file and score-to-embedding ordering in a durable output manifest.
- Persist every successfully extracted raw and normalized embedding in SQLite.
- Store score identity, source provenance, validation results, embedding dimensions, and CLaMP model/version metadata with each embedding.
- Persist MEI-derived song title, artist or composer, and nullable work-creation date without making descriptive metadata part of embedding identity.
- Use a SQLite vector extension to support similarity queries over normalized embeddings.
- Encode ordered positive and negative emotion poles with the CLaMP configuration aligned to stored score vectors.
- Construct and L2-normalize a deterministic positive-minus-negative contrast vector and retrieve catalog-shaped song matches through SQLite cosine search.
- Expose contrastive emotion retrieval, but not batch embedding generation, as a Claude-facing MCP tool.
- Apply schema migrations and database writes transactionally.
- Provide a standalone batch CLI with configurable inputs, outputs, cache paths, database paths, logging, validation policy, and intermediate-file retention.

## Current non-goals

- Segmenting scores, detecting phrases, or generating multiple embeddings from regions of one score.
- MIDI export or MIDI conversion validation.
- Supporting `.mxl`, `.musicxml`, or other intermediate output suffixes in this workflow.
- Training, fine-tuning, or modifying CLaMP 3.
- Hosted embedding inference.
- Exposing batch embedding generation through the MCP tool registry.
- Bundling CLaMP inference or model weights into the Docker deployment.
- Installing dependencies or downloading artifacts during module import.
- Committing third-party CLaMP source code or model weights to this repository.
- Operating a remote, distributed, or multi-user vector database service.
- Providing a general-purpose database administration interface.

## Success criteria

- Standardization produces deterministic results without mutating the caller-owned music21 stream.
  *Delivered by: score-embeddings*
- Every accepted input score is exported to an `.xml` MusicXML document and reparsed before inference.
  *Delivered by: score-embeddings*
- Conversion reports detect event-count, pitch, onset, and duration mismatches with a configurable timing tolerance.
  *Delivered by: score-embeddings*
- CLaMP 3 setup uses a pinned upstream revision and integrity-checked model artifacts and can be reused offline after successful setup.
  *Delivered by: score-embeddings*
- Batch output contains one validated, correctly ordered embedding result per successfully processed complete score.
  *Delivered by: score-embeddings*
- Raw embeddings are shape-checked and L2-normalized without producing invalid values for zero vectors.
  *Delivered by: score-embeddings*
- Python APIs are typed and raise actionable domain-specific errors; the CLI returns meaningful exit codes and logs.
  *Delivered by: score-embeddings*
- Automated coverage exercises score standardization, XML round trips, validation outcomes, output ordering, normalization, cleanup, and external-process failures without downloading CLaMP or its weights.
  *Delivered by: score-embeddings*
- Every successful score embedding is transactionally stored with sufficient source, validation, and model provenance to reproduce or diagnose it.
  *Delivered by: score-embeddings*
- Stored vector dimensions are validated against the configured CLaMP model, and incompatible embeddings are rejected with actionable errors.
  *Delivered by: score-embeddings*
- Normalized embeddings can be retrieved through a tested vector-similarity query without loading the complete embedding collection into Python.
  *Delivered by: score-embeddings*
- Reprocessing a score follows an explicit, deterministic duplicate or upsert policy defined by ADR-0003.
  *Delivered by: score-embeddings*
- Stored embeddings retain faithful MEI-derived title, artist or composer, and nullable work-creation date while ingestion timestamps remain distinct.
  *Delivered by: score-embeddings*
- Both emotion poles are encoded with the same compatible CLaMP model configuration as the stored score vectors.
  *Delivered by: score-embeddings, emotion-retrieval*
- Emotion queries compute and L2-normalize the ordered positive-minus-negative direction and reject incompatible, non-finite, or zero directions actionably.
  *Delivered by: score-embeddings, emotion-retrieval*
- Contrastive similarity executes inside SQLite with stable ordering and without loading the complete embedding collection into Python.
  *Delivered by: score-embeddings, emotion-retrieval*
- MCP emotion results include the ordered poles and deterministic title, artist or composer, work-date, score identity, and distance metadata.
  *Delivered by: emotion-retrieval*
