# CLaMP 3 Score Embeddings

The optional score-embedding workflow processes complete symbolic scores. It standardizes each score without mutating caller-owned music21 streams, exports and reparses `.xml` MusicXML, extracts one 768-dimensional CLaMP 3 C2 embedding, and stores raw and normalized vectors with catalog metadata in SQLite.

Batch generation remains separate from the MCP server and does not segment scores, produce MIDI, or run inside the project's Docker deployment. A query-only MCP tool can search a prepared local database using matched prompt ensembles for an ordered semantic contrast.

## Clone → setup → run

For a source checkout on **Windows x64, Linux x86_64, or macOS on Apple Silicon**, install uv and Git,
then run these commands from the repository root:

```bash
uv run --extra score-embeddings --locked encoding-music-embeddings bootstrap
uv run --extra score-embeddings --locked encoding-music-mcp
```

Bootstrap creates `.venv-clamp` with Python **3.10.16**, synchronizes its separate
committed dependency lock, and calls the existing pinned model setup into
`.clamp3-cache`. The MCP server retains its own Python 3.12+ environment. The
bundled embedding database is ready for retrieval; bootstrap does not regenerate it.

Choose exactly one profile:

| Profile | Command suffix | Runtime |
| --- | --- | --- |
| CPU (default) | `--profile cpu` | PyTorch 2.7.1; Windows/Linux CPU wheels or native macOS arm64 wheels; no GPU required |
| NVIDIA GPU | `--profile cu128` | Windows/Linux only; PyTorch 2.7.1 CUDA 12.8 wheels; compatible NVIDIA GPU and driver required |

On Apple Silicon, use a native arm64 terminal and uv/Python installation, not
Rosetta. The same bootstrap command selects the macOS PyTorch wheels from PyPI
and runs CLaMP on the CPU; Apple GPU (MPS) acceleration is not enabled.
Intel Macs are not supported by the pinned PyTorch 2.7.1 runtime.
Bootstrap rejects CUDA on Mac before installing packages or downloading models.

Both profiles pin torchvision 0.22.1, torchaudio 2.7.1, upstream CLaMP dependencies,
and their transitive dependencies in
[`clamp_runtime/uv.lock`](../../src/encoding_music_mcp/tools/score_embeddings/clamp_runtime/uv.lock).
The [PyTorch wheel profiles](https://pytorch.org/get-started/previous-versions/#v271)
and [CLaMP requirements](https://github.com/sanderwood/clamp3/blob/9016d2b0c8d12d1aa79c2e0ab201e6822bdc83a8/requirements.txt)
are the sources for these selections. CUDA setup executes a small tensor operation
before model downloads so an incompatible driver or unavailable device fails early.

Initial setup needs network access, several GB of free disk space for Python,
dependencies, model weights and download caches, and sufficient RAM to load the model.
The C2 checkpoint alone is about 2.52 GB. CPU inference can be slow. Use
`--timeout SECONDS` to increase the default 3600-second limit per setup operation.

Rerun the same bootstrap command after a failed setup or a dependency-lock update;
it reuses the environment and valid downloads. To change profiles, rerun with the
new profile; uv synchronizes the environment to that profile's locked packages.
Restart Claude after bootstrap, especially when changing profiles. Virtual
environments are local machine artifacts: bootstrap each clone on its target OS
rather than copying `.venv-clamp` between machines.

Both retrieval tools use explicit environment overrides first, then the local
runtime/cache beside the source checkout. No per-machine CLaMP paths are needed
in Claude's config. A missing local runtime or incomplete local cache produces the
bootstrap command in its error. See [Configuration](configuration.md) for the full
Claude launcher, including `--extra score-embeddings --locked`.

Bootstrap is limited to the platforms above. Other platforms and
installed wheels can still use a separately provisioned CLaMP environment as below.

The Apple Silicon bootstrap path is covered by automated platform tests and
dependency-resolution checks. Full model setup and retrieval still need validation
on a physical Mac; they have not been run on macOS in this development environment.

## External-runtime prerequisites

- Python 3.12 or newer and uv for the MCP project
- The optional `score-embeddings` dependency set (`uv sync --extra score-embeddings --locked`)
- Git and network access during explicit setup
- A separately provisioned Python 3.10 CLaMP environment with compatible PyTorch

Provision that environment using the [upstream CLaMP 3 instructions](https://github.com/sanderwood/clamp3),
then pass its interpreter to `setup`. This lower-level command verifies the environment
and prepares assets but does not install PyTorch; `bootstrap` performs both stages.

## Pinned model setup

The setup command is the only pipeline operation permitted to use the network:

```bash
uv run encoding-music-embeddings setup \
  --clamp-python /absolute/path/to/clamp-python
```

The setup contract is defined by ADR-0001. It:

1. acquires the pinned CLaMP 3 source revision into a configurable user cache;
2. selects the symbolic C2 configuration;
3. downloads the pinned C2 checkpoint and verifies its SHA-256 digest;
4. inventories and prefetches required tokenizer and model assets;
5. records an artifact manifest; and
6. runs an offline readiness check with the configured interpreter.

Use `--cache-dir PATH` to override the platform-specific user cache. Setup is idempotent: valid cached artifacts are reused, while partial or checksum-invalid downloads are rejected and replaced through an atomic temporary file.

Imports and extraction never run setup implicitly.

## Extract complete scores

The extraction interface accepts one or more MEI files or directories:

```bash
uv run encoding-music-embeddings extract scores/ \
  --database score-embeddings.sqlite3 \
  --output-dir output/score_embeddings \
  --clamp-python /absolute/path/to/clamp-python
```

Important options include:

- `--cache-dir PATH`: verified CLaMP source and model cache
- `--database PATH`: SQLite database destination
- `--output-dir PATH`: durable run-manifest directory
- `--tolerance FLOAT`: absolute onset and duration comparison tolerance
- `--timeout SECONDS`: external-process timeout
- `--keep-intermediates`: retain generated XML and NumPy files for diagnosis
- `--log-level LEVEL`: standard Python logging level

Inputs are ordered deterministically. Each input is treated as one complete score and exported only as `.xml`; there is no segmentation or MIDI conversion.

Some corpora contain include-only MEI aggregate manifests that reference separate score-bearing movement files but contain no `<score>` themselves. During directory discovery, the pipeline skips these parent manifests, logs them, and records them under `skipped_inputs` in the run manifest. Their referenced movement files are discovered and processed normally. Supplying an aggregate parent explicitly fails early with an actionable list of its references instead of exposing a `music21` parser traceback. The pipeline does not concatenate or resolve aggregate movements.

## Validation policy

The pipeline compares ordered note events from the standardized source and reparsed XML. Each event contains onset, MIDI pitch number as a comparison value, and duration; no MIDI file is created.

- `PASS`: event count, pitches, onsets, and durations agree.
- `PASS WITH WARNINGS`: at least 99% of pitch and timing comparisons agree within the configured tolerance.
- `FAIL`: the event count differs or agreement falls below the warning threshold.

Failed scores do not reach CLaMP and do not create or update embedding records. Warning dispositions remain visible in the database and run manifest.

If upstream CLaMP preprocessing silently omits individual validated scores, the pipeline stores every valid output it did produce and records a per-score extraction error for each omission. The manifest has no run-level error when at least one safe output is usable, although the extraction CLI returns status 1 to report the incomplete batch. Unexpected outputs, malformed vectors, or a validated batch producing no embeddings remain fatal and are not partially persisted.

## Database and similarity search

ADR-0003 defines SQLite persistence and embedding identity. Each successful result stores nullable MEI-derived song title, artist or composer, and work-creation date alongside source and processing hashes, validation evidence, CLaMP provenance, the raw float32 embedding, and a normalized `sqlite-vec` vector. Publication and ingestion timestamps are not substituted for an unknown work-creation date.

The query interface is:

```bash
uv run encoding-music-embeddings similar \
  --database score-embeddings.sqlite3 \
  --score-id SCORE_ID \
  --limit 10
```

Reprocessing the same source, processing configuration, CLaMP revision, and model weights atomically updates the same logical record. Changing any identity component creates a distinct record.

For direct database access through a connection that has loaded `sqlite-vec`, the `song_catalog` view exposes the compact shape requested by catalog consumers:

```sql
SELECT song_title, artist, date_created, vector_embedding
FROM song_catalog;
```

The view joins the production provenance table to the `sqlite-vec` index; it is not a second source of truth. The project repository API loads the extension automatically. A standalone `sqlite3` shell must load the packaged extension before querying the view. Use the Python or MCP APIs for vector search because they also validate vectors and filter results to the exact model identity.

## Semantic retrieval through Claude

Bootstrapped source checkouts need no environment variables. To override their defaults
or use an external runtime, configure the server process after preparing the database and assets:

```bash
export ENCODING_MUSIC_EMBEDDINGS_DATABASE=/absolute/path/score-embeddings.sqlite3
export ENCODING_MUSIC_CLAMP_PYTHON=/absolute/path/to/clamp-python
export ENCODING_MUSIC_CLAMP_CACHE_DIR=/absolute/path/to/clamp-cache  # optional
export ENCODING_MUSIC_CLAMP_TIMEOUT_SECONDS=3600                     # optional
```

Claude can then call `search_songs_by_semantic_axis`. For “find the happiest songs,” it supplies 3–5 caption-like descriptions of joyful music and an equally sized, positionally matched ensemble describing sorrowful music. Each pair should share musical context and differ mainly in happiness. The application embeds the ordered batch with the same pinned CLaMP checkpoint as the scores, L2-normalizes every prompt before averaging, normalizes both centroids, and L2-normalizes `positive_centroid - negative_centroid` before cosine search inside SQLite. Claude never constructs or receives the numeric vectors.

Only rows with the exact matching CLaMP commit, model revision, weight hash, and dimension are eligible. Results contain the complete ordered ensembles, aggregation and model provenance, distance, score identity, title, artist, and work-creation date. See [Semantic Axis Retrieval](../tools/semantic-axis-retrieval.md) for the full prompt contract.

For one independent category without a necessary opposite, Claude calls
`search_songs_by_prototype` with a concept label and 3–5 equivalent descriptions.
The tool independently normalizes the prompt embeddings and reports each song's
arithmetic mean cosine similarity to them. Use semantic-axis retrieval for a
genuine continuum and symbolic tools for exact musical facts. See
[Dynamic Prototype Retrieval](../tools/prototype-retrieval.md) for scoring,
result interpretation, and the cold/warm timing command.

## Output layout

```text
output/score_embeddings/<run-id>/
|-- manifest.json
`-- intermediates/              # only with --keep-intermediates
    |-- xml/
    `-- embeddings/

score-embeddings.sqlite3        # durable relational and vector data
```

The manifest maps every score source to its validation disposition, extraction result, database identity, and diagnostics. Its separate `skipped_inputs` collection records include-only aggregate parents and their referenced files. Workspace cleanup never deletes the database or manifest.

## Offline behavior

After setup succeeds, extraction runs with network-disabled model settings. Missing or invalid cache artifacts produce an actionable setup error rather than an implicit download.

For portable automation, configure cache, database, output, and interpreter paths explicitly instead of depending on host defaults.

## Run extraction on a Colab GPU

Use [`notebooks/score_embeddings_colab.ipynb`](../../notebooks/score_embeddings_colab.ipynb) when a local CUDA runtime is unavailable. It works in browser Colab and through the official Google Colab VS Code extension. Select a GPU kernel before running any cells; the notebook checks CUDA and minimum VRAM both in the notebook kernel and in the separate Python 3.10 interpreter that actually runs CLaMP.

Build the current local project into a wheel before connecting the notebook:

```bash
uv build --wheel
```

Then connect the notebook to a Colab GPU and use the VS Code Colab extension to upload exactly one `dist/encoding_music_mcp-*.whl` file into `/content`. The notebook fails with an actionable message if the wheel is missing or if multiple matching wheels are present. It inspects the wheel for the score-embedding pipeline and bundled MEI resources before creating an isolated Python 3.12 project environment and installing the wheel with its `score-embeddings` optional dependencies. No Git checkout is needed in Colab.

Edit the configuration cell before running it. Additional MEI inputs, CLaMP timeout, minimum VRAM, CUDA PyTorch wheel index and packages, output paths, and artifact name are explicit settings. The default input is the complete installed `encoding_music_mcp.resources/mei_files` directory. Optional additional inputs append to that corpus and must be absolute file or directory paths in the Colab runtime.

The workflow preserves the ADR-0001 lifecycle:

1. install the uploaded local wheel into a Python 3.12 project environment and provision the separate Python 3.10 CLaMP environment;
2. run the explicit, network-enabled `encoding-music-embeddings setup` command;
3. run the existing `extract` command with offline model environment settings;
4. open the resulting database with `EmbeddingRepository`; and
5. package the SQLite database, pipeline `manifest.json`, and `SHA256SUMS` into a `.tar.gz` archive.

Colab runtimes are ephemeral. After the final cell succeeds, download the displayed archive from the VS Code extension's remote **Contents** view before disconnecting. Browser users may set `BROWSER_DOWNLOAD = True` to request a browser download. The notebook prints a prominent download warning either way.

Google Drive use is optional and disabled by default. When enabled, it is used only for the reusable CLaMP source/model cache; the database, manifest, and final archive remain under `/content` until you download them locally. No credentials or user-specific Drive paths are stored in the notebook.

After downloading, verify and extract the archive locally:

```bash
tar -xzf encoding-music-embeddings-<run-id>.tar.gz
sha256sum -c SHA256SUMS
```

To verify that the local database is compatible with the project repository API:

```bash
uv run --extra score-embeddings python -c \
  'from encoding_music_mcp.tools.score_embeddings.storage import EmbeddingRepository; import sys; r = EmbeddingRepository(sys.argv[1]); r.open(); print(r.connection.execute("SELECT COUNT(*) FROM score_embeddings").fetchone()[0]); r.close()' \
  score-embeddings.sqlite3
```

The archive is the durable handoff. Do not disconnect the Colab runtime while it contains the only copy.

## Troubleshooting

- **Setup checksum failure:** remove only the reported partial artifact and rerun setup; do not bypass verification.
- **CLaMP environment failure:** run the readiness check and verify that the selected interpreter has the upstream Python and PyTorch dependencies.
- **XML validation failure:** rerun with `--keep-intermediates` and inspect the source, generated XML, and validation report.
- **Missing `.npy`:** inspect the score's manifest error and captured CLaMP diagnostics; valid outputs from the same batch remain stored.
- **Unexpected or malformed `.npy`:** inspect captured CLaMP stdout/stderr; unsafe output sets remain fatal and are not partially stored.
- **SQLite extension failure:** install the optional dependency set and ensure the platform has a supported `sqlite-vec` wheel.
- **Dimension mismatch:** confirm that the database and cache use the CLaMP 3 C2 768-dimensional model selected by ADR-0001.
