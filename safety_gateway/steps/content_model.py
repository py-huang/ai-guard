"""A small trained text classifier that sits behind the phrase rules.

Phrase rules are precise but cannot reach most natural-language abuse. This model covers that
gap with two linear heads blended into one score:

  * hashed character n-grams (spelling; needs only numpy), and
  * a sentence embedding from a small local ONNX model (meaning; optional, see embedder.py).

There is no scikit-learn, no pickle and no network at run time: a few milliseconds a message.

The artifact is a directory written by ``scripts/train_content_model.py``:

  weights.npz   float32 arrays only (loaded with allow_pickle=False)
  meta.json     labels, hashing parameters, blend, threshold, training metrics
  embedder/     the ONNX model + tokenizer, when the embedding head is used

Training data and the trained artifact live under ``.cache/`` and are git-ignored. When no
artifact is present the gateway simply runs on its rules, exactly as before.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from safety_gateway.steps.embedder import OnnxEmbedder
from safety_gateway.steps.finetuned import FinetunedClassifier

ARTIFACT_VERSION = 2
WEIGHTS_FILE = "weights.npz"
META_FILE = "meta.json"
EMBEDDER_DIR = "embedder"
FINETUNED_DIR = "finetuned"
# Longer texts are outside what the model was trained on (short child messages).
MAX_TEXT_CHARS = 400

_WHITESPACE = re.compile(r"\s+")

# The block classes the model can name, mapped onto the gateway's existing child messages.
LABEL_TO_CATEGORY: dict[str, str] = {
    "toxic": "hate_speech",
    "unsafe": "illegal",
    "injection": "prompt_injection",
}


def normalize(text: str) -> str:
    return _WHITESPACE.sub("", unicodedata.normalize("NFKC", text).casefold())


def featurize(
    text: str, *, buckets: int, ngram_range: tuple[int, int]
) -> tuple[np.ndarray, np.ndarray]:
    """Hashed, sublinear-tf, L2-normalised character n-grams (identical at train and run time)."""
    padded = "\x02" + normalize(text) + "\x03"
    counts: dict[int, int] = {}
    low, high = ngram_range
    for size in range(low, high + 1):
        for start in range(len(padded) - size + 1):
            key = zlib.crc32(padded[start : start + size].encode("utf-8")) % buckets
            counts[key] = counts.get(key, 0) + 1
    if not counts:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    indices = np.fromiter(counts.keys(), dtype=np.int64, count=len(counts))
    values = np.array([1.0 + math.log(c) for c in counts.values()], dtype=np.float32)
    values /= np.linalg.norm(values)
    return indices, values


@dataclass(frozen=True)
class ModelVerdict:
    block_score: float  # probability that the message should be blocked
    category: str | None  # gateway category when blocked, else None
    label: str | None  # model label (toxic / unsafe / injection) when blocked

    @property
    def blocked(self) -> bool:
        return self.category is not None


def _sigmoid(margin: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, margin))))


class ContentModel:
    def __init__(
        self,
        *,
        block_weights: np.ndarray,
        block_bias: float,
        label_weights: np.ndarray,
        label_bias: np.ndarray,
        labels: list[str],
        buckets: int,
        ngram_range: tuple[int, int],
        threshold: float,
        label_thresholds: dict[str, float] | None = None,
        embedder: OnnxEmbedder | None = None,
        embed_weights: np.ndarray | None = None,
        embed_bias: float = 0.0,
        embed_label_weights: np.ndarray | None = None,
        blend: tuple[float, float] = (1.0, 0.0),
        finetuned: FinetunedClassifier | None = None,
        finetuned_weight: float = 0.0,
        meta: dict | None = None,
    ) -> None:
        self._block_w = block_weights.astype(np.float32, copy=False)
        self._block_b = float(block_bias)
        self._label_w = label_weights.astype(np.float32, copy=False)
        self._label_b = label_bias.astype(np.float32, copy=False)
        self.labels = labels
        self.buckets = buckets
        self.ngram_range = ngram_range
        self.threshold = threshold  # floor: below this nothing is blocked, whatever the label
        # Each kind of harm can need its own bar: precise labels can be caught earlier than noisy ones.
        self.label_thresholds = {**{label: threshold for label in labels}, **(label_thresholds or {})}
        self.embedder = embedder
        self._embed_w = None if embed_weights is None else embed_weights.astype(np.float32, copy=False)
        self._embed_b = float(embed_bias)
        self._embed_label_w = (
            None if embed_label_weights is None else embed_label_weights.astype(np.float32, copy=False)
        )
        self.blend = blend  # (weight of the character margin, weight of the embedding margin)
        # Optional fine-tuned encoder: adds its own margin to the blend and, when present, names the label.
        self.finetuned = finetuned
        self.finetuned_weight = float(finetuned_weight)
        self.meta = meta or {}
        if embedder is not None and (self._embed_w is None or self._embed_label_w is None):
            raise ValueError("an embedder needs embedding weights")

    def margins(self, text: str, embedding: np.ndarray | None = None) -> tuple[float, float]:
        """(character margin, embedding margin) of a text; the second is 0 without an embedder."""
        indices, values = featurize(text, buckets=self.buckets, ngram_range=self.ngram_range)
        char = float(self._block_w[indices] @ values) + self._block_b
        if self.embedder is None or (self.blend[1] == 0.0 and embedding is None):
            return char, 0.0  # no embedder, or its margin carries no weight in the blend
        if embedding is None:
            embedding = self.embedder.embed([text])[0]
        return char, float(self._embed_w @ embedding) + self._embed_b

    def finetuned_logits(self, text: str) -> np.ndarray | None:
        return None if self.finetuned is None else self.finetuned.logits([text])[0]

    def block_score(
        self, text: str, embedding: np.ndarray | None = None, finetuned_logits: np.ndarray | None = None
    ) -> float:
        char, emb = self.margins(text, embedding)
        total = self.blend[0] * char + self.blend[1] * emb
        if self.finetuned is not None:
            if finetuned_logits is None:
                finetuned_logits = self.finetuned_logits(text)
            total += self.finetuned_weight * float(FinetunedClassifier.margin(finetuned_logits))
        return _sigmoid(total)

    def predict(self, text: str, embedding: np.ndarray | None = None) -> ModelVerdict:
        if not text or len(text) > MAX_TEXT_CHARS:
            return ModelVerdict(0.0, None, None)
        ft_logits = self.finetuned_logits(text)
        score = self.block_score(text, embedding, ft_logits)
        if score < min(self.threshold, *self.label_thresholds.values()):
            return ModelVerdict(score, None, None)
        if ft_logits is not None:
            label_scores = ft_logits[1:]  # the fine-tuned head names the kind of harm directly
        else:
            indices, values = featurize(text, buckets=self.buckets, ngram_range=self.ngram_range)
            label_scores = self._label_w[:, indices] @ values + self._label_b
            if self.embedder is not None:
                vector = embedding if embedding is not None else self.embedder.embed([text])[0]
                label_scores = label_scores + self._embed_label_w @ vector
        label = self.labels[int(np.argmax(label_scores))]
        if score < self.label_thresholds[label]:
            return ModelVerdict(score, None, None)
        return ModelVerdict(score, LABEL_TO_CATEGORY.get(label, "illegal"), label)

    # --- persistence -------------------------------------------------------------------
    def save(
        self, directory: Path, embedder_source: Path | None = None, finetuned_source: Path | None = None
    ) -> None:
        import shutil

        directory.mkdir(parents=True, exist_ok=True)
        arrays = {
            "block_weights": self._block_w,
            "block_bias": np.float32(self._block_b),
            "label_weights": self._label_w,
            "label_bias": self._label_b,
        }
        if self.embedder is not None:
            arrays["embed_weights"] = self._embed_w
            arrays["embed_bias"] = np.float32(self._embed_b)
            arrays["embed_label_weights"] = self._embed_label_w
            if embedder_source is not None:
                target = directory / EMBEDDER_DIR
                target.mkdir(exist_ok=True)
                for name in ("model_quantized.onnx", "tokenizer.json"):
                    shutil.copyfile(embedder_source / name, target / name)
        if self.finetuned is not None and finetuned_source is not None:
            target = directory / FINETUNED_DIR
            target.mkdir(exist_ok=True)
            for name in ("model_quantized.onnx", "tokenizer.json", "meta.json"):
                shutil.copyfile(finetuned_source / name, target / name)
        np.savez_compressed(directory / WEIGHTS_FILE, **arrays)
        meta = {
            **self.meta,
            "version": ARTIFACT_VERSION,
            "labels": self.labels,
            "buckets": self.buckets,
            "ngram_range": list(self.ngram_range),
            "threshold": self.threshold,
            "label_thresholds": self.label_thresholds,
            "blend": list(self.blend),
            "finetuned_weight": self.finetuned_weight,
        }
        (directory / META_FILE).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: Path) -> ContentModel:
        meta = json.loads((directory / META_FILE).read_text(encoding="utf-8"))
        if meta.get("version") != ARTIFACT_VERSION:
            raise ValueError(f"unsupported content model version: {meta.get('version')!r}")
        buckets = int(meta["buckets"])
        with np.load(directory / WEIGHTS_FILE, allow_pickle=False) as data:
            arrays = {name: data[name] for name in data.files}
        if arrays["block_weights"].shape != (buckets,) or arrays["label_weights"].shape[1] != buckets:
            raise ValueError("content model weights do not match its metadata")
        embedder = None
        if "embed_weights" in arrays:
            spec = meta["embedder"]
            embedder = OnnxEmbedder(
                directory / EMBEDDER_DIR,
                pooling=spec["pooling"],
                max_length=int(spec["max_length"]),
                prefix=spec.get("prefix", ""),
            )
            if embedder.dimension != arrays["embed_weights"].shape[0]:
                raise ValueError("embedder does not match the trained embedding head")
        finetuned = None
        if (directory / FINETUNED_DIR).is_dir() and float(meta.get("finetuned_weight", 0.0)) != 0.0:
            finetuned = FinetunedClassifier(directory / FINETUNED_DIR)
        return cls(
            block_weights=arrays["block_weights"],
            block_bias=float(arrays["block_bias"]),
            label_weights=arrays["label_weights"],
            label_bias=arrays["label_bias"],
            labels=list(meta["labels"]),
            buckets=buckets,
            ngram_range=(int(meta["ngram_range"][0]), int(meta["ngram_range"][1])),
            threshold=float(meta["threshold"]),
            label_thresholds={k: float(v) for k, v in meta.get("label_thresholds", {}).items()},
            embedder=embedder,
            embed_weights=arrays.get("embed_weights"),
            embed_bias=float(arrays.get("embed_bias", 0.0)),
            embed_label_weights=arrays.get("embed_label_weights"),
            blend=(float(meta["blend"][0]), float(meta["blend"][1])),
            finetuned=finetuned,
            finetuned_weight=float(meta.get("finetuned_weight", 0.0)),
            meta=meta,
        )


def load_if_present(directory: Path | str | None) -> ContentModel | None:
    """The artifact if there is one; ``None`` when the gateway should run on rules alone."""
    if not directory:
        return None
    path = Path(directory)
    if not (path / META_FILE).is_file():
        return None
    return ContentModel.load(path)
