# GPU extraction notebook

## Purpose

Provide a VS Code/Google Colab notebook that runs the existing standalone score-embedding pipeline on a hosted CUDA kernel and returns durable embedding artifacts to the operator's local machine. It does not add hosted inference, expose batch generation through MCP, change score validation, or duplicate extraction and storage logic.

## Components

| File | Purpose |
|---|---|
| `notebooks/score_embeddings_colab.ipynb` | Configurable GPU preflight, isolated CLaMP provisioning, pinned setup, extraction, artifact packaging, and local-download handoff |
| `tests/score_embeddings/test_colab_notebook.py` | Static notebook contract coverage without network, CLaMP weights, or accelerator hardware |
| `docs/getting-started/clamp3-pipeline.md` | Operator instructions for Colab kernels, local artifact retrieval, and optional cache persistence |
| `docs/development/structure.md` | Project-layout entry for the operational notebook |

## Configuration

The notebook consumes one locally built `encoding_music_mcp-*.whl` uploaded to the Colab runtime. It exposes additional MEI input paths, CLaMP timeout, CUDA PyTorch wheel index, minimum VRAM, optional Google Drive cache path, and local artifact naming as explicit parameters. It contains no Git bootstrap, credentials, repository revisions, or operator-specific paths.

The default input is the complete installed `encoding_music_mcp.resources/mei_files` directory from the uploaded wheel. Operators may add absolute Colab paths for separately uploaded MEI files or directories without replacing the bundled-corpus default.

Google Drive persistence is disabled by default and, when enabled, is limited to the reusable CLaMP checkout/model cache. The SQLite database and run manifest are produced on the Colab runtime, packaged with a SHA-256 checksum, and explicitly downloaded through the VS Code Colab extension's remote Contents view.

## Integration points

The notebook provisions a Python 3.12 project environment from the uploaded wheel and the ADR-0001 external Python 3.10/PyTorch runtime, invokes the existing `encoding-music-embeddings setup` and `extract` interfaces, and packages the ADR-0003 SQLite database plus the pipeline run manifest. It does not import the MCP server or alter ADR-0004 query behavior.

## Testing

- Parse the notebook as valid version-4 notebook JSON.
- Verify actionable CUDA and minimum-VRAM preflight guards.
- Verify the external CLaMP interpreter checks CUDA independently of the notebook kernel.
- Verify setup is explicit and extraction invokes the existing project CLI rather than duplicating pipeline logic.
- Verify Git commands, repository URLs, and revision configuration are absent.
- Verify exactly one uploaded project wheel is required with actionable missing/ambiguous diagnostics and installed with the score-embedding dependencies.
- Verify the complete installed `mei_files` resource directory is the default input, with additional absolute uploaded paths configurable.
- Verify cache, output, timeout, CUDA wheel settings, and artifact naming remain configurable without embedded secrets or personal paths.
- Verify successful output is bundled with the SQLite database, run manifest, and SHA-256 checksum for local download.
- Verify Google Drive is optional, disabled by default, and limited to CLaMP cache persistence.
- Build and inspect the local wheel, run the focused notebook contract tests, existing score-embedding suite, Ruff checks, and the bundled-corpus workflow on a real Colab GPU kernel.

Automated verification: 9 focused notebook contract tests and the 87-test score-embedding suite pass without network, model weights, or accelerator hardware; Ruff and whitespace checks pass. A built wheel contains the pipeline entry point and 371 bundled MEI files, and an isolated Python 3.12 smoke environment installs the wheel, resolves all 371 resources, and exposes `encoding-music-embeddings`.

Operational verification: the complete bundled-corpus workflow ran on a real Colab GPU. It discovered 337 score inputs, stored 290 embeddings, retained 31 MusicXML validation failures and 16 CLaMP omissions as per-score diagnostics, and completed with no run-level error. The archive was downloaded locally, both entries in `SHA256SUMS` passed, and `EmbeddingRepository` opened all 290 stored rows.

The extraction CLI may return status 1 when individual inputs are rejected. The notebook treats the run as packageable only when the newly written manifest has no `run_error` and the SQLite database exists, preserving per-score validation diagnostics without discarding successful embeddings.

Confirmed 2026-08-28
