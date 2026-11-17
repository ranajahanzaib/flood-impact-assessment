from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from ml.evaluation.metrics import compute_segmentation_metrics
from ml.models.base import get_compute_device


class DiceBCELoss(nn.Module):
    def __init__(self, smooth: float = 1e-6):
        super().__init__()
        self.smooth = smooth
        self.bce = nn.BCEWithLogitsLoss()

    def forward(self, logits: torch.Tensor, targets: torch.Tensor) -> torch.Tensor:
        bce_loss = self.bce(logits, targets)
        probs = torch.sigmoid(logits)

        probs_flat = probs.view(-1)
        targets_flat = targets.view(-1)

        intersection = (probs_flat * targets_flat).sum()
        dice_score = (2.0 * intersection + self.smooth) / (probs_flat.sum() + targets_flat.sum() + self.smooth)
        dice_loss = 1.0 - dice_score

        return 0.5 * bce_loss + 0.5 * dice_loss

class FloodDataset(Dataset):
    """
    Synthetic / in-memory or loaded raster tile dataset for flood adapter training.
    """
    def __init__(self, images: np.ndarray, masks: np.ndarray):
        self.images = torch.from_numpy(images.astype(np.float32))
        self.masks = torch.from_numpy(masks.astype(np.float32)).unsqueeze(1)

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        return self.images[idx], self.masks[idx]

class FloodModelTrainer:
    """
    Reproducible training pipeline for Earth-Observation flood segmentation adapters.
    """
    def __init__(
        self,
        model: nn.Module,
        output_dir: Path | None = None,
        lr: float = 1e-4,
        device: torch.device | None = None,
        seed: int = 42
    ):
        self.set_seed(seed)
        self.device = device or get_compute_device()
        self.model = model.to(self.device)
        self.output_dir = Path(output_dir or "data/cache/checkpoints")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.criterion = DiceBCELoss()
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-4)

    @staticmethod
    def set_seed(seed: int = 42):
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    def fit(
        self,
        train_loader: DataLoader,
        val_loader: DataLoader,
        epochs: int = 5,
        early_stopping_patience: int = 3
    ) -> dict[str, Any]:
        best_val_iou = 0.0
        patience_counter = 0
        history = []

        for epoch in range(1, epochs + 1):
            self.model.train()
            train_loss = 0.0

            for images, masks in train_loader:
                images = images.to(self.device)
                masks = masks.to(self.device)

                self.optimizer.zero_grad()
                logits = self.model(images)
                loss = self.criterion(logits, masks)
                loss.backward()
                self.optimizer.step()

                train_loss += loss.item()

            train_loss /= max(len(train_loader), 1)

            # Validation
            val_metrics = self.evaluate(val_loader)
            val_iou = val_metrics["iou"]

            epoch_record = {
                "epoch": epoch,
                "train_loss": round(train_loss, 4),
                **val_metrics
            }
            history.append(epoch_record)

            if val_iou > best_val_iou:
                best_val_iou = val_iou
                patience_counter = 0
                torch.save(self.model.state_dict(), self.output_dir / "best_model.pt")
            else:
                patience_counter += 1
                if patience_counter >= early_stopping_patience:
                    break

        return {"best_val_iou": best_val_iou, "history": history}

    def evaluate(self, val_loader: DataLoader) -> dict[str, float]:
        self.model.eval()
        all_preds = []
        all_targets = []
        all_probs = []

        with torch.no_grad():
            for images, masks in val_loader:
                images = images.to(self.device)
                logits = self.model(images)
                probs = torch.sigmoid(logits).cpu().numpy()
                preds = (probs >= 0.5).astype(bool)

                all_probs.append(probs.squeeze(1))
                all_preds.append(preds.squeeze(1))
                all_targets.append(masks.numpy().squeeze(1))

        if not all_preds:
            return {"iou": 0.0, "dice": 0.0, "precision": 0.0, "recall": 0.0}

        preds_cat = np.concatenate(all_preds, axis=0)
        targets_cat = np.concatenate(all_targets, axis=0)
        probs_cat = np.concatenate(all_probs, axis=0)

        return compute_segmentation_metrics(preds_cat, targets_cat, pred_prob=probs_cat)
