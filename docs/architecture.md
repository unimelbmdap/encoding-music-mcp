# Architecture

## System overview

Encoding Music MCP is a Python distribution with two coordinated runtime entry points:

1. The FastMCP server exposes MEI discovery, analysis, rendering, playback, and query-time contrastive emotion retrieval over stdio or HTTP.
2. The standalone score-embedding pipeline converts complete symbolic scores to validated `.xml` MusicXML, extracts CLaMP 3 embeddings, and stores them in SQLite.

Batch embedding generation is not registered as an MCP tool and is not included in the container deployment. The MCP emotion tool consumes an explicitly configured database and external CLaMP runtime at query time; it does not install or download them.

The CLaMP boundary follows ADR-0001. Vector persistence follows ADR-0003. Contrastive cross-modal retrieval follows ADR-0004.

## Runtime topology

```text
MCP clients
    |
    v
FastMCP server --> existing tools, resources, prompts, and notation apps
    |
    +--> contrastive emotion retrieval
             |
             +--> pinned external CLaMP text encoder
             |
             +--> positive-minus-negative normalization
             |
             +--> SQLite/sqlite-vec cosine search


CLI or Python caller
    |
    v
score orchestrator
    |
    +--> music21 standardization
    |        |
    |        v
    |    temporary .xml workspace
    |        |
    |        v
    |    round-trip validator
    |
    +--> CLaMP runner adapter
    |        |
    |        v
    |    pinned external CLaMP checkout, interpreter, and model cache
    |        |
    |        v
    |    raw .npy embeddings
    |
    +--> shape validation and L2 normalization
             |
             v
         SQLite repository
         + relational provenance and raw vectors
         + sqlite-vec normalized-vector index
             |
             v
         durable run manifest
```

## Runtime components

### Existing MCP server

`encoding_music_mcp.server` remains responsible for FastMCP transport, registration, and deployment. The score-embedding pipeline does not import the server or mutate its tool registry. The emotion-retrieval module registers a query-only tool that accepts ordered semantic poles and returns catalog-shaped results.

### Score processing

The score processor accepts complete MEI inputs or caller-provided music21 streams. It deep-copies caller-owned streams, removes or replaces standardization metadata through supported music21 container operations, applies deterministic instrument, tempo, and velocity defaults, and exports only `.xml` MusicXML.

No segmentation or MIDI conversion occurs.

### XML workspace and validation

Each run creates a controlled workspace with collision-resistant, deterministic score filenames. Exported XML is reparsed with music21 and compared with the standardized source using ordered note events containing onset, pitch, and duration.

Validation reports distinguish exact passes, tolerance-qualified warnings, and failures. A failed score is excluded from inference and recorded as failed; it cannot create or update an embedding record.

Intermediates are removed after the run unless retention is explicitly requested.

### CLaMP setup and runner adapter

The setup component owns acquisition and verification of the external checkout, symbolic C2 weights, and transitive model assets described by ADR-0001. It records an artifact manifest in the configured cache and performs an offline readiness check.

The runner receives only validated XML files. It invokes the pinned XML-to-ABC, interleaved-ABC, and global feature-extraction scripts as separate subprocesses with an explicitly configured interpreter, argument arrays, controlled working directories and environment, captured output, timeouts, and actionable errors.

The runner does not install packages or access the network. Model setup is never triggered by import or implicitly by extraction.

The same adapter exposes offline text encoding for emotion poles only when the pinned checkpoint provides a text path aligned with the stored symbolic-music vectors. Readiness checks verify that capability and the repository verifies compatible model identity and dimension before search.

### Embedding loader and normalizer

The loader maps generated `.npy` files back to score identities through deterministic filenames. Music-batch orchestration may admit a requested subset when upstream preprocessing silently omits individual scores, preserving requested order and recording each omission in the run manifest. Strict loading remains the default for text encoding. Duplicate, unexpected, non-numeric, non-finite, or incorrectly shaped outputs remain fatal, as does a validated music batch that produces no embeddings.

Global embeddings have 768 values. Raw values are retained as float32, while normalization divides by the L2 norm and safely preserves zero vectors without NaN or infinity values.

### SQLite embedding repository

The repository owns schema migration, persistence, retrieval, and similarity search under ADR-0003.

A relational table stores score identity, nullable title, artist or composer, nullable work-creation date, source hash and location, processing fingerprint, validation evidence, CLaMP code and model provenance, vector dimensions, raw embedding data, and timestamps. A `sqlite-vec` virtual table uses the same row identifier to store normalized `float[768]` vectors with cosine distance. Catalog APIs project the simpler title, artist, work-date, and vector/result shape without deleting internal provenance.

Migrations and paired relational/vector writes execute transactionally. Reprocessing the same logical identity atomically updates its record; changes to the source, processing configuration, CLaMP revision, or model weights create a distinct identity.

The repository rejects incompatible schema versions, vector dimensions, and non-finite values before writing.

The repository also accepts an arbitrary validated normalized query vector. It performs cosine KNN inside SQLite and returns stable distance-and-ID ordering with catalog metadata; it never loads the complete vector collection into Python.

### Contrastive emotion retrieval

The emotion-retrieval component accepts a positive target pole and negative contrast pole chosen by Claude. It delegates text encoding to the score-embeddings CLaMP adapter, verifies both outputs against stored model identity, computes and L2-normalizes `positive - negative`, rejects zero and non-finite directions, and queries the repository. It returns both poles, ranking metadata, score identity, title, artist or composer, and work-creation date. Claude does not create or subtract numeric embeddings.

### Pipeline CLI

A second console entry point uses `argparse` to expose setup, extraction, and similarity-query operations without changing the existing `encoding-music-mcp` command.

The extraction command accepts files or directories, output and database paths, cache and external-interpreter configuration, timing tolerance, logging level, timeout, and intermediate-retention options. It writes a deterministic run manifest connecting each source score to validation results, extraction disposition, database identity, and diagnostics.

The CLI returns a non-zero status when setup, validation, extraction, or persistence fails. Python callers receive typed results and domain-specific exceptions rather than process exits.

## Data flow

1. Resolve input MEI files in deterministic path order and assign stable score identities.
2. Parse each complete score and create a standardized deep copy.
3. Export the copy to a deterministic `.xml` path in the run workspace.
4. Reparse the XML and compare ordered note events with the standardized source.
5. Exclude failed conversions and batch the validated XML files.
6. Invoke the pinned CLaMP preprocessing and global extraction pipeline offline.
7. Match each `.npy` output to exactly one validated score and record any omitted expected score as a per-score failure.
8. Require at least one matched output and validate each `(768,)` global-vector shape and numeric value.
9. Produce raw float32 and L2-normalized representations for the matched subset.
10. Transactionally upsert relational provenance, the raw vector, and the normalized vector index for each matched score.
11. Write the run manifest, retaining validation and extraction omissions, and clean temporary artifacts unless retention was requested.

Contrastive retrieval follows a separate query path:

1. Claude converts an emotion request into ordered positive and negative text poles.
2. The MCP tool validates the pole strings and sends both to the pinned offline CLaMP text encoder.
3. The application verifies compatible dimensions and model identity, computes `positive - negative`, L2-normalizes it, and rejects invalid or zero directions.
4. The repository performs cosine KNN through `sqlite-vec` with stable tie ordering.
5. The tool returns catalog-shaped matches plus the exact poles and model/query provenance.

A score never reaches CLaMP or SQLite without passing XML validation. A database transaction never commits one side of the relational/vector pair without the other.

## Technology stack

- Python 3.12 or newer for the MCP server and score-embedding package
- FastMCP for the existing server
- music21 for symbolic-score parsing, standardization, XML export, and reparse
- NumPy for embedding loading, shape checks, and normalization
- Python `sqlite3` plus pinned `sqlite-vec` for persistence and similarity search
- `argparse` and standard-library logging for the standalone CLI
- A separately provisioned Python 3.10/PyTorch environment for pinned CLaMP 3
- uv for project dependency locking
- pytest for unit and integration tests
- Ruff for formatting and linting

## Constraints and lifecycle

- Imports are deterministic and perform no installation, cloning, download, database migration, or subprocess execution.
- `.xml` MusicXML is the only intermediate score format.
- Input songs are processed whole; segmentation is outside this architecture.
- External paths are normalized and subprocess arguments are never constructed through the shell.
- CLaMP runs use controlled workspaces because the pinned upstream scripts depend on relative paths and temporary directories.
- Network access is permitted only during the explicit setup operation.
- Successful setup must support subsequent offline extraction.
- Temporary XML and `.npy` workspaces have explicit ownership and cleanup.
- Durable databases and manifests are never deleted by workspace cleanup.
- SQLite extension loading is limited to the packaged `sqlite-vec` binary and disabled immediately afterward.
- Default automated tests do not require the CLaMP repository, weights, network access, or accelerator hardware.
- Query-time MCP retrieval requires explicit database, external-interpreter, and cache configuration and fails actionably when compatible text assets or stored model identity are unavailable.
- The SQLite database is local and embedded; distributed coordination and multi-user service semantics are not provided.

## Extension points

- Input resolution can be extended with additional whole-score sources without introducing segmentation.
- The standardization policy can gain explicit configuration while retaining non-mutation and deterministic fingerprints.
- The model-runner protocol can support a future CLaMP revision or another whole-score embedding model behind a new decision record.
- Storage consumers can build additional retrieval workflows over arbitrary normalized query vectors without duplicating SQLite behavior.
- Batch-generation MCP exposure, containerized inference, and hosted vector search require separate design revisions.

## Software architecture

### score-embeddings

**Purpose:** Convert complete symbolic scores into validated XML representations and reproducible CLaMP 3 embeddings, retain catalog metadata, encode compatible CLaMP text queries, and store vectors for retrieval.

**Data concern:** Owns score-processing identity, catalog metadata, standardized and validated XML artifacts, conversion evidence, compatible text/music model provenance, raw and normalized embedding vectors, arbitrary-vector search, database persistence, and run manifests.

**Dependencies:** Depends on music21 and NumPy, the ADR-0001 external CLaMP runtime, and the ADR-0003 SQLite vector boundary. It does not depend on the FastMCP server or tool registry.

**Consumed by:** The standalone batch CLI, typed Python callers, and emotion-retrieval.

### emotion-retrieval

**Purpose:** Expose Claude-facing contrastive emotion search and return catalog-shaped song matches.

**Data concern:** Owns ordered semantic poles, query provenance, contrast-vector construction, MCP error translation, and retrieval-result presentation. It does not own stored score vectors.

**Dependencies:** Depends on score-embeddings for the ADR-0001 CLaMP runtime adapter and ADR-0003 SQLite repository, and on the FastMCP registry for tool exposure.

**Consumed by:** MCP clients, including Claude.
