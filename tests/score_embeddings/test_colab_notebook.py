"""Static contracts for the hosted-GPU score extraction notebook."""

from __future__ import annotations

import ast
import json
from pathlib import Path


NOTEBOOK_PATH = Path(__file__).parents[2] / "notebooks" / "score_embeddings_colab.ipynb"


def _notebook() -> dict:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _sources(notebook: dict, *, cell_type: str | None = None) -> str:
    return "\n".join(
        "".join(cell["source"])
        for cell in notebook["cells"]
        if cell_type is None or cell["cell_type"] == cell_type
    )


def test_notebook_is_valid_v4_json_with_gpu_metadata():
    notebook = _notebook()

    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["accelerator"] == "GPU"
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
    assert notebook["cells"]
    assert all("cell_type" in cell and "source" in cell for cell in notebook["cells"])
    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            ast.parse("".join(cell["source"]))


def test_configuration_is_explicit_and_not_operator_specific():
    source = _sources(_notebook())

    for setting in (
        "WHEEL_UPLOAD_DIR",
        "ADDITIONAL_MEI_INPUTS",
        "CLAMP_TIMEOUT_SECONDS",
        "MINIMUM_VRAM_GB",
        "CUDA_WHEEL_INDEX",
        "TORCH_PACKAGES",
        "DATABASE_PATH",
        "OUTPUT_DIR",
        "ARTIFACT_BASENAME",
    ):
        assert setting in source
    assert "USE_GOOGLE_DRIVE_CACHE = False" in source
    assert 'GOOGLE_DRIVE_CACHE_DIR = ""' in source
    assert "/home/warda" not in source
    assert "s4g4n-dev" not in source
    assert "AIza" not in source


def test_project_is_installed_from_exactly_one_uploaded_wheel_without_git():
    source = _sources(_notebook(), cell_type="code")
    lowered = source.lower()

    assert 'glob("encoding_music_mcp-*.whl")' in source
    assert "No uploaded encoding_music_mcp-*.whl was found" in source
    assert "Multiple encoding_music_mcp-*.whl files were found" in source
    assert '"uv", "venv", "--python", "3.12"' in source
    assert 'f"{PROJECT_WHEEL}[score-embeddings]"' in source
    assert "PIPELINE_CLI.is_file()" in source
    for forbidden in (
        "repository_url",
        "repository_revision",
        '"git"',
        "git clone",
        "git fetch",
        "git checkout",
    ):
        assert forbidden not in lowered


def test_wheel_contains_pipeline_and_bundled_mei_resources():
    source = _sources(_notebook(), cell_type="code")

    assert "zipfile.ZipFile(PROJECT_WHEEL)" in source
    assert '"encoding_music_mcp/score_embeddings/pipeline.py"' in source
    assert 'name.startswith("encoding_music_mcp/resources/mei_files/")' in source
    assert 'name.endswith(".mei")' in source
    assert "BUNDLED_MEI_DIRECTORY" in source
    assert 'files("encoding_music_mcp.resources").joinpath("mei_files")' in source


def test_gpu_preflights_cover_kernel_and_external_clamp_interpreter():
    source = _sources(_notebook(), cell_type="code")

    assert source.count("torch.cuda.is_available()") >= 2
    assert "Runtime > Change runtime type > GPU" in source
    assert "MINIMUM_VRAM_GB" in source
    assert "Select a larger GPU runtime" in source
    assert "separate CLaMP Python" in source
    assert 'CLAMP_PYTHON), "-c", probe_code' in source


def test_notebook_uses_explicit_setup_and_existing_offline_cli():
    source = _sources(_notebook(), cell_type="code")

    assert 'PIPELINE_CLI, "setup"' in source
    assert 'PIPELINE_CLI, "extract"' in source
    assert source.index('PIPELINE_CLI, "setup"') < source.index(
        'PIPELINE_CLI, "extract"'
    )
    assert '"HF_HUB_OFFLINE": "1"' in source
    assert '"TRANSFORMERS_OFFLINE": "1"' in source
    assert "run_pipeline(" not in source
    assert "process_score_to_xml(" not in source
    assert "EmbeddingRecord(" not in source


def test_drive_is_optional_and_only_selects_the_clamp_cache():
    source = _sources(_notebook(), cell_type="code")

    assert "if USE_GOOGLE_DRIVE_CACHE:" in source
    assert "CLAMP_CACHE_DIR = Path(GOOGLE_DRIVE_CACHE_DIR)" in source
    assert 'DATABASE_PATH = RUNTIME_ROOT / "score-embeddings.sqlite3"' in source
    assert 'OUTPUT_DIR = RUNTIME_ROOT / "runs"' in source
    assert "DATABASE_PATH = Path(GOOGLE_DRIVE_CACHE_DIR)" not in source
    assert "OUTPUT_DIR = Path(GOOGLE_DRIVE_CACHE_DIR)" not in source


def test_archive_contract_and_prominent_download_handoff():
    notebook = _notebook()
    source = _sources(notebook, cell_type="code")
    markdown = _sources(notebook, cell_type="markdown")

    assert "packaged_database = payload / DATABASE_PATH.name" in source
    assert 'packaged_manifest = payload / "manifest.json"' in source
    assert 'checksums = payload / "SHA256SUMS"' in source
    assert 'tarfile.open(ARTIFACT_ARCHIVE, "w:gz")' in source
    assert "EmbeddingRepository" in source
    assert "DOWNLOAD REQUIRED BEFORE DISCONNECTING" in source
    assert "remote" in markdown and "Contents" in markdown
    assert "Do not disconnect" in markdown


def test_default_run_is_full_bundled_corpus_with_optional_absolute_additions():
    source = _sources(_notebook(), cell_type="code")

    assert "MEI_INPUTS = [BUNDLED_MEI_DIRECTORY]" in source
    assert "MEI_INPUTS.extend(additional_inputs)" in source
    assert "Additional MEI inputs must be absolute Colab paths" in source
    assert "Bach_BWV_0772.mei" not in source
