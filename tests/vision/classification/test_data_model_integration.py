# Copyright The PyTorch Lightning team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from flash import Trainer
from flash.vision import ImageClassificationData, ImageClassifier


def _dummy_image_loader(_):
    return torch.rand(3, 224, 224)


def _rand_image():
    return Image.fromarray(np.random.randint(0, 255, (64, 64, 3), dtype="uint8"))


def test_classification(tmpdir):
    tmpdir = Path(tmpdir)

    (tmpdir / "a").mkdir()
    (tmpdir / "b").mkdir()
    _rand_image().save(tmpdir / "a" / "a_1.png")
    _rand_image().save(tmpdir / "a" / "a_2.png")

    _rand_image().save(tmpdir / "b" / "a_1.png")
    _rand_image().save(tmpdir / "b" / "a_2.png")
    data = ImageClassificationData.from_filepaths(
        train_filepaths=[tmpdir / "a", tmpdir / "b"],
        train_labels=[0, 1],
        train_transform={"per_sample_per_batch_transform": lambda x: x},
        num_workers=0,
        batch_size=2,
    )
    model = ImageClassifier(2, backbone="resnet18")
    trainer = Trainer(default_root_dir=tmpdir, fast_dev_run=True)
    trainer.finetune(model, datamodule=data, strategy="freeze")
