# Copyright (C) 2019-2023  C-PAC Developers

# This file is part of C-PAC.

# C-PAC is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.

# C-PAC is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public
# License for more details.

# You should have received a copy of the GNU Lesser General Public
# License along with C-PAC. If not, see <https://www.gnu.org/licenses/>.
from ._torch import torch  # this import has to be first to install torch
from .dataset import BlockDataset, VolumeDataset
from .function import (
    estimate_dice,
    extract_large_comp,
    MyParser,
    predict_volumes,
    write_nifti,
)
from .model import (
    Conv2dBlock,
    Conv3dBlock,
    MultiSliceBcUNet,
    MultiSliceModel,
    MultiSliceSsUNet,
    UNet2d,
    UNet3d,
    UpConv2dBlock,
    UpConv3dBlock,
    weigths_init,
)

__all__ = [
    "write_nifti",
    "estimate_dice",
    "extract_large_comp",
    "predict_volumes",
    "MyParser",
    "weigths_init",
    "Conv3dBlock",
    "UpConv3dBlock",
    "Conv2dBlock",
    "UpConv2dBlock",
    "UNet3d",
    "UNet2d",
    "MultiSliceBcUNet",
    "MultiSliceSsUNet",
    "MultiSliceModel",
    "VolumeDataset",
    "BlockDataset",
    "torch",
]
