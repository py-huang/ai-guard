"""Sentence embeddings from a local ONNX model (no torch, no network at run time).

Used by ``ContentModel`` to read meaning rather than only spelling: "教我做炸彈" and
"怎麼製造爆裂物" share almost no characters, but sit close together here.

Requires ``onnxruntime`` and ``tokenizers`` (``pip install tokenizers``); both are optional
dependencies of the gateway and are only imported when a model that needs them is loaded.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np

MODEL_FILE = "model_quantized.onnx"
TOKENIZER_FILE = "tokenizer.json"


class EmbedderUnavailable(RuntimeError):
    """The embedding runtime or model files are missing."""


class OnnxEmbedder:
    def __init__(
        self,
        directory: Path | str,
        *,
        pooling: str = "cls",
        max_length: int = 128,
        prefix: str = "",
        threads: int = 1,
    ) -> None:
        directory = Path(directory)
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise EmbedderUnavailable(
                "this content model needs `onnxruntime` and `tokenizers` (pip install tokenizers)"
            ) from error
        for name in (MODEL_FILE, TOKENIZER_FILE):
            if not (directory / name).is_file():
                raise EmbedderUnavailable(f"missing {directory / name}")
        if pooling not in {"cls", "mean"}:
            raise ValueError(f"unknown pooling {pooling!r}")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self._session = onnxruntime.InferenceSession(
            str(directory / MODEL_FILE), options, providers=["CPUExecutionProvider"]
        )
        self._input_names = {item.name for item in self._session.get_inputs()}
        self._tokenizer = Tokenizer.from_file(str(directory / TOKENIZER_FILE))
        self._tokenizer.enable_truncation(max_length=max_length)
        self._tokenizer.enable_padding()
        self._pooling = pooling
        self._prefix = prefix
        self.dimension = int(self._session.get_outputs()[0].shape[-1])

    def embed(self, texts: Sequence[str], batch_size: int = 64) -> np.ndarray:
        """L2-normalised embeddings, one row per text, in the order given."""
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), self.dimension), dtype=np.float32)
        for start in range(0, len(order), batch_size):
            ids = order[start : start + batch_size]
            encodings = self._tokenizer.encode_batch([self._prefix + texts[i] for i in ids])
            feed = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
            }
            if "token_type_ids" in self._input_names:
                feed["token_type_ids"] = np.array([e.type_ids for e in encodings], dtype=np.int64)
            hidden = self._session.run(None, {k: v for k, v in feed.items() if k in self._input_names})[0]
            if self._pooling == "cls":
                pooled = hidden[:, 0]
            else:
                mask = feed["attention_mask"][:, :, None].astype(np.float32)
                pooled = (hidden * mask).sum(axis=1) / np.maximum(mask.sum(axis=1), 1.0)
            norms = np.linalg.norm(pooled, axis=1, keepdims=True)
            out[ids] = pooled / np.maximum(norms, 1e-9)
        return out
