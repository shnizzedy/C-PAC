# Copyright (C) 2012-2024  C-PAC Developers

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
"""CWAS module for CPAC."""

import os

import numpy as np
from numpy import inf
import pandas as pd
import nibabel as nib
from scipy.stats import t

from CPAC.cwas.mdmr import mdmr
from CPAC.pipeline.cpac_ga_model_generator import (
    create_merge_mask,
    create_merged_copefile,
)
from CPAC.utils import correlation


def joint_mask(subjects, mask_file=None):
    """Create a joint mask.

    A joint mask is an intersection common to all the subjects in a provided list
    and a provided mask.

    Parameters
    ----------
    subjects : dict of strings
        A length `N` list of file paths of the nifti files of subjects
    mask_file : string
        Path to a mask file in nifti format

    Returns
    -------
    joint_mask : string
        Path to joint mask file in nifti format

    """
    if not mask_file:
        files = list(subjects.values())
        cope_file = os.path.join(os.getcwd(), "joint_cope.nii.gz")
        mask_file = os.path.join(os.getcwd(), "joint_mask.nii.gz")
        create_merged_copefile(files, cope_file)
        create_merge_mask(cope_file, mask_file)
    return mask_file


def calc_mdmrs(D, regressor, cols, permutations):
    """Calculate pseudo-F values and significance probabilities."""
    cols = np.array(cols, dtype=np.int32)
    F_set, p_set = mdmr(D, regressor, cols, permutations)
    return F_set, p_set


def calc_subdists(subjects_data, voxel_range):
    """Calculate the subdistributions of the subjects data."""
    subjects, voxels, _ = subjects_data.shape
    D = np.zeros((len(voxel_range), subjects, subjects))
    for i, v in enumerate(voxel_range):
        profiles = np.zeros((subjects, voxels))
        for si in range(subjects):
            profiles[si] = correlation(subjects_data[si, v], subjects_data[si])
        profiles = np.clip(np.nan_to_num(profiles), -0.9999, 0.9999)
        profiles = np.arctanh(np.delete(profiles, v, 1))
        D[i] = correlation(profiles, profiles)

    return np.sqrt(2.0 * (1.0 - D))


def calc_cwas(
    subjects_data, regressor, regressor_selected_cols, permutations, voxel_range
):
    """Calculate CWAS pseudo-F values and significance probabilities."""
    D = calc_subdists(subjects_data, voxel_range)
    F_set, p_set = calc_mdmrs(D, regressor, regressor_selected_cols, permutations)
    return F_set, p_set


def pval_to_zval(p_set, permu):
    """Convert p-values to z-values."""
    inv_pval = 1 - p_set
    zvals = t.ppf(inv_pval, (len(p_set) - 1))
    zvals[zvals == -inf] = permu / (permu + 1)
    zvals[zvals == inf] = permu / (permu + 1)
    return zvals


def nifti_cwas(
    subjects,
    mask_file,
    regressor_file,
    participant_column,
    columns_string,
    permutations,
    voxel_range,
):
    """Perform CWAS for a group of subjects.

    Parameters
    ----------
    subjects : dict of strings:strings
        A length `N` dict of id and file paths of the nifti files of subjects
    mask_file : string
        Path to a mask file in nifti format
    regressor_file : string
        file path to regressor CSV or TSV file (phenotypic info)
    columns_string : string
        comma-separated string of regressor labels
    permutations : integer
        Number of pseudo f values to sample using a random permutation test
    voxel_range : ndarray
        Indexes from range of voxels (inside the mask) to perform cwas on.
        Index ordering is based on the np.where(mask) command

    Returns
    -------
    F_file : string
        .npy file of pseudo-F statistic calculated for every voxel
    p_file : string
        .npy file of significance probabilities of pseudo-F values
    voxel_range : tuple
        Passed on by the voxel_range provided in parameters, used to make parallelization
        easier

    """
    try:
        regressor_data = pd.read_table(
            regressor_file, sep=None, engine="python", dtype={participant_column: str}
        )
    except (KeyError, OSError, pd.errors.ParserError, ValueError):
        regressor_data = pd.read_table(regressor_file, sep=None, engine="python")
        regressor_data = regressor_data.astype({participant_column: str})

    # drop duplicates
    regressor_data = regressor_data.drop_duplicates()

    regressor_cols = list(regressor_data.columns)
    if participant_column not in regressor_cols:
        msg = "Participant column was not found in regressor file."
        raise ValueError(msg)

    if participant_column in columns_string:
        msg = "Participant column can not be a regressor."
        raise ValueError(msg)

    subject_ids = list(subjects.keys())
    subject_files = list(subjects.values())

    # check for inconsistency with leading zeroes
    # (sometimes, the sub_ids from individual will be something like
    #  '0002601' and the phenotype will have '2601')
    for index, row in regressor_data.iterrows():
        pheno_sub_id = str(row[participant_column])
        for sub_id in subject_ids:
            if str(sub_id).lstrip("0") == str(pheno_sub_id):
                regressor_data.at[index, participant_column] = str(sub_id)

    regressor_data.index = regressor_data[participant_column]

    # Keep only data from specific subjects
    ordered_regressor_data = regressor_data.loc[subject_ids]

    columns = columns_string.split(",")
    regressor_selected_cols = [i for i, c in enumerate(regressor_cols) if c in columns]

    if len(regressor_selected_cols) == 0:
        regressor_selected_cols = [i for i, c in enumerate(regressor_cols)]
    regressor_selected_cols = np.array(regressor_selected_cols)
    # Remove participant id column from the dataframe and convert it to a numpy matrix
    regressor = (
        ordered_regressor_data.drop(columns=[participant_column])
        .reset_index(drop=True)
        .values.astype(np.float64)
    )
    if len(regressor.shape) == 1:
        regressor = regressor[:, np.newaxis]
    elif len(regressor.shape) != 2:  # noqa: PLR2004
        raise ValueError("Bad regressor shape: %s" % str(regressor.shape))
    if len(subject_files) != regressor.shape[0]:
        msg = "Number of subjects does not match regressor size"
        raise ValueError(msg)
    mask = nib.load(mask_file).get_fdata().astype("bool")
    mask_indices = np.where(mask)
    subjects_data = np.array(
        [
            nib.load(subject_file).get_fdata().astype("float64")[mask_indices]
            for subject_file in subject_files
        ]
    )

    F_set, p_set = calc_cwas(
        subjects_data, regressor, regressor_selected_cols, permutations, voxel_range
    )
    cwd = os.getcwd()
    F_file = os.path.join(cwd, "pseudo_F.npy")
    p_file = os.path.join(cwd, "significance_p.npy")

    np.save(F_file, F_set)
    np.save(p_file, p_set)

    return F_file, p_file, voxel_range


def create_cwas_batches(mask_file, batches):
    """Create batches of voxels to process in parallel."""
    mask = nib.load(mask_file).get_fdata().astype("bool")
    voxels = mask.sum(dtype=int)
    return np.array_split(np.arange(voxels), batches)


def volumize(mask_image, data):
    """Create a volume from a mask and data."""
    mask_data = mask_image.get_fdata().astype("bool")
    volume = np.zeros_like(mask_data, dtype=data.dtype)
    volume[mask_data] = data
    return nib.Nifti1Image(volume, header=mask_image.header, affine=mask_image.affine)


def merge_cwas_batches(cwas_batches, mask_file, z_score, permutations):
    """Merge CWAS batches into a single volume."""
    _, _, voxel_range = zip(*cwas_batches)
    voxels = np.array(np.concatenate(voxel_range))

    mask_image = nib.load(mask_file)

    F_set = np.zeros_like(voxels, dtype=np.float64)
    p_set = np.zeros_like(voxels, dtype=np.float64)
    for F_file, p_file, voxel_range in cwas_batches:
        F_set[voxel_range] = np.load(F_file)
        p_set[voxel_range] = np.load(p_file)

    log_p_set = -np.log10(p_set)
    one_p_set = 1 - p_set

    F_vol = volumize(mask_image, F_set)
    p_vol = volumize(mask_image, p_set)
    log_p_vol = volumize(mask_image, log_p_set)
    one_p_vol = volumize(mask_image, one_p_set)

    cwd = os.getcwd()
    F_file = os.path.join(cwd, "pseudo_F_volume.nii.gz")
    p_file = os.path.join(cwd, "p_significance_volume.nii.gz")
    log_p_file = os.path.join(cwd, "neglog_p_significance_volume.nii.gz")
    one_p_file = os.path.join(cwd, "one_minus_p_values.nii.gz")

    F_vol.to_filename(F_file)
    p_vol.to_filename(p_file)
    log_p_vol.to_filename(log_p_file)
    one_p_vol.to_filename(one_p_file)

    if 1 in z_score:
        zvals = pval_to_zval(p_set, permutations)
        z_file = zstat_image(zvals, mask_file)
    else:
        z_file = None

    return F_file, p_file, log_p_file, one_p_file, z_file


def zstat_image(zvals, mask_file):
    """Create a zstat image from zvals and mask_file."""
    mask_image = nib.load(mask_file)

    z_vol = volumize(mask_image, zvals)

    cwd = os.getcwd()
    z_file = os.path.join(cwd, "zstat.nii.gz")

    z_vol.to_filename(z_file)
    return z_file
