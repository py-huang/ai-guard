"""A fine-tuned small multilingual encoder with a 4-way head, run from ONNX (no torch, no network).

The frozen-embedding heads in ``ContentModel`` read meaning but cannot adapt it: "教我做炸彈" and
"教我做蛋糕" sit close together in a general-purpose embedding space. Fine-tuning moves them apart.
Training happens offline (``scripts/finetune_content_model.py``, needs torch); this module only
needs ``onnxruntime`` and ``tokenizers``.

Output classes, in order: allow, toxic, unsafe, injection.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from safety_gateway.steps.embedder import EmbedderUnavailable

MODEL_FILE = "model_quantized.onnx"
TOKENIZER_FILE = "tokenizer.json"
META_FILE = "meta.json"
CLASSES = ("allow", "toxic", "unsafe", "injection")


def _logsumexp(values: np.ndarray, axis: int = -1) -> np.ndarray:
    peak = values.max(axis=axis, keepdims=True)
    return (peak + np.log(np.exp(values - peak).sum(axis=axis, keepdims=True))).squeeze(axis)


class FinetunedClassifier:
    def __init__(self, directory: Path | str, *, threads: int = 1) -> None:
        directory = Path(directory)
        try:
            import onnxruntime
            from tokenizers import Tokenizer
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise EmbedderUnavailable("the fine-tuned classifier needs `onnxruntime` and `tokenizers`") from error
        for name in (MODEL_FILE, TOKENIZER_FILE, META_FILE):
            if not (directory / name).is_file():
                raise EmbedderUnavailable(f"missing {directory / name}")
        meta = json.loads((directory / META_FILE).read_text(encoding="utf-8"))
        if tuple(meta.get("classes", ())) != CLASSES:
            raise ValueError(f"unexpected classes in {directory / META_FILE}: {meta.get('classes')!r}")
        options = onnxruntime.SessionOptions()
        options.intra_op_num_threads = threads
        options.inter_op_num_threads = 1
        self._session = onnxruntime.InferenceSession(
            str(directory / MODEL_FILE), options, providers=["CPUExecutionProvider"]
        )
        self._input_names = {item.name for item in self._session.get_inputs()}
        self._tokenizer = Tokenizer.from_file(str(directory / TOKENIZER_FILE))
        self._tokenizer.enable_truncation(max_length=int(meta["max_length"]))
        self._tokenizer.enable_padding()
        self._prefix = str(meta.get("prefix", ""))
        self.meta = meta

    def logits(self, texts: Sequence[str], batch_size: int = 64) -> np.ndarray:
        """Raw class scores, shape (len(texts), 4), in the order given."""
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), len(CLASSES)), dtype=np.float32)
        for start in range(0, len(order), batch_size):
            ids = order[start : start + batch_size]
            encodings = self._tokenizer.encode_batch([self._prefix + texts[i] for i in ids])
            feed = {
                "input_ids": np.array([e.ids for e in encodings], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in encodings], dtype=np.int64),
            }
            out[ids] = self._session.run(None, {k: v for k, v in feed.items() if k in self._input_names})[0]
        return out

    @staticmethod
    def margin(logits: np.ndarray) -> np.ndarray:
        """log-odds that a text is *any* kind of unsafe: logsumexp(harm classes) - allow."""
        return _logsumexp(logits[..., 1:]) - logits[..., 0]
