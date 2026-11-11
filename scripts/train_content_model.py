#!/usr/bin/env python3
"""Train the local content-safety classifier from the public corpus built by eval_corpus.py.

  .venv/bin/python scripts/eval_corpus.py fetch && .venv/bin/python scripts/eval_corpus.py build
  .venv/bin/python scripts/train_content_model.py            # writes .cache/models/content_safety
  .venv/bin/python scripts/eval_corpus.py run --split test --engine combined
  .venv/bin/python scripts/eval_corpus.py run --challenge --engine combined

Everything it reads and writes lives under ``.cache/`` (git-ignored): the raw datasets, the
built corpus, the embedding model and the trained artifact. Training needs scikit-learn and
tokenizers (``pip install scikit-learn tokenizers``, or ``--target .cache/pylib``) and the ONNX
embedding model (``--embedder`` directory; see README). The gateway itself needs only numpy,
plus onnxruntime and tokenizers when the embedding head is used.

Anti-confound measures, because a naive classifier on this data learns *style*, not harm:
  * Only rows labelled by their source are used. Sets whose label is "topic is sensitive"
    (mental health, ethics, ...) and the mixed Reverse_Exposure set are left out.
  * Every length bucket is re-weighted to hold as many block as allow examples, so length
    cannot be used as a shortcut.
  * Plenty of ordinary imperative requests (alpaca-zh, TaiwanChat) and protective how-to
    questions (reverse_protective) are allow examples, so "請幫我…" / "怎麼…" is not an attack.
  * Fit on ``train``, choose the blend and threshold on ``val``, never touch ``test``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.append(str(ROOT / ".cache" / "pylib"))

import numpy as np  # noqa: E402

from safety_gateway.steps.content_model import ContentModel, featurize  # noqa: E402

CORPUS = ROOT / ".cache" / "eval-corpus" / "corpus.jsonl"
OUT_DIR = ROOT / ".cache" / "models" / "content_safety"
EMBEDDER_DIR = ROOT / ".cache" / "models" / "embedders" / "bge-small-zh-v1.5"
EMBED_CACHE = ROOT / ".cache" / "models" / "embed-cache"

BLOCK_SETS = {
    "cold_offensive": "toxic",
    "insult": "toxic",
    "unsafe_instruction": "unsafe",
    "goal_hijacking": "injection",
    "injection_en": "injection",
    # Counterfactual templates (tests/synth_content.py): train-side template families only.
    "synth_toxic": "toxic",
    "synth_unsafe": "unsafe",
    "synth_injection": "injection",
    # Public English red-team prompts: teach intent across languages; adult-flavoured, so they
    # never count towards the validation headline (see TRAIN_ONLY).
    "redteam_en": "unsafe",
}
ALLOW_SETS = ("cold_neutral", "benign_instruction", "taiwanchat_benign", "benign_en")
# Harmless sets whose wording is close to the attacks. They are weakly labelled or generated,
# so they never count towards the headline, but the threshold must still keep them mostly allowed.
WEAK_ALLOW_SETS = ("reverse_protective", "synth_allow")
TRAIN_ONLY_ALLOW = ("contrast_safe_en",)  # XSTest-safe / JBB-benign: "sounds dangerous, is fine"
TRAIN_ONLY = frozenset({"redteam_en", *TRAIN_ONLY_ALLOW})
LABELS = ["toxic", "unsafe", "injection"]
LENGTH_EDGES = (12, 24, 48, 96, 200, 400)
SYNTH_WEIGHT = 2.0  # templated rows are few and clean; give them a little more say


def load_rows() -> dict[str, list[tuple[str, str]]]:
    used = set(BLOCK_SETS) | set(ALLOW_SETS) | set(WEAK_ALLOW_SETS) | set(TRAIN_ONLY_ALLOW)
    parts: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for line in CORPUS.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        row = json.loads(line)
        if row["set"] in used:
            parts[row["part"]].append((row["set"], row["text"]))
    return parts


def is_block(name: str) -> bool:
    return name in BLOCK_SETS


def length_bucket(text: str) -> int:
    for index, edge in enumerate(LENGTH_EDGES):
        if len(text) <= edge:
            return index
    return len(LENGTH_EDGES)


def char_matrix(texts: list[str], buckets: int, ngram_range: tuple[int, int]):
    from scipy.sparse import csr_matrix

    data: list[np.ndarray] = []
    cols: list[np.ndarray] = []
    indptr = [0]
    for text in texts:
        indices, values = featurize(text, buckets=buckets, ngram_range=ngram_range)
        cols.append(indices)
        data.append(values)
        indptr.append(indptr[-1] + len(indices))
    return csr_matrix(
        (np.concatenate(data), np.concatenate(cols), np.array(indptr)),
        shape=(len(texts), buckets),
    )


def embeddings(embedder, texts: list[str], tag: str) -> np.ndarray:
    """Embed each distinct text once, ever: a per-text cache keyed by the text's hash."""
    EMBED_CACHE.mkdir(parents=True, exist_ok=True)
    path = EMBED_CACHE / f"{tag}.npz"
    keys: list[str] = []
    vectors = np.zeros((0, embedder.dimension), dtype=np.float32)
    if path.exists():
        with np.load(path, allow_pickle=False) as data:
            keys, vectors = list(data["keys"]), data["vectors"]
    index = {key: i for i, key in enumerate(keys)}
    hashes = [hashlib.sha1(t.encode("utf-8")).hexdigest() for t in texts]
    todo = {h: t for h, t in zip(hashes, texts) if h not in index}
    if todo:
        started = time.time()
        fresh = embedder.embed(list(todo.values()))
        keys += list(todo)
        vectors = np.vstack([vectors, fresh])
        np.savez(path, keys=np.array(keys), vectors=vectors)
        index = {key: i for i, key in enumerate(keys)}
        print(f"  embedded {len(todo)} new texts in {time.time() - started:.0f}s ({len(texts) - len(todo)} cached)")
    return vectors[[index[h] for h in hashes]]


def balanced_weights(rows: list[tuple[str, str]]) -> np.ndarray:
    """Within each length bucket give block and allow rows the same total weight."""
    totals: Counter[tuple[int, bool]] = Counter()
    for name, text in rows:
        totals[(length_bucket(text), is_block(name))] += 1
    weights = np.empty(len(rows), dtype=np.float64)
    for index, (name, text) in enumerate(rows):
        bucket, block = length_bucket(text), is_block(name)
        both = totals[(bucket, True)] + totals[(bucket, False)]
        weights[index] = both / (2.0 * totals[(bucket, block)]) if totals[(bucket, block)] else 1.0
    return weights


def per_set_accuracy(rows: list[tuple[str, str]], scores: np.ndarray, threshold: float) -> dict[str, float]:
    hit: Counter[str] = Counter()
    seen: Counter[str] = Counter()
    for (name, _), score in zip(rows, scores):
        seen[name] += 1
        blocked = score >= threshold
        hit[name] += int(blocked if is_block(name) else not blocked)
    return {name: hit[name] / seen[name] for name in seen}


def sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--buckets", type=int, default=1 << 19)
    parser.add_argument("--ngram-min", type=int, default=1)
    parser.add_argument("--ngram-max", type=int, default=3)
    parser.add_argument("--c-char", type=float, nargs="+", default=[4.0, 16.0])
    parser.add_argument("--synth-weight", type=float, default=SYNTH_WEIGHT)
    parser.add_argument("--redteam-weight", type=float, default=0.6, help="weight of the English red-team rows")
    parser.add_argument("--c-embed", type=float, nargs="+", default=[4.0, 32.0])
    parser.add_argument("--embedder", type=Path, default=EMBEDDER_DIR, help="ONNX embedder dir, or 'none'")
    parser.add_argument("--pooling", default="cls", help="cls (bge) or mean (e5)")
    parser.add_argument("--prefix", default="", help='text prefix the embedder expects, e.g. "query: " for e5')
    parser.add_argument("--min-allow", type=float, default=0.95, help="floor for every authoritative allow set on val")
    parser.add_argument("--min-weak-allow", type=float, default=0.92,
                        help="floor for the weakly labelled / generated allow sets (hard negatives)")
    parser.add_argument("--finetuned", type=Path, default=None,
                        help="dir from scripts/finetune_content_model.py; adds its margin to the blend and names the label")
    parser.add_argument("--out", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    if not CORPUS.exists():
        print("run eval_corpus.py fetch and build first")
        return 2
    from sklearn.linear_model import LogisticRegression

    ngram_range = (args.ngram_min, args.ngram_max)
    parts = load_rows()
    train, val = parts["train"], parts["val"]
    from tests.synth_content import family_part, generate

    everything = generate()
    synth_train = [s for s in everything if family_part(s.family) == "train"]
    synth_val = [s for s in everything if family_part(s.family) == "val"]
    train = train + [(f"synth_{s.label}", s.text) for s in synth_train]
    val = val + [(f"synth_{s.label}", s.text) for s in synth_val]
    print(f"synthetic rows: {len(synth_train)} train / {len(synth_val)} val template families "
          f"({sum(family_part(s.family) == 'test' for s in everything)} held out for the final test)")
    print(f"train {len(train)}  val {len(val)}  (test is never loaded: {len(parts['test'])} rows held out)")
    texts_train, texts_val = [t for _, t in train], [t for _, t in val]
    y_train = np.array([int(is_block(n)) for n, _ in train])
    y_val = np.array([int(is_block(n)) for n, _ in val])
    w_train, w_val = balanced_weights(train), balanced_weights(val)
    w_train = w_train * np.array([args.synth_weight if n.startswith("synth_") else args.redteam_weight if n in TRAIN_ONLY else 1.0 for n, _ in train])

    # --- character head -----------------------------------------------------------------
    x_train = char_matrix(texts_train, args.buckets, ngram_range)
    x_val = char_matrix(texts_val, args.buckets, ngram_range)
    best_char = None
    for c in args.c_char:
        model = LogisticRegression(C=c, solver="liblinear", max_iter=200).fit(x_train, y_train, sample_weight=w_train)
        loss = float(np.average(-np.log(np.where(y_val == 1, sigmoid(x_val @ model.coef_[0] + model.intercept_[0]), 1 - sigmoid(x_val @ model.coef_[0] + model.intercept_[0])) + 1e-9), weights=w_val))
        print(f"char C={c:<5} val weighted log-loss {loss:.4f}")
        if best_char is None or loss < best_char[0]:
            best_char = (loss, c, model)
    _, c_char, char_model = best_char
    m_val_char = x_val @ char_model.coef_[0] + char_model.intercept_[0]

    # --- embedding head -----------------------------------------------------------------
    embedder = None
    embed_model = None
    m_val_emb = np.zeros(len(val))
    e_train = e_val = None
    if str(args.embedder).lower() != "none":
        from safety_gateway.steps.embedder import OnnxEmbedder

        embedder = OnnxEmbedder(args.embedder, pooling=args.pooling, prefix=args.prefix, threads=4)
        tag = args.embedder.name
        e_train = embeddings(embedder, texts_train, tag)
        e_val = embeddings(embedder, texts_val, tag)
        best_emb = None
        for c in args.c_embed:
            model = LogisticRegression(C=c, solver="lbfgs", max_iter=500).fit(e_train, y_train, sample_weight=w_train)
            margin = e_val @ model.coef_[0] + model.intercept_[0]
            p = sigmoid(margin)
            loss = float(np.average(-np.log(np.where(y_val == 1, p, 1 - p) + 1e-9), weights=w_val))
            print(f"embed C={c:<5} val weighted log-loss {loss:.4f}")
            if best_emb is None or loss < best_emb[0]:
                best_emb = (loss, c, model)
        _, c_embed, embed_model = best_emb
        m_val_emb = e_val @ embed_model.coef_[0] + embed_model.intercept_[0]

    # --- fine-tuned encoder (optional): its logits on val -------------------------------
    finetuned = None
    m_val_ft = np.zeros(len(val))
    ft_logits_val = None
    if args.finetuned is not None:
        from safety_gateway.steps.finetuned import FinetunedClassifier

        finetuned = FinetunedClassifier(args.finetuned, threads=4)
        started = time.time()
        ft_logits_val = finetuned.logits(texts_val)
        m_val_ft = FinetunedClassifier.margin(ft_logits_val)
        print(f"fine-tuned encoder scored {len(val)} val texts in {time.time() - started:.0f}s")

    # --- blend: a few numbers fitted on val ---------------------------------------------
    columns = [m_val_char]
    if embed_model is not None:
        columns.append(m_val_emb)
    if finetuned is not None:
        columns.append(m_val_ft)
    if len(columns) > 1:
        blend_model = LogisticRegression(C=100.0).fit(np.column_stack(columns), y_val, sample_weight=w_val)
        coef = list(map(float, blend_model.coef_[0]))
        blend = (coef[0], coef[1] if embed_model is not None else 0.0)
        ft_weight = coef[-1] if finetuned is not None else 0.0
        blend_bias = float(blend_model.intercept_[0])
    else:
        blend, ft_weight, blend_bias = (1.0, 0.0), 0.0, 0.0
    scores = sigmoid(blend[0] * m_val_char + blend[1] * m_val_emb + ft_weight * m_val_ft + blend_bias)
    print(f"blend: char x{blend[0]:.2f}  embed x{blend[1]:.2f}  fine-tuned x{ft_weight:.2f}  bias {blend_bias:+.2f}")

    # --- which kind of harm: heads trained on block rows only ---------------------------
    block_idx = [i for i, (n, _) in enumerate(train) if is_block(n)]
    y_label = np.array([LABELS.index(BLOCK_SETS[train[i][0]]) for i in block_idx])
    label_char = LogisticRegression(C=c_char, solver="lbfgs", max_iter=300).fit(x_train[block_idx], y_label)
    label_embed = None
    if embedder is not None:
        label_embed = LogisticRegression(C=c_embed, solver="lbfgs", max_iter=500).fit(e_train[block_idx], y_label)
    label_scores = x_val @ label_char.coef_.T + label_char.intercept_
    if label_embed is not None:
        label_scores = label_scores + e_val @ label_embed.coef_.T
    predicted = np.argmax(label_scores, axis=1)
    if ft_logits_val is not None:
        predicted = np.argmax(ft_logits_val[:, 1:], axis=1)  # the fine-tuned head names the harm

    # --- one threshold per kind of harm, searched jointly on val ------------------------
    set_names = sorted({n for n, _ in val})
    masks = {n: np.array([name == n for name, _ in val]) for n in set_names}
    core_sets = [n for n in set_names if (n in BLOCK_SETS and not n.startswith('synth_') and n not in TRAIN_ONLY) or n in ALLOW_SETS]
    grid = np.arange(0.30, 0.981, 0.025)
    best = None
    for t_toxic in grid:
        for t_unsafe in grid:
            for t_injection in grid:
                cut = np.array([t_toxic, t_unsafe, t_injection])[predicted]
                blocked = scores >= cut
                accuracy = {
                    n: float(blocked[masks[n]].mean() if is_block(n) else 1 - blocked[masks[n]].mean())
                    for n in set_names
                }
                if min(accuracy[n] for n in ALLOW_SETS if n in accuracy) < args.min_allow:
                    continue
                if min(accuracy[n] for n in WEAK_ALLOW_SETS if n in accuracy) < args.min_weak_allow:
                    continue
                macro = sum(accuracy[n] for n in core_sets) / len(core_sets)
                if best is None or macro > best[0]:
                    best = (macro, (float(t_toxic), float(t_unsafe), float(t_injection)), accuracy)
    if best is None:
        print(f"no thresholds keep every allow set at >= {args.min_allow:.0%} on val")
        return 1
    macro, cuts, accuracy = best
    thresholds = dict(zip(LABELS, cuts))
    print("\nthresholds " + "  ".join(f"{k}={v:.3f}" for k, v in thresholds.items()) + f"   val macro accuracy {macro:.1%}")
    for name, value in sorted(accuracy.items()):
        print(f"  {name:20} {value:6.1%}")

    # Fold the blend into the heads so inference is a single sum (a*m_char + b*m_emb + bias).
    artifact = ContentModel(
        block_weights=char_model.coef_[0] * blend[0],
        block_bias=float(char_model.intercept_[0]) * blend[0] + blend_bias,
        label_weights=label_char.coef_,
        label_bias=label_char.intercept_,
        labels=LABELS,
        buckets=args.buckets,
        ngram_range=ngram_range,
        threshold=min(cuts),
        label_thresholds=thresholds,
        embedder=embedder,
        embed_weights=None if embed_model is None else embed_model.coef_[0] * blend[1],
        embed_bias=0.0 if embed_model is None else float(embed_model.intercept_[0]) * blend[1],
        embed_label_weights=None if label_embed is None else label_embed.coef_,
        blend=(1.0, 1.0),
        finetuned=finetuned,
        finetuned_weight=ft_weight,
        meta={
            "trained_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "corpus_sha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest(),
            "train_rows": len(train),
            "val_rows": len(val),
            "C_char": c_char,
            "val_per_set_accuracy": {k: round(v, 4) for k, v in accuracy.items()},
            "val_macro_accuracy": round(macro, 4),
            "finetuned": None if finetuned is None else {"name": args.finetuned.name, **finetuned.meta},
            "embedder": None
            if embedder is None
            else {"name": args.embedder.name, "pooling": args.pooling, "max_length": 128, "prefix": args.prefix},
        },
    )
    artifact.save(
        args.out,
        embedder_source=args.embedder if embedder is not None else None,
        finetuned_source=args.finetuned,
    )
    print(f"\nsaved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
