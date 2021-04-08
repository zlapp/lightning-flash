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
from typing import Tuple
import pytest

import os
from pathlib import Path

import numpy as np
from PIL import Image

import torch
import kornia as K

from flash.data.data_utils import labels_from_categorical_csv
from flash.vision import ImageClassificationData


def _rand_image(size: Tuple[int, int]=None):
    if size is None:
        _size = np.random.choice([196, 244])
        size = (_size, _size)
    return Image.fromarray(np.random.randint(0, 255, (*size, 3), dtype="uint8"))


def test_from_filepaths_smoke(tmpdir):
    tmpdir = Path(tmpdir)

    img_size: Tuple[int, int] = 12, 33  # height, width
    B = 2  # batch_size

    (tmpdir / "a").mkdir()
    (tmpdir / "b").mkdir()
    _rand_image(img_size).save(tmpdir / "a" / "a_1.png")
    _rand_image(img_size).save(tmpdir / "a" / "a_2.png")

    _rand_image(img_size).save(tmpdir / "b" / "a_1.png")
    _rand_image(img_size).save(tmpdir / "b" / "a_2.png")

    img_data = ImageClassificationData.from_filepaths(
        train_filepaths=[tmpdir / "a", tmpdir / "b"],
        train_transform=None,
        train_labels=[0, 1],
        batch_size=B,
        num_workers=0,
    )
    data = next(iter(img_data.train_dataloader()))
    imgs, labels = data

    # default image size is 196
    out_size: Tuple[int, int] = img_data.image_size
    H, W = out_size

    assert imgs.shape == (B, 3, H, W)
    assert labels.shape == (B, )

    assert img_data.val_dataloader() is None
    assert img_data.test_dataloader() is None


@pytest.mark.parametrize("img_shape", [(1, 3, 24, 33), (2, 3, 12, 21)])
@pytest.mark.parametrize("val_split", [None, 0.3])
def test_from_filepaths_params(tmpdir, img_shape, val_split):
    tmpdir = Path(tmpdir)

    B, C, H, W = img_shape
    img_size: Tuple[int, int] = H, W

    (tmpdir / "c").mkdir()
    (tmpdir / "d").mkdir()
    _rand_image(img_size).save(tmpdir / "c" / "c_1.png")
    _rand_image(img_size).save(tmpdir / "c" / "c_2.png")
    _rand_image(img_size).save(tmpdir / "d" / "d_1.png")
    _rand_image(img_size).save(tmpdir / "d" / "d_2.png")

    (tmpdir / "e").mkdir()
    (tmpdir / "f").mkdir()
    _rand_image(img_size).save(tmpdir / "e" / "e_1.png")
    _rand_image(img_size).save(tmpdir / "e" / "e_2.png")
    _rand_image(img_size).save(tmpdir / "f" / "f_1.png")
    _rand_image(img_size).save(tmpdir / "f" / "f_2.png")

    def preprocess(x):
        out =  K.image_to_tensor(np.array(x))
        return out

    _to_tensor = {
        "pre_tensor_transform": lambda x: preprocess(x),
    }

    img_data = ImageClassificationData.from_filepaths(
        train_filepaths=[tmpdir / "a", tmpdir / "b"],
        train_labels=[0, 1],
        val_filepaths=[tmpdir / "c", tmpdir / "d"],
        val_labels=[0, 1],
        train_transform=_to_tensor,
        val_transform=_to_tensor,
        test_transform=_to_tensor,
        test_filepaths=[tmpdir / "e", tmpdir / "f"],
        test_labels=[0, 1],
        batch_size=B,
        num_workers=0,
        val_split=val_split,
    )
    assert img_data.val_dataloader() is not None
    assert img_data.test_dataloader() is not None

    data = next(iter(img_data.val_dataloader()))
    imgs, labels = data
    assert imgs.shape == (B, 3, H, W)
    assert labels.shape == (B, )

    data = next(iter(img_data.test_dataloader()))
    imgs, labels = data
    assert imgs.shape == (B, 3, H, W)
    assert labels.shape == (B, )


def test_categorical_csv_labels(tmpdir):
    train_dir = Path(tmpdir / "some_dataset")
    train_dir.mkdir()

    (train_dir / "train").mkdir()
    _rand_image().save(train_dir / "train" / "train_1.png")
    _rand_image().save(train_dir / "train" / "train_2.png")

    (train_dir / "valid").mkdir()
    _rand_image().save(train_dir / "valid" / "val_1.png")
    _rand_image().save(train_dir / "valid" / "val_2.png")

    (train_dir / "test").mkdir()
    _rand_image().save(train_dir / "test" / "test_1.png")
    _rand_image().save(train_dir / "test" / "test_2.png")

    train_csv = os.path.join(tmpdir, 'some_dataset', 'train.csv')
    text_file = open(train_csv, 'w')
    text_file.write(
        'my_id,label_a,label_b,label_c\n"train_1.png", 0, 1, 0\n"train_2.png", 0, 0, 1\n"train_2.png", 1, 0, 0\n'
    )
    text_file.close()

    val_csv = os.path.join(tmpdir, 'some_dataset', 'valid.csv')
    text_file = open(val_csv, 'w')
    text_file.write('my_id,label_a,label_b,label_c\n"val_1.png", 0, 1, 0\n"val_2.png", 0, 0, 1\n"val_3.png", 1, 0, 0\n')
    text_file.close()

    test_csv = os.path.join(tmpdir, 'some_dataset', 'test.csv')
    text_file = open(test_csv, 'w')
    text_file.write(
        'my_id,label_a,label_b,label_c\n"test_1.png", 0, 1, 0\n"test_2.png", 0, 0, 1\n"test_3.png", 1, 0, 0\n'
    )
    text_file.close()

    def index_col_collate_fn(x):
        return os.path.splitext(x)[0]

    train_labels = labels_from_categorical_csv(
        train_csv, 'my_id', feature_cols=['label_a', 'label_b', 'label_c'], index_col_collate_fn=index_col_collate_fn
    )
    val_labels = labels_from_categorical_csv(
        val_csv, 'my_id', feature_cols=['label_a', 'label_b', 'label_c'], index_col_collate_fn=index_col_collate_fn
    )
    test_labels = labels_from_categorical_csv(
        test_csv, 'my_id', feature_cols=['label_a', 'label_b', 'label_c'], index_col_collate_fn=index_col_collate_fn
    )
    data = ImageClassificationData.from_filepaths(
        batch_size=2,
        train_transform=None,
        val_transform=None,
        test_transform=None,
        train_filepaths=os.path.join(tmpdir, 'some_dataset', 'train'),
        train_labels=train_labels.values(),
        val_filepaths=os.path.join(tmpdir, 'some_dataset', 'valid'),
        val_labels=val_labels.values(),
        test_filepaths=os.path.join(tmpdir, 'some_dataset', 'test'),
        test_labels=test_labels.values(),
    )

    for (x, y) in data.train_dataloader():
        assert len(x) == 2

    for (x, y) in data.val_dataloader():
        assert len(x) == 2

    for (x, y) in data.test_dataloader():
        assert len(x) == 2


def test_from_folders(tmpdir):
    train_dir = Path(tmpdir / "train")
    train_dir.mkdir()

    (train_dir / "a").mkdir()
    _rand_image().save(train_dir / "a" / "1.png")
    _rand_image().save(train_dir / "a" / "2.png")

    (train_dir / "b").mkdir()
    _rand_image().save(train_dir / "b" / "1.png")
    _rand_image().save(train_dir / "b" / "2.png")

    img_data = ImageClassificationData.from_folders(train_dir, train_transform=None, batch_size=1)
    data = next(iter(img_data.train_dataloader()))
    imgs, labels = data
    assert imgs.shape == (1, 3, 196, 196)
    assert labels.shape == (1, )

    assert img_data.val_dataloader() is None
    assert img_data.test_dataloader() is None

    img_data = ImageClassificationData.from_folders(
        train_dir,
        val_folder=train_dir,
        test_folder=train_dir,
        batch_size=1,
        num_workers=0,
    )

    data = next(iter(img_data.val_dataloader()))
    imgs, labels = data
    assert imgs.shape == (1, 3, 196, 196)
    assert labels.shape == (1, )

    data = next(iter(img_data.test_dataloader()))
    imgs, labels = data
    assert imgs.shape == (1, 3, 196, 196)
    assert labels.shape == (1, )
