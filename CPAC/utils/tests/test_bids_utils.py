# Copyright (C) 2021-2024  C-PAC Developers

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
"""Tests for bids_utils."""

from importlib import resources
import os
from subprocess import run

import pytest
import yaml

from CPAC.utils.bids_utils import (
    _check_value_type,
    bids_gen_cpac_sublist,
    cl_strip_brackets,
    collect_bids_files_configs,
    create_cpac_data_config,
    load_cpac_data_config,
    load_yaml_config,
    sub_list_filter_by_labels,
)
from CPAC.utils.monitoring.custom_logging import getLogger

logger = getLogger("CPAC.utils.tests")


def create_sample_bids_structure(root_dir):
    """Create temporary synthetic BIDS data for testing parsing."""

    def _prefix_entities(paths, path):
        return f'sub-{paths[path]["sub"]}_ses-{paths[path]["ses"]}'

    suffixes = {
        "anat": ["T1w.nii.gz", "acq-VNavNorm_T1w.nii.gz"],
        "fmap": [],
        "func": [
            f"task-{task}_run-{run}_bold.nii.gz"
            for run in ["1", "2"]
            for task in ["rest"]
        ],
    }

    paths = {
        os.path.join(root_dir, subpath): {
            "sub": sub,
            "ses": ses,
            "data_type": data_type,
        }
        for data_type in ["anat", "fmap", "func"]
        for ses in ["1", "2"]
        for sub in ["0001", "0002"]
        for subpath in [f"sub-{sub}/ses-{ses}/{data_type}"]
    }

    for path in paths:
        os.makedirs(path, exist_ok=True)
        for suffix in suffixes[paths[path]["data_type"]]:
            open(
                os.path.join(path, "_".join([_prefix_entities(paths, path), suffix])),
                "w",
            )


def test_bids_validator() -> None:
    """Test subprocess call to `bids-validator`."""
    run(["bids-validator", "--version"], check=True)


@pytest.mark.parametrize("only_one_anat", [True, False])
def test_create_cpac_data_config_only_one_anat(tmp_path, only_one_anat):
    """Test 'only_one_anat' parameter of 'create_cpac_data_config' function."""
    create_sample_bids_structure(tmp_path)
    assert isinstance(
        create_cpac_data_config(str(tmp_path), only_one_anat=only_one_anat)[0]["anat"][
            "T1w"
        ],
        str if only_one_anat else list,
    )


@pytest.mark.skip(reason="needs local files not included in package")
def test_gen_bids_sublist(bids_dir, test_yml, creds_path, dbg=False):
    (img_files, config) = collect_bids_files_configs(bids_dir, creds_path)
    logger.info("Found %d config files for %d image files", len(config), len(img_files))
    sublist = bids_gen_cpac_sublist(bids_dir, img_files, config, creds_path, dbg)

    with open(test_yml, "w") as ofd:
        yaml.dump(sublist, ofd, encoding="utf-8")

    sublist = bids_gen_cpac_sublist(bids_dir, img_files, None, creds_path, dbg)

    test_yml = test_yml.replace(".yml", "_no_param.yml")
    with open(test_yml, "w") as ofd:
        yaml.dump(sublist, ofd, encoding="utf-8")

    assert sublist


def test_load_data_config_with_ints() -> None:
    """Check that C-PAC coerces sub- and ses- ints to strings."""
    data_config_file = resources.files("CPAC").joinpath(
        "utils/tests/configs/github_2144.yml"
    )
    # make sure there are ints in the test data
    assert _check_value_type(load_yaml_config(str(data_config_file), None))
    # make sure there aren't ints when it's loaded through the loader
    assert not _check_value_type(
        load_cpac_data_config(str(data_config_file), None, None)
    )


@pytest.mark.parametrize("t1w_label", ["acq-HCP", "acq-VNavNorm", "T1w", None])
@pytest.mark.parametrize(
    "bold_label", ["task-peer_run-1", "[task-peer_run-1 task-peer_run-2]", "bold", None]
)
@pytest.mark.parametrize("participant_label", ["NDARAA504CRN", "NDARAC462DZH", None])
def test_sub_list_filter_by_labels(t1w_label, bold_label, participant_label):
    """Tests for sub_list_filter_by_labels."""
    if participant_label:
        participant_label = [
            "sub-" + pt if not pt.startswith("sub-") else pt for pt in participant_label
        ]
    sub_list = load_cpac_data_config(
        "/code/CPAC/pipeline/test/issue_1606_data_config.yml",
        participant_label.split(" ") if isinstance(participant_label, str) else None,
        None,
    )
    bold_labels = bold_label.split(" ") if bold_label is not None else None
    sub_list = sub_list_filter_by_labels(
        sub_list, {"T1w": t1w_label, "bold": bold_labels}
    )
    logger.info(sub_list)
    if t1w_label is not None:
        if participant_label == "NDARAA504CRN":
            anat_sub_list = [sub.get("anat") for sub in sub_list]
            assert any("T2w" in filepath for filepath in anat_sub_list)
            if t1w_label != "T1w":
                assert (
                    "s3://fcp-indi/data/Projects/HBN/MRI/Site-CBIC/"
                    f"sub-NDARAA504CRN/anat/sub-NDARAA504CRN_{t1w_label}_"
                    "T1w.nii.gz" in anat_sub_list
                )
            else:
                assert any("T1w" in filepath for filepath in anat_sub_list)
        else:
            assert 1 <= len(sub_list) <= 2
    else:
        assert (
            "s3://fcp-indi/data/Projects/HBN/MRI/Site-CBIC/"
            "sub-NDARAA504CRN/anat/sub-NDARAA504CRN_acq-VNavNorm_"
            "T1w.nii.gz" not in [sub.get("anat") for sub in sub_list]
        )
    if bold_label is not None:
        if participant_label == "NDARAC462DZH":
            # all functional scans in data config
            func_scans = [
                scan
                for scan in [
                    sub.get("func").get(task, {}).get("scan")
                    for task in [
                        task
                        for scan in [sub.get("func").keys() for sub in sub_list]
                        for task in scan
                    ]
                    for sub in sub_list
                ]
                if scan
            ]
            if bold_label == "bold":
                assert any("bold" in filepath for filepath in func_scans)
            else:
                bold_labels = cl_strip_brackets(bold_labels)
                for label in bold_labels:
                    assert any(label in func for func in func_scans)
        elif t1w_label is not None:
            assert 1 <= len(sub_list) <= 2
        else:
            assert all(
                len(sub.get("func")) in [0, len(bold_labels)] for sub in sub_list
            )
    else:
        assert all(len(sub.get("func")) in [0, 5] for sub in sub_list)
