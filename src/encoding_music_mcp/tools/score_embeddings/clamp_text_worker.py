"""Resident, offline CLaMP text encoder process.

This module is executed by the separately configured CLaMP interpreter.  It is
not imported by the MCP process, which keeps importing score-embeddings free of
PyTorch and Transformers side effects.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.util
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any


def _send(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, separators=(",", ":")), flush=True)


def _read() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise EOFError("worker input closed")
    value = json.loads(line)
    if not isinstance(value, dict):
        raise ValueError("worker request must be a JSON object")
    return value


def _load_config(code_dir: Path) -> Any:
    spec = importlib.util.spec_from_file_location("clamp3_worker_config", code_dir / "config.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load pinned CLaMP config from {code_dir}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TextRuntime:
    """Pinned full CLaMP runtime used through its native text feature path."""

    def __init__(self, request: dict[str, Any]) -> None:
        import torch
        from transformers import AutoTokenizer, BertConfig

        self.torch = torch
        code_dir = Path(request["checkout_dir"]) / "code"
        checkpoint_path = Path(request["weight_path"])
        expected_dimension = int(request["expected_dimension"])
        config = _load_config(code_dir)
        sys.path.insert(0, str(code_dir))
        clamp_utils = importlib.import_module("utils")
        self.max_length = int(config.MAX_TEXT_LENGTH)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.device.type == "cpu":
            import os
            torch.set_num_threads(min(8, os.cpu_count() or 4))

        started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(
            config.TEXT_MODEL_NAME,
            local_files_only=True,
        )
        audio_config = BertConfig(
            vocab_size=1,
            hidden_size=config.AUDIO_HIDDEN_SIZE,
            num_hidden_layers=config.AUDIO_NUM_LAYERS,
            num_attention_heads=config.AUDIO_HIDDEN_SIZE // 64,
            intermediate_size=config.AUDIO_HIDDEN_SIZE * 4,
            max_position_embeddings=config.MAX_AUDIO_LENGTH,
        )
        symbolic_config = BertConfig(
            vocab_size=1,
            hidden_size=config.M3_HIDDEN_SIZE,
            num_hidden_layers=config.PATCH_NUM_LAYERS,
            num_attention_heads=config.M3_HIDDEN_SIZE // 64,
            intermediate_size=config.M3_HIDDEN_SIZE * 4,
            max_position_embeddings=config.PATCH_LENGTH,
        )
        self.model = clamp_utils.CLaMP3Model(
            audio_config=audio_config,
            symbolic_config=symbolic_config,
            text_model_name=config.TEXT_MODEL_NAME,
            hidden_size=expected_dimension,
            load_m3=config.CLAMP3_LOAD_M3,
        )
        model_loaded = time.perf_counter()

        checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
        state = checkpoint.get("model")
        if not isinstance(state, dict):
            raise RuntimeError("CLaMP checkpoint does not contain a model state dictionary")
        self.model.load_state_dict(state, strict=True)
        # load_state_dict copies the tensors into the model. Release both
        # references to the multi-GB checkpoint before device transfer and
        # warm-up, otherwise startup holds two complete models in memory.
        del state, checkpoint
        self.model.to(self.device).eval()
        checkpoint_loaded = time.perf_counter()

        self.encode(["Warm-up music description."])
        warmed = time.perf_counter()
        self.startup_timings = {
            "model_and_tokenizer_load_seconds": model_loaded - started,
            "checkpoint_load_seconds": checkpoint_loaded - model_loaded,
            "warmup_seconds": warmed - checkpoint_loaded,
        }

    def _prepare_text(self, text: str) -> str:
        # Match the pinned extractor for ordinary and multi-line .txt inputs.
        lines = [line for line in list(set(text.split("\n"))) if line]
        return self.tokenizer.sep_token.join(lines)

    def encode(self, texts: list[str]) -> tuple[list[list[float]], float, float]:
        torch = self.torch
        tokenise_started = time.perf_counter()
        token_ids = self.tokenizer(
            [self._prepare_text(text) for text in texts],
            padding=False,
            truncation=False,
        )["input_ids"]
        segments: list[list[int]] = []
        prompt_segments: list[tuple[int, list[int]]] = []
        for input_ids in token_ids:
            start = len(segments)
            prompt_chunks = [
                input_ids[index : index + self.max_length]
                for index in range(0, len(input_ids), self.max_length)
            ]
            prompt_chunks[-1] = input_ids[-self.max_length :]
            segments.extend(prompt_chunks)
            full_chunks, remainder = divmod(len(input_ids), self.max_length)
            weights = [self.max_length] * full_chunks
            if remainder:
                weights.append(remainder)
            prompt_segments.append((start, weights))
        input_tensor = torch.full(
            (len(segments), self.max_length),
            self.tokenizer.pad_token_id,
            dtype=torch.long,
        )
        mask_tensor = torch.zeros(
            (len(segments), self.max_length),
            dtype=torch.long,
        )
        for index, segment in enumerate(segments):
            length = len(segment)
            input_tensor[index, :length] = torch.tensor(segment, dtype=torch.long)
            mask_tensor[index, :length] = 1
        tokenised = time.perf_counter()
        input_tensor, mask_tensor = torch.stack((input_tensor, mask_tensor)).to(
            self.device
        )
        with torch.inference_mode():
            segment_features = self.model.get_text_features(
                text_inputs=input_tensor,
                text_masks=mask_tensor,
                get_global=True,
            )
            projected = []
            for start, weights in prompt_segments:
                weight_tensor = torch.tensor(
                    weights,
                    device=self.device,
                    dtype=segment_features.dtype,
                ).unsqueeze(-1)
                features = segment_features[start : start + len(weights)]
                projected.append((features * weight_tensor).sum(0) / weight_tensor.sum())
            projected = torch.stack(projected)
        if self.device.type == "cuda":
            torch.cuda.synchronize(self.device)
        inferred = time.perf_counter()
        raw = projected.float().cpu().numpy().tolist()
        return raw, tokenised - tokenise_started, inferred - tokenised


def main() -> int:
    booted = time.perf_counter()
    _send({"event": "booted"})
    try:
        request = _read()
        if request.get("operation") != "initialize":
            raise ValueError("first worker request must initialize the runtime")
        # Keep all third-party informational prints away from protocol stdout.
        with contextlib.redirect_stdout(sys.stderr):
            runtime = TextRuntime(request)
        _send(
            {
                "event": "ready",
                "timings": runtime.startup_timings,
                "device": str(runtime.device),
                "precision": "float32",
                "worker_initialization_seconds": time.perf_counter() - booted,
            }
        )
    except Exception as exc:
        _send(
            {
                "event": "fatal",
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }
        )
        return 1

    for line in sys.stdin:
        try:
            request = json.loads(line)
            operation = request.get("operation")
            if operation == "shutdown":
                _send({"event": "stopped"})
                return 0
            if operation != "encode":
                raise ValueError(f"Unsupported worker operation: {operation!r}")
            texts = request.get("texts")
            if not isinstance(texts, list) or not all(isinstance(text, str) for text in texts):
                raise ValueError("encode texts must be a list of strings")
            raw, tokenisation, inference = runtime.encode(texts)
            _send(
                {
                    "event": "encoded",
                    "request_id": request.get("request_id"),
                    "texts": texts,
                    "raw": raw,
                    "timings": {
                        "tokenisation_seconds": tokenisation,
                        "model_inference_seconds": inference,
                    },
                }
            )
        except Exception as exc:
            _send(
                {
                    "event": "error",
                    "request_id": request.get("request_id") if isinstance(request, dict) else None,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
