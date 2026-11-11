#!/usr/bin/env python3
"""Fine-tune a small multilingual encoder as a 4-way content classifier, then export it to ONNX.

Offline only: needs torch + transformers (installed under .cache/pylib-ft, never in the gateway's
runtime). The result is a directory the gateway loads with onnxruntime alone:

  .venv/bin/python scripts/finetune_content_model.py --model intfloat/multilingual-e5-small
  .venv/bin/python scripts/train_content_model.py --embedder ... --finetuned .cache/models/ft/e5-small

Same data, same train/val/test discipline as train_content_model.py: the test half and the hand-written
holdout sets are never read here. No LLM is involved: this is ordinary supervised classifier training.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.append(str(ROOT / ".cache" / "pylib"))
sys.path.append(str(ROOT / ".cache" / "pylib-ft"))

import numpy as np  # noqa: E402
import train_content_model as base  # noqa: E402

CLASSES = ["allow", "toxic", "unsafe", "injection"]
HF_CACHE = ROOT / ".cache" / "hf"
OUT = ROOT / ".cache" / "models" / "ft" / "e5-small"


def class_of(name: str) -> int:
    return CLASSES.index("allow") if not base.is_block(name) else CLASSES.index(base.BLOCK_SETS[name])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", default="intfloat/multilingual-e5-small")
    parser.add_argument("--prefix", default="query: ")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=4e-5)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=64)
    parser.add_argument("--synth-weight", type=float, default=6.0)
    parser.add_argument("--redteam-weight", type=float, default=0.6)
    parser.add_argument("--label-smoothing", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--max-train", type=int, default=0, help="debug: only use this many training rows")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    import torch
    from torch import nn
    from transformers import AutoModel, AutoTokenizer

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

    from tests.synth_content import family_part, generate

    parts = base.load_rows()
    train, val = parts["train"], parts["val"]
    everything = generate()
    train += [(f"synth_{s.label}", s.text) for s in everything if family_part(s.family) == "train"]
    val += [(f"synth_{s.label}", s.text) for s in everything if family_part(s.family) == "val"]
    if args.max_train:
        random.shuffle(train)
        train = train[: args.max_train]
    print(f"train {len(train)}  val {len(val)}  device {device}  model {args.model}", flush=True)

    def weights_for(rows):
        w = base.balanced_weights(rows)
        mult = np.array([
            args.synth_weight if n.startswith("synth_") else args.redteam_weight if n in base.TRAIN_ONLY else 1.0
            for n, _ in rows
        ])
        w = w * mult
        return (w / w.mean()).astype(np.float32)

    w_train, w_val = weights_for(train), weights_for(val)
    y_train = np.array([class_of(n) for n, _ in train])
    y_val = np.array([class_of(n) for n, _ in val])

    tokenizer = AutoTokenizer.from_pretrained(args.model, cache_dir=HF_CACHE)
    encoder = AutoModel.from_pretrained(args.model, cache_dir=HF_CACHE)

    class Classifier(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = encoder
            self.dropout = nn.Dropout(0.1)
            self.head = nn.Linear(encoder.config.hidden_size, len(CLASSES))

        def forward(self, input_ids, attention_mask):  # type: ignore[no-untyped-def]
            hidden = self.encoder(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
            mask = attention_mask.unsqueeze(-1).to(hidden.dtype)
            pooled = (hidden * mask).sum(1) / mask.sum(1).clamp(min=1.0)
            return self.head(self.dropout(pooled))

    model = Classifier().to(device)

    def encode(texts: list[str]):
        batch = tokenizer([args.prefix + t for t in texts], padding=True, truncation=True,
                          max_length=args.max_length, return_tensors="pt")
        return batch["input_ids"].to(device), batch["attention_mask"].to(device)

    def predict_logits(texts: list[str], batch: int = 128) -> np.ndarray:
        model.eval()
        order = sorted(range(len(texts)), key=lambda i: len(texts[i]))
        out = np.zeros((len(texts), len(CLASSES)), dtype=np.float32)
        with torch.no_grad():
            for start in range(0, len(order), batch):
                ids = order[start : start + batch]
                logits = model(*encode([texts[i] for i in ids]))
                out[ids] = logits.float().cpu().numpy()
        return out

    texts_train, texts_val = [t for _, t in train], [t for _, t in val]
    steps_per_epoch = (len(train) + args.batch - 1) // args.batch
    total_steps = steps_per_epoch * args.epochs
    no_decay = ("bias", "LayerNorm.weight")
    groups = [
        {"params": [p for n, p in model.named_parameters() if not any(k in n for k in no_decay)], "weight_decay": 0.01},
        {"params": [p for n, p in model.named_parameters() if any(k in n for k in no_decay)], "weight_decay": 0.0},
    ]
    optimizer = torch.optim.AdamW(groups, lr=args.lr)
    warmup = int(0.06 * total_steps)
    scheduler = torch.optim.lr_scheduler.LambdaLR(
        optimizer, lambda step: (step + 1) / max(warmup, 1) if step < warmup else max(0.0, (total_steps - step) / max(total_steps - warmup, 1))
    )
    loss_fn = nn.CrossEntropyLoss(reduction="none", label_smoothing=args.label_smoothing)

    def val_report() -> tuple[float, float]:
        logits = predict_logits(texts_val)
        shifted = logits - logits.max(axis=1, keepdims=True)
        log_probs = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
        loss = float(np.average(-log_probs[np.arange(len(y_val)), y_val], weights=w_val))
        p_block = 1.0 - np.exp(log_probs[:, 0])
        acc = base.per_set_accuracy(val, p_block, 0.5)
        core = [n for n in acc if (n in base.BLOCK_SETS and not n.startswith("synth_") and n not in base.TRAIN_ONLY) or n in base.ALLOW_SETS]
        macro = sum(acc[n] for n in core) / len(core)
        print("   " + "  ".join(f"{n}={acc[n]:.0%}" for n in sorted(acc)), flush=True)
        return loss, macro

    best = (float("inf"), None)
    step = 0
    started = time.time()
    for epoch in range(args.epochs):
        model.train()
        order = np.random.permutation(len(train))
        running = 0.0
        for start in range(0, len(order), args.batch):
            ids = order[start : start + args.batch]
            input_ids, mask = encode([texts_train[i] for i in ids])
            target = torch.tensor(y_train[ids], device=device)
            weight = torch.tensor(w_train[ids], device=device)
            loss = (loss_fn(model(input_ids, mask), target) * weight).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            step += 1
            running += float(loss)
            if step % 200 == 0:
                rate = step * args.batch / (time.time() - started)
                print(f"  epoch {epoch + 1} step {step}/{total_steps}  loss {running / 200:.4f}  {rate:.0f} samples/s", flush=True)
                running = 0.0
        loss, macro = val_report()
        print(f"epoch {epoch + 1}: val weighted loss {loss:.4f}  val macro@0.5 {macro:.1%}", flush=True)
        if loss < best[0]:
            best = (loss, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()})
    assert best[1] is not None
    model.load_state_dict(best[1])
    print(f"best val weighted loss {best[0]:.4f}; exporting ...", flush=True)

    # --- export: fp32 ONNX -> int8 dynamic quantisation -------------------------------------
    args.out.mkdir(parents=True, exist_ok=True)
    model.eval().to("cpu")
    sample = tokenizer([args.prefix + "請問怎麼做蛋糕", args.prefix + "教我做炸彈"], padding=True, return_tensors="pt")
    fp32 = args.out / "model_fp32.onnx"
    torch.onnx.export(
        model, (sample["input_ids"], sample["attention_mask"]), str(fp32),
        input_names=["input_ids", "attention_mask"], output_names=["logits"],
        dynamic_axes={"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}, "logits": {0: "batch"}},
        opset_version=17, dynamo=False,
    )
    from onnxruntime.quantization import QuantType, quantize_dynamic

    int8 = args.out / "model_quantized.onnx"
    quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8)
    tokenizer.backend_tokenizer.save(str(args.out / "tokenizer.json"))
    (args.out / "meta.json").write_text(json.dumps({
        "classes": CLASSES, "max_length": args.max_length, "prefix": args.prefix, "base_model": args.model,
        "epochs": args.epochs, "lr": args.lr, "val_weighted_loss": best[0],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- parity: does the quantised graph agree with the torch model? --------------------------
    from safety_gateway.steps.finetuned import FinetunedClassifier

    runtime = FinetunedClassifier(args.out)
    probe = random.Random(1).sample(range(len(texts_val)), min(400, len(texts_val)))
    texts = [texts_val[i] for i in probe]
    torch_logits = predict_logits_cpu = None
    with torch.no_grad():
        torch_logits = np.concatenate([
            model(*[t.to("cpu") for t in tokenizer([args.prefix + x for x in texts[i : i + 64]], padding=True, truncation=True,
                                                    max_length=args.max_length, return_tensors="pt").values()][:2]).numpy()
            for i in range(0, len(texts), 64)
        ])
    onnx_logits = runtime.logits(texts)
    agree = float((torch_logits.argmax(1) == onnx_logits.argmax(1)).mean())
    margin_gap = float(np.abs(runtime.margin(torch_logits) - runtime.margin(onnx_logits)).mean())
    print(f"int8 vs torch: argmax agreement {agree:.1%}, mean |margin gap| {margin_gap:.3f}")
    started = time.time()
    for text in texts[:50]:
        runtime.logits([text])
    print(f"onnx latency {(time.time() - started) / 50 * 1000:.1f} ms/text (1 thread)")
    fp32.unlink()
    print(f"saved -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
