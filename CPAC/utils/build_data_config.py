# Copyright (C) 2017-2024  C-PAC Developers

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
"""Build a C-PAC data configuration."""

from pathlib import Path
from typing import Any

from CPAC.utils.monitoring.custom_logging import getLogger

logger = getLogger("CPAC.utils.data-config")


def _cannot_write(file_name: Path | str) -> None:
    """Raise an IOError when a file cannot be written to disk."""
    msg = (
        f"\n\nCPAC says: I couldn't save this file to your drive:\n{file_name}\n\nMake"
        " sure you have write access? Then come back. Don't worry.. I'll wait.\n\n"
    )
    raise IOError(msg)


def gather_file_paths(base_directory, verbose=False) -> list[Path | str]:
    """Return a list of file paths from a base directory."""
    # this will go into core tools eventually

    # ideas: return number of paths, optionally instead
    #        or write out, optionally, a text file with all paths, for easy
    #        searching

    # test cases:
    #   - proper data directory
    #   - empty directory

    import os

    path_list = []

    for root, dirs, files in os.walk(base_directory):
        for path in files:
            fullpath = os.path.join(root, path)
            path_list.append(fullpath)

    if verbose:
        logger.info("Number of paths: %s", len(path_list))

    return path_list


def _no_anatomical_found(
    data_dct: dict,
    verbose: bool,
    purpose: str,
    entity: str,
    _id: str,
    file_path: Path | str,
) -> dict:
    """Return the data dictionary and warn no anatomical entries are found."""
    if verbose:
        logger.warning(
            "No anatomical entries found for %s for %s %s:\n%s\n",
            purpose,
            entity,
            _id,
            file_path,
        )
    return data_dct


def pull_s3_sublist(data_folder, creds_path=None, keep_prefix=True) -> list[Path | str]:
    """Return a list of input data file paths that are available from AWS S3."""
    import os

    from indi_aws import fetch_creds

    if creds_path:
        creds_path = os.path.abspath(creds_path)

    s3_path = data_folder.split("s3://")[1]
    bucket_name = s3_path.split("/")[0]
    bucket_prefix = s3_path.split(bucket_name + "/")[1]

    logger.info("Pulling from %s ...", data_folder)

    s3_list = []
    bucket = fetch_creds.return_bucket(creds_path, bucket_name)

    # ensure slash at end of bucket_prefix, so that if the final
    # directory name is a substring in other directory names, these
    # other directories will not be pulled into the file list
    if "/" not in bucket_prefix[-1]:
        bucket_prefix += "/"

    # Build S3-subjects to download
    for bk in bucket.objects.filter(Prefix=bucket_prefix):
        if keep_prefix:
            fullpath = os.path.join("s3://", bucket_name, str(bk.key))
            s3_list.append(fullpath)
        else:
            s3_list.append(str(bk.key).replace(bucket_prefix, ""))

    logger.info("Finished pulling from S3. %s file paths found.", len(s3_list))

    if not s3_list:
        err = (
            "\n\n[!] No input data found matching your data settings in "
            f"the AWS S3 bucket provided:\n{data_folder}\n\n"
        )
        raise FileNotFoundError(err)

    return s3_list


def get_file_list(
    base_directory, creds_path=None, write_txt=None, write_pkl=None, write_info=False
) -> list[Path | str]:
    """Return a list of input and data file paths.

    These paths are either stored locally or on an AWS S3 bucket on the cloud.
    """
    import os

    if "s3://" in base_directory:
        # AWS S3 bucket
        file_list = pull_s3_sublist(base_directory, creds_path)
    else:
        # local
        base_directory = os.path.abspath(base_directory)
        file_list = gather_file_paths(base_directory)

    if len(file_list) == 0:
        warn = (
            "\n\n[!] No files were found in the base directory you "
            f"provided.\n\nDirectory: {base_directory}\n\n"
        )
        raise FileNotFoundError(warn)

    if write_txt:
        if ".txt" not in write_txt:
            write_txt = f"{write_txt}.txt"
        write_txt = os.path.abspath(write_txt)
        with open(write_txt, "wt") as f:
            for path in file_list:
                f.write(f"{path}\n")
        logger.info("\nFilepath list text file written:\n%s", write_txt)

    if write_pkl:
        import pickle

        if ".pkl" not in write_pkl:
            write_pkl = f"{write_pkl}.pkl"
        write_pkl = os.path.abspath(write_pkl)
        with open(write_pkl, "wb") as f:
            pickle.dump(list(file_list), f)
        logger.info("\nFilepath list pickle file written:\n%s", write_pkl)

    if write_info:
        niftis = []
        jsons = []
        scan_jsons = []
        csvs = []
        tsvs = []
        part_tsvs = []
        for path in file_list:
            if ".nii" in path:
                niftis.append(path)
            elif ".json" in path:
                jsons.append(path)
                if "bold.json" in path:
                    scan_jsons.append(path)
            elif ".csv" in path:
                csvs.append(path)
            elif ".tsv" in path:
                tsvs.append(path)
                if "participants.tsv" in path:
                    part_tsvs.append(path)

        logger.info(
            "\nBase directory: %s\nFile paths found: %s\n..NIFTI files: %s\n..JSON files: %s",
            base_directory,
            len(file_list),
            len(niftis),
            len(jsons),
        )

        if jsons:
            logger.info(
                "....%s of which are scan parameter JSON files", len(scan_jsons)
            )
        logger.info("..CSV files: %s\n..TSV files: %s", len(csvs), len(tsvs))
        if tsvs:
            logger.info("....%s of which are participants.tsv files", len(part_tsvs))

    return file_list


def download_single_s3_path(
    s3_path, download_dir=None, creds_path=None, overwrite=False
):
    """Download a single file from an AWS s3 bucket.

    :type s3_path: str
    :param s3_path: An "s3://" pre-pended path to a file stored on an
                    Amazon AWS s3 bucket.
    :type cfg_dict: dictionary
    :param cfg_dict: A dictionary containing the pipeline setup
                     parameters.
    :rtype: str
    :return: The local filepath of the downloaded s3 file.
    """
    # TODO: really for core tools and/or utility

    import os

    from indi_aws import aws_utils, fetch_creds

    if "s3://" in s3_path:
        s3_prefix = s3_path.replace("s3://", "")
    else:
        err = "[!] S3 file paths must be pre-pended with the 's3://' prefix."
        raise SyntaxError(err)

    bucket_name = s3_prefix.split("/")[0]
    data_dir = s3_path.split(bucket_name + "/")[1]

    if not download_dir:
        download_dir = os.getcwd()
        local_dl = os.path.join(download_dir, data_dir)
    else:
        local_dl = os.path.join(download_dir, data_dir.split("/")[-1])

    bucket = fetch_creds.return_bucket(creds_path, bucket_name)

    if os.path.isfile(local_dl):
        if overwrite:
            logger.info("\nS3 bucket file already downloaded! Overwriting..")
            aws_utils.s3_download(bucket, ([data_dir], [local_dl]))
        else:
            logger.info(
                "\nS3 bucket file already downloaded! Skipping download.\nS3 file: %s\nLocal file already exists: %s\n",
                s3_path,
                local_dl,
            )
    else:
        aws_utils.s3_download(bucket, ([data_dir], [local_dl]))

    return local_dl


def generate_group_analysis_files(data_config_outdir, data_config_name):
    """Create the group-level analysis inclusion list."""
    import csv
    import os

    import yaml

    data_config_path = os.path.join(data_config_outdir, data_config_name)

    try:
        subjects_list = yaml.safe_load(open(data_config_path, "r"))
    except (OSError, TypeError) as e:
        msg = (
            "\n\n[!] Data configuration file couldn't be read!\nFile path:"
            f"{data_config_path}\n"
        )
        raise OSError(msg) from e

    subject_scan_set = set()
    subID_set = set()
    session_set = set()
    subject_set = set()
    scan_set = set()
    data_list = []

    try:
        for sub in subjects_list:
            if sub["unique_id"]:
                subject_id = sub["subject_id"] + "_" + sub["unique_id"]
            else:
                subject_id = sub["subject_id"]

            try:
                for scan in sub["func"]:
                    subject_scan_set.add((subject_id, scan))
                    subID_set.add(sub["subject_id"])
                    session_set.add(sub["unique_id"])
                    subject_set.add(subject_id)
                    scan_set.add(scan)
            except KeyError:
                try:
                    for scan in sub["rest"]:
                        subject_scan_set.add((subject_id, scan))
                        subID_set.add(sub["subject_id"])
                        session_set.add(sub["unique_id"])
                        subject_set.add(subject_id)
                        scan_set.add(scan)
                except KeyError:
                    # one of the participants in the subject list has no
                    # functional scans
                    subID_set.add(sub["subject_id"])
                    session_set.add(sub["unique_id"])
                    subject_set.add(subject_id)

    except TypeError:
        logger.error(
            "Subject list could not be populated!\nThis is most likely due to a"
            " mis-formatting in your inclusion and/or exclusion subjects txt file or"
            " your anatomical and/or functional path templates."
        )
        err_str = (
            "Check formatting of your anatomical/functional path templates and"
            " inclusion/exclusion subjects text files"
        )
        raise TypeError(err_str)

    for item in subject_scan_set:
        list1 = []
        list1.append(item[0] + "/" + item[1])
        for val in subject_set:
            if val in item:
                list1.append(1)
            else:
                list1.append(0)

        for val in scan_set:
            if val in item:
                list1.append(1)
            else:
                list1.append(0)

        data_list.append(list1)

    # generate the phenotypic file templates for group analysis
    file_name = os.path.join(
        data_config_outdir, "phenotypic_template_%s.csv" % data_config_name
    )

    try:
        f = open(file_name, "wb")
    except (OSError, TypeError):
        _cannot_write(file_name)

    writer = csv.writer(f)

    writer.writerow(["participant", "EV1", ".."])
    for sub in sorted(subID_set):
        writer.writerow([sub, ""])

    f.close()

    logger.info("Template phenotypic file for group analysis - %s", file_name)

    # generate the group analysis subject lists
    file_name = os.path.join(
        data_config_outdir, "participant_list_group_analysis_%s.txt" % data_config_name
    )

    try:
        with open(file_name, "w") as f:
            for sub in sorted(subID_set):
                f.write(f"{sub}\n")
    except (AttributeError, OSError, TypeError, ValueError):
        _cannot_write(file_name)

    logger.info(
        "Participant list required later for group analysis - %s\n\n", file_name
    )


def extract_scan_params_csv(scan_params_csv: Path | str) -> dict[str, Any]:
    """
    Extract the site-based scan parameters from a csv file.

    Returns a dictionary of their values.

    Parameters
    ----------
    scan_params_csv : string
        filepath to the scan parameters csv file

    Returns
    -------
    site_dict : dictionary
        a dictionary where site names are the keys and the scan
        parameters for that site are the values stored as a dictionary
    """
    # Import packages
    import csv

    # Init variables
    csv_open = open(scan_params_csv, "r")
    site_dict = {}

    # Init csv dictionary reader
    reader = csv.DictReader(csv_open)

    placeholders = ["None", "NONE", "none", "All", "ALL", "all", "", " "]

    keys = {
        "TR (seconds)": "TR",
        "TE (seconds)": "TE",
        "Reference (slice no)": "reference",
        "Acquisition (pattern)": "acquisition",
        "FirstTR (start volume index)": "first_TR",
        "LastTR (final volume index)": "last_TR",
    }

    # Iterate through the csv and pull in parameters
    for dict_row in reader:
        if dict_row["Site"] in placeholders:
            site = "All"
        else:
            site = dict_row["Site"]

        sub = "All"
        if "Participant" in dict_row.keys():
            if dict_row["Participant"] not in placeholders:
                sub = dict_row["Participant"]

        ses = "All"
        if "Session" in dict_row.keys():
            if dict_row["Session"] not in placeholders:
                ses = dict_row["Session"]

        if ses != "All":
            # for session-specific scan parameters
            if site not in site_dict.keys():
                site_dict[site] = {}
            if sub not in site_dict[site]:
                site_dict[site][sub] = {}

            site_dict[site][sub][ses] = {
                keys[key]: val
                for key, val in dict_row.items()
                if key not in ("Site", "Participant", "Session", "Series")
            }

            # Assumes all other fields are formatted properly, but TR might
            # not be
            # site_dict[site][sub][ses]['tr'] = \
            #    site_dict[site][sub][ses].pop('tr (seconds)')

        elif sub != "All":
            # participant-specific scan parameters
            if site not in site_dict.keys():
                site_dict[site] = {}
            if sub not in site_dict[site]:
                site_dict[site][sub] = {}

            site_dict[site][sub][ses] = {
                keys[key]: val
                for key, val in dict_row.items()
                if key not in ("Site", "Participant", "Session", "Series")
            }

            # Assumes all other fields are formatted properly, but TR might
            # not be
            # site_dict[site][sub][ses]['tr'] =
            #    site_dict[site][sub][ses].pop('tr (seconds)')

        else:
            # site-specific scan parameters only
            if site not in site_dict.keys():
                site_dict[site] = {}
            if sub not in site_dict[site]:
                site_dict[site][sub] = {}

            site_dict[site][sub][ses] = {
                keys[key]: val
                for key, val in dict_row.items()
                if key not in ("Site", "Participant", "Session", "Series")
            }

            # Assumes all other fields are formatted properly, but TR might
            # not be
            # site_dict[site][sub][ses]['tr'] = \
            #    site_dict[site][sub][ses].pop('tr (seconds)')

    return site_dict


def format_incl_excl_dct(incl_list, info_type="participants"):
    """Create either an inclusion or exclusion dictionary...

    ...to determine which input files to include or not include in the data
    configuration file.
    """
    incl_dct = {}

    if isinstance(incl_list, str):
        if ".txt" in incl_list:
            with open(incl_list, "r") as f:
                incl_dct[info_type] = [
                    x.rstrip("\n").replace(" ", "") for x in f.readlines() if x != ""
                ]
        elif "," in incl_list:
            incl_dct[info_type] = [x.replace(" ", "") for x in incl_list.split(",")]
        elif incl_list:
            # if there's only one item in the box, most common probably
            if "None" in incl_list or "none" in incl_list:
                return incl_dct
            incl_dct[info_type] = incl_list
    elif isinstance(incl_list, list):
        incl_dct[info_type] = incl_list

    return incl_dct


def get_BIDS_data_dct(
    bids_base_dir,
    file_list=None,
    anat_scan=None,
    aws_creds_path=None,
    freesurfer_dir=None,
    brain_mask_template=None,
    inclusion_dct=None,
    exclusion_dct=None,
    config_dir=None,
):
    """Return a data dictionary...

    ...mapping input file paths to participant,
    session, scan, and site IDs (where applicable) for a BIDS-formatted data
    directory.

    This function prepares a file path template, then uses the
    already-existing custom template function for producing a data dictionary.

    NOTE: For now, accepts the brain_mask_template argument, as the BIDS
          specification is still in flux regarding how to handle anatomical
          derivatives. Thus, we allow users to modify what the expected BIDS
          layout is for their anatomical brain masks.
    """
    import glob
    import os
    import re

    if not config_dir:
        config_dir = os.getcwd()

    anat_sess = os.path.join(
        bids_base_dir,
        "sub-{participant}/ses-{session}/anat/sub-"
        "{participant}_ses-{session}_T1w.nii.gz",
    )
    anat = os.path.join(
        bids_base_dir, "sub-{participant}/anat/sub-{participant}_T1w.nii.gz"
    )

    if anat_scan:
        anat_sess = anat_sess.replace("_T1w", "_*T1w")  # "_*_T1w")
        anat = anat.replace("_T1w", "_*T1w")  # "_*_T1w")

    func_sess = os.path.join(
        bids_base_dir,
        "sub-{participant}"
        "/ses-{session}/func/sub-"
        "{participant}_ses-{session}_task-{scan}_"
        "bold.nii.gz",
    )
    func = os.path.join(
        bids_base_dir,
        "sub-{participant}/func/sub-{participant}_task-{scan}_bold.nii.gz",
    )

    fmap_phase_sess = os.path.join(
        bids_base_dir,
        "sub-{participant}/ses-{session}/fmap/"
        "sub-{participant}_ses-{session}*phase"
        "diff.nii.gz",
    )
    fmap_phase = os.path.join(
        bids_base_dir, "sub-{participant}/fmap/sub-{participant}*phasediff.nii.gz"
    )

    fmap_mag_sess = os.path.join(
        bids_base_dir,
        "sub-{participant}/ses-{session}/fmap/"
        "sub-{participant}_ses-{session}*"
        "magnitud*.nii.gz",
    )

    fmap_mag = os.path.join(
        bids_base_dir, "sub-{participant}/fmap/sub-{participant}*magnitud*.nii.gz"
    )

    fmap_pedir_sess = os.path.join(
        bids_base_dir,
        "sub-{participant}/ses-{session}/fmap/"
        "sub-{participant}_ses-{session}/"
        "*acq-fMR*_epi.nii.gz",
    )

    fmap_pedir = os.path.join(
        bids_base_dir, "sub-{participant}/fmap/sub-{participant}*acq-fMR*_epi.nii.gz"
    )

    sess_glob = os.path.join(bids_base_dir, "sub-*/ses-*/*")

    fmap_phase_scan_glob = os.path.join(
        bids_base_dir, "sub-*fmap/sub-*phasediff.nii.gz"
    )

    fmap_mag_scan_glob = os.path.join(bids_base_dir, "sub-*fmap/sub-*magnitud*.nii.gz")

    os.path.join(bids_base_dir, "sub-*fmap/sub-*_*acq-fMR*_epi.nii.gz")

    part_tsv_glob = os.path.join(bids_base_dir, "*participants.tsv")

    """
    site_jsons_glob = os.path.join(bids_base_dir, "*bold.json")
    sub_jsons_glob = os.path.join(bids_base_dir, "*sub-*/*bold.json")
    ses_jsons_glob = os.path.join(bids_base_dir, "*ses-*bold.json")
    ses_scan_jsons_glob = os.path.join(bids_base_dir, "*ses-*task-*bold.json")
    scan_jsons_glob = os.path.join(bids_base_dir, "*task-*bold.json")
    """

    site_dir_glob = os.path.join(bids_base_dir, "*", "sub-*/*/*.nii*")

    json_globs = [
        os.path.join(bids_base_dir, "sub-*/ses-*/func/*bold.json"),
        os.path.join(bids_base_dir, "sub-*/ses-*/*bold.json"),
        os.path.join(bids_base_dir, "sub-*/func/*bold.json"),
        os.path.join(bids_base_dir, "sub-*/*bold.json"),
        os.path.join(bids_base_dir, "*bold.json"),
    ]

    site_json_globs = [
        os.path.join(bids_base_dir, "*/sub-*/ses-*/func/*bold.json"),
        os.path.join(bids_base_dir, "*/sub-*/ses-*/*bold.json"),
        os.path.join(bids_base_dir, "*/sub-*/func/*bold.json"),
        os.path.join(bids_base_dir, "*/sub-*/*bold.json"),
        os.path.join(bids_base_dir, "*/*bold.json"),
    ]

    ses = False
    site_dir = False
    part_tsv = None

    site_jsons = []
    jsons = []

    if file_list:
        import fnmatch

        for filepath in file_list:
            if (
                fnmatch.fnmatch(filepath, site_dir_glob)
                and "derivatives" not in filepath
            ):
                # check if there is a directory level encoding site ID, even
                # though that is not BIDS format
                site_dir = True
                sess_glob = os.path.join(bids_base_dir, "*", "sub-*/ses-*/*")

            if fnmatch.fnmatch(filepath, sess_glob):
                # check if there is a session level
                ses = True

            if fnmatch.fnmatch(filepath, fmap_phase_scan_glob):
                # check if there is a scan level for the fmap phase files
                fmap_phase_sess = os.path.join(
                    bids_base_dir,
                    "sub-{participant}/ses-{session}/fmap/"
                    "sub-{participant}_ses-{session}*phase"
                    "diff.nii.gz",
                )
                fmap_phase = os.path.join(
                    bids_base_dir,
                    "sub-{participant}/fmap/sub-{participant}*phasediff.nii.gz",
                )

            if fnmatch.fnmatch(filepath, fmap_mag_scan_glob):
                # check if there is a scan level for the fmap magnitude files
                fmap_mag_sess = os.path.join(
                    bids_base_dir,
                    "sub-{participant}/ses-{session}/fmap/"
                    "sub-{participant}_ses-{session}*magnitud*.nii.gz",
                )
                fmap_mag = os.path.join(
                    bids_base_dir,
                    "sub-{participant}/fmap/sub-{participant}*magnitud*.nii.gz",
                )

            """
            if fnmatch.fnmatch(filepath, fmap_pedir_scan_glob):
                # check if there is a scan level for the fmap magnitude files
                fmap_pedir_sess = os.path.join(bids_base_dir,
                                             "sub-{participant}/ses-{session}/fmap/"
                                             "sub-{participant}_ses-{session}_task-{scan}_magnitud*.nii.gz")
                fmap_pedir = os.path.join(bids_base_dir,
                                        "sub-{participant}/fmap/sub-{participant}"
                                        "task-{scan}_magnitud*.nii.gz")
            """

            if fnmatch.fnmatch(filepath, part_tsv_glob):
                # check if there is a participants.tsv file
                part_tsv = filepath

            for glob_str in site_json_globs:
                if fnmatch.fnmatch(filepath, glob_str):
                    site_dir = True
                    site_jsons.append(filepath)

            for glob_str in json_globs:
                if fnmatch.fnmatch(filepath, glob_str):
                    jsons.append(filepath)

    else:
        if len(glob.glob(site_dir_glob)) > 0:
            # check if there is a directory level encoding site ID, even
            # though that is not BIDS format
            site_dir = True
            sess_glob = os.path.join(bids_base_dir, "*", "sub-*/ses-*/*")

        ses = False
        if len(glob.glob(sess_glob)) > 0:
            # check if there is a session level
            ses = True

        # check if there is a participants.tsv file
        part_tsv_finds = glob.glob(part_tsv_glob)
        if part_tsv_finds:
            part_tsv = part_tsv_finds[0]

        for glob_str in site_json_globs:
            site_jsons = site_jsons + glob.glob(glob_str)

        for glob_str in json_globs:
            jsons = jsons + glob.glob(glob_str)

    sites_dct = {}
    sites_subs_dct = {}

    if part_tsv:
        # handle participants.tsv file in BIDS dataset if one is present
        # this would contain site information if the dataset is multi-site
        import csv

        if part_tsv.startswith("s3://"):
            logger.info(
                "\n\nFound a participants.tsv file in your BIDS data set on the S3"
                " bucket. Downloading..\n"
            )
            part_tsv = download_single_s3_path(
                part_tsv, config_dir, aws_creds_path, overwrite=True
            )

        logger.info(
            "Checking participants.tsv file for site information:\n%s", part_tsv
        )

        with open(part_tsv, "r") as f:
            tsv = csv.DictReader(f)
            for row in tsv:
                if "site" in row.keys():
                    site = row["site"]
                    sub = row["participant_id"]
                    if site not in sites_dct.keys():
                        sites_dct[site] = []
                    sites_dct[site].append(sub)

        if sites_dct:
            # check for duplicates
            sites = sites_dct.keys()
            logger.info("%s sites found in the participant.tsv file.", len(sites))
            for site in sites:
                for other_site in sites:
                    if site == other_site:
                        continue
                    dups = set(sites_dct[site]) & set(sites_dct[other_site])
                    if dups:
                        err = (
                            "\n\n[!] There are duplicate participant IDs in different"
                            " sites, as defined by your participants.tsv file!"
                            " Consider prefixing the participant IDs with the site"
                            f" names.\n\nDuplicates:\nSites: {site}, {other_site}\n"
                            f"Duplicate IDs: {dups!s}\n\n"
                        )
                        raise LookupError(err)

                # now invert
                for sub in sites_dct[site]:
                    sites_subs_dct[sub] = site
        else:
            logger.warning("No site information found in the participants.tsv file.")

    if not sites_subs_dct:
        # if there was no participants.tsv file, (or no site column in the
        # participants.tsv file), check for a directory level where multiple
        # sites might be encoded
        if site_dir:
            sub_dir = os.path.join(bids_base_dir, "sub-{participant}")
            new_dir = os.path.join(bids_base_dir, "{site}", "sub-{participant}")
            if ses:
                anat_sess = anat_sess.replace(sub_dir, new_dir)
                func_sess = func_sess.replace(sub_dir, new_dir)
                fmap_phase_sess = fmap_phase_sess.replace(sub_dir, new_dir)
                fmap_mag_sess = fmap_mag_sess.replace(sub_dir, new_dir)
            else:
                anat = anat.replace(sub_dir, new_dir)
                func = func.replace(sub_dir, new_dir)
                fmap_phase = fmap_phase.replace(sub_dir, new_dir)
                fmap_mag = fmap_mag.replace(sub_dir, new_dir)

    scan_params_dct = {}

    if site_jsons:
        # if there is a site-level directory in the BIDS dataset (not BIDS
        # compliant)
        #     example: /bids_dir/site01/sub-01/func/sub-01_task-rest_bold.json
        #     instead of /bids_dir/sub-01/func/sub-01_task-rest_bold.json
        for json_file in site_jsons:
            # get site ID
            site_id = json_file.replace(f"{bids_base_dir}/", "").split("/")[0]
            if "site-" in site_id:
                site_id = site_id.replace("site-", "")

            # get other IDs, from the BIDS format tags, such as "sub-01" or
            # "task-rest". also handle things like "task-rest_run-1"
            ids = re.split("/|_", json_file)

            sub_id = "All"
            ses_id = "All"
            scan_id = "All"
            run_id = None
            acq_id = None

            for _id in ids:
                if "sub-" in _id:
                    sub_id = _id.replace("sub-", "")
                if "ses-" in _id:
                    ses_id = _id.replace("ses-", "")
                if "task-" in _id:
                    scan_id = _id.replace("task-", "")
                if "run-" in _id:
                    run_id = _id.replace("run-", "")
                if "acq-" in _id:
                    acq_id = _id.replace("acq-", "")

            if run_id or acq_id:
                json_filename = os.path.basename(json_file)
                if "task-" in json_filename:
                    # if we have a scan ID already, get the "full" scan ID
                    # including any run- and acq- tags, since the rest of
                    # CPAC encodes all of the task-, acq-, and run- tags
                    # together for each series/scan
                    scan_id = json_filename.split("task-")[1].split("_bold")[0]
                elif "_" in json_filename:
                    # if this is an all-scan JSON file, but specific only to
                    # the run or acquisition: create a tag that reads
                    # {All}_run-1, for example, to be interpreted later when
                    # matching scan params JSONs to each func scan
                    scan_id = "[All]"
                    for additional_id in json_filename.split("_"):
                        if "run-" in additional_id or "acq-" in additional_id:
                            scan_id = f"{scan_id}_{additional_id}"

            if site_id not in scan_params_dct.keys():
                scan_params_dct[site_id] = {}
            if sub_id not in scan_params_dct[site_id]:
                scan_params_dct[site_id][sub_id] = {}
            if ses_id not in scan_params_dct[site_id][sub_id]:
                scan_params_dct[site_id][sub_id][ses_id] = {}

            scan_params_dct[site_id][sub_id][ses_id][scan_id] = json_file

            # scan_id can now be something like {All}_run-2, change other code

    elif jsons:
        for json_file in jsons:
            # get other IDs, from the BIDS format tags, such as "sub-01" or
            # "task-rest". also handle things like "task-rest_run-1"
            ids = re.split("/|_", json_file)

            site_id = "All"
            sub_id = "All"
            ses_id = "All"
            scan_id = "All"
            run_id = None
            acq_id = None

            for _id in ids:
                if "sub-" in _id:
                    sub_id = _id.replace("sub-", "")
                if "ses-" in _id:
                    ses_id = _id.replace("ses-", "")
                if "task-" in _id:
                    scan_id = _id.replace("task-", "")
                if "run-" in _id:
                    run_id = _id.replace("run-", "")
                if "acq-" in _id:
                    acq_id = _id.replace("acq-", "")

            if run_id or acq_id:
                json_filename = os.path.basename(json_file)
                if "task-" in json_filename:
                    # if we have a scan ID already, get the "full" scan ID
                    # including any run- and acq- tags, since the rest of
                    # CPAC encodes all of the task-, acq-, and run- tags
                    # together for each series/scan
                    scan_id = json_filename.split("task-")[1].split("_bold")[0]
                elif "_" in json_filename:
                    # if this is an all-scan JSON file, but specific only to
                    # the run or acquisition: create a tag that reads
                    # {All}_run-1, for example, to be interpreted later when
                    # matching scan params JSONs to each func scan
                    scan_id = "[All]"
                    for additional_id in json_filename.split("_"):
                        if "run-" in additional_id or "acq-" in additional_id:
                            scan_id = f"{scan_id}_{additional_id}"

            if site_id not in scan_params_dct.keys():
                scan_params_dct[site_id] = {}
            if sub_id not in scan_params_dct[site_id]:
                scan_params_dct[site_id][sub_id] = {}
            if ses_id not in scan_params_dct[site_id][sub_id]:
                scan_params_dct[site_id][sub_id][ses_id] = {}

            scan_params_dct[site_id][sub_id][ses_id][scan_id] = json_file

            # scan_id can now be something like {All}_run-2, change other code

    if ses:
        # if there is a session level in the BIDS dataset
        data_dct = get_nonBIDS_data(
            anat_sess,
            func_sess,
            file_list=file_list,
            anat_scan=anat_scan,
            scan_params_dct=scan_params_dct,
            brain_mask_template=brain_mask_template,
            fmap_phase_template=fmap_phase_sess,
            fmap_mag_template=fmap_mag_sess,
            fmap_pedir_template=fmap_pedir_sess,
            freesurfer_dir=freesurfer_dir,
            aws_creds_path=aws_creds_path,
            inclusion_dct=inclusion_dct,
            exclusion_dct=exclusion_dct,
            sites_dct=sites_subs_dct,
        )
    else:
        # no session level
        data_dct = get_nonBIDS_data(
            anat,
            func,
            file_list=file_list,
            anat_scan=anat_scan,
            scan_params_dct=scan_params_dct,
            brain_mask_template=brain_mask_template,
            fmap_phase_template=fmap_phase,
            fmap_mag_template=fmap_mag,
            fmap_pedir_template=fmap_pedir,
            freesurfer_dir=freesurfer_dir,
            aws_creds_path=aws_creds_path,
            inclusion_dct=inclusion_dct,
            exclusion_dct=exclusion_dct,
            sites_dct=sites_subs_dct,
        )

    return data_dct


def find_unique_scan_params(scan_params_dct, site_id, sub_id, ses_id, scan_id):
    """Return the scan parameters information...

    ...stored in the provided scan parameters dictionary for the IDs of a specific
    functional input scan.
    """
    scan_params = None

    if site_id not in scan_params_dct.keys():
        site_id = "All"
        try:
            scan_params_dct[site_id] = {}
        except TypeError:
            logger.info("%s", scan_params_dct)
            scan_params_dct = {site_id: {}}
    if sub_id not in scan_params_dct[site_id]:
        sub_id = "All"
        scan_params_dct[site_id][sub_id] = {}
    if ses_id not in scan_params_dct[site_id][sub_id]:
        ses_id = "All"
        scan_params_dct[site_id][sub_id][ses_id] = {}
    if scan_id not in scan_params_dct[site_id][sub_id][ses_id]:
        for key in scan_params_dct[site_id][sub_id][ses_id]:
            # scan_id (incoming file path) might have run- or acq-, if
            # this is a BIDS dataset, such as "acq-inv1_run-1_BOLD"
            #     however, the scan ID keys here in scan_params_dct might
            #     have something like "run-1_BOLD", meaning this also
            #     applies to the "acq-inv1_run-1_BOLD" scan!
            #
            # "key" will always be the smaller/equal of the scan tags
            if key in scan_id:
                scan_id = key
                break
    else:
        scan_id = "All"

    try:
        scan_params = scan_params_dct[site_id][sub_id][ses_id][scan_id]
    except TypeError as type_error:
        # this ideally should never fire
        err = (
            "\n[!] The scan parameters dictionary supplied to the data configuration"
            " builder is not in the proper format.\n\n The key combination that caused"
            f" this error:\n{site_id}, {sub_id}, {ses_id}, {scan_id}\n\n"
        )
        raise SyntaxError(err) from type_error
    except KeyError:
        pass

    if not scan_params:
        logger.warning(
            "\n[!] No scan parameter information found in your scan parameter"
            " configuration for the functional input file:\nsite: %s, participant: %s,"
            " session: %s, series: %s\n\n",
            site_id,
            sub_id,
            ses_id,
            scan_id,
        )

    return scan_params


def update_data_dct(
    file_path,
    file_template,
    data_dct=None,
    data_type="anat",
    anat_scan=None,
    sites_dct=None,
    scan_params_dct=None,
    inclusion_dct=None,
    exclusion_dct=None,
    aws_creds_path=None,
    verbose=True,
) -> dict[str, Any]:
    """Return a data dictionary with a new file path parsed and added in,...

    ...keyed with its appropriate ID labels.
    """
    import glob
    import os
    from pathlib import Path

    if not data_dct:
        data_dct = {}

    # NIFTIs only
    if ".nii" not in file_path and "freesurfer" not in data_type:
        return data_dct

    if data_type == "anat":
        # pick the right anatomical scan, if "anatomical_scan" has been provided
        if anat_scan:
            file_name = os.path.basename(file_path)
            if anat_scan not in file_name:
                return data_dct
            # if we're dealing with BIDS here
            if "sub-" in file_name and "T1w." in file_name:
                anat_scan_identifier = False
                # BIDS tags are delineated with underscores
                bids_tags = []
                for tag in file_name.split("_"):
                    if anat_scan == tag:
                        # the "anatomical_scan" substring provided is
                        # one of the BIDS tags
                        anat_scan_identifier = True
                    else:
                        if "sub-" not in tag and "ses-" not in tag and "T1w" not in tag:
                            bids_tags.append(tag)
                        if anat_scan in tag:
                            # the "anatomical_scan" substring provided was
                            # found in one of the BIDS tags
                            anat_scan_identifier = True
                if anat_scan_identifier:
                    if len(bids_tags) > 1:
                        # if this fires, then there are other tags as well
                        # in addition to what was defined in the
                        # "anatomical_scan" field in the data settings,
                        #     for example, we might be looking for only
                        #     run-1, but we found acq-inv_run-1 instead
                        return data_dct

            # if we're dealing with a custom data directory format
            else:
                # TODO: more involved processing here? or not necessary?
                pass

    # reduce the template down to only the sub-strings that do not have
    # these tags or IDs

    # Example
    #   file_template =
    #     /path/to/{site}/sub-{participant}/ses-{session}/func/
    #         sub-{participant}_ses-{session}_task-{scan}_bold.nii.gz
    site_parts = file_template.split("{site}")

    # Example, cont.
    # site_parts =
    #   ['/path/to/', '/sub-{participant}/ses-{session}/..']

    partic_parts = []
    for part in site_parts:
        partic_parts = partic_parts + part.split("{participant}")

    # Example, cont.
    # partic_parts =
    #   ['/path/to/', '/sub-', '/ses-{session}/func/sub-', '_ses-{session}..']

    ses_parts = []
    for part in partic_parts:
        ses_parts = ses_parts + part.split("{session}")

    # Example, cont.
    # ses_parts =
    #   ['/path/to/', '/sub-', '/ses-', '/func/sub-', '_ses-',
    #    '_task-{scan}_bold.nii.gz']

    if data_type in ("anat", "brain_mask", "freesurfer_dir"):
        parts = ses_parts
    else:
        # if functional, or field map files
        parts = []
        for part in ses_parts:
            parts = parts + part.split("{scan}")

        # Example, cont.
        #   parts = ['/path/to/', '/sub-', '/ses-', '/func/sub-', '_ses-',
        #            '_task-', '_bold.nii.gz']

    if "*" in file_template:
        wild_parts = []
        for part in parts:
            wild_parts = wild_parts + part.split("*")
        parts = wild_parts

    new_template = file_template
    new_path = file_path

    # go through the non-label/non-ID substrings and parse them out,
    # going from left to right and chopping out both sides of the whole
    # string until only the tag, and the ID, are left
    path_dct = {}
    for idx in range(0, len(parts)):
        part1 = parts[idx]
        try:
            part2 = parts[idx + 1]
        except IndexError:
            break
        label = new_template.split(part1, 1)[1]
        if "freesurfer" not in data_type:
            label = label.split(part2, 1)[0]

        if label in path_dct.keys():
            continue

        if label == "*":
            # if current key is a wildcard
            continue

        try:
            id_value = new_path.split(part1, 1)[1]
            id_value = id_value.split(part2, 1)[0]
        except (IndexError, TypeError):
            logger.error("Path split exception: %s // %s, %s", new_path, part1, part2)

        # example, ideally at this point, something like this:
        #   template = /path/to/sub-{participant}/etc.
        #   filepath = /path/to/sub-200/etc.
        #   label    = {participant}
        #   id_value = '200'

        if label not in path_dct.keys():
            path_dct[label] = id_value
            skip = False
        elif path_dct[label] != id_value:
            logger.warning(
                "\n\n[!] WARNING: While parsing your input data files, a file path"
                " was found with conflicting IDs for the same data level.\n\nFile"
                " path: %s\nLevel: %s\nConflicting IDs: %s, %s\n\nThus, we can't"
                " tell which %s it belongs to, and whether this file should be"
                " included or excluded! Therefore, this file has not been added to"
                " the data configuration.",
                file_path,
                label,
                path_dct[label],
                id_value,
                label.replace("{", "").replace("}", ""),
            )
            skip = True
            break

        new_template = new_template.replace(part1, "", 1)
        new_template = new_template.replace(label, "", 1)

        new_path = new_path.replace(part1, "", 1)
        new_path = new_path.replace(id_value, "", 1)

    if skip:
        return data_dct

    sub_id = path_dct["{participant}"]

    if "{site}" in path_dct.keys():
        site_id = path_dct["{site}"]
    elif sites_dct:
        # mainly if we're pulling site info from a participants.tsv file
        # for a BIDS data set
        try:
            site_id = sites_dct[sub_id]
        except KeyError:
            site_id = "site-1"
    else:
        site_id = "site-1"

    if "{session}" in path_dct.keys():
        ses_id = path_dct["{session}"]
    else:
        ses_id = "ses-1"

    if data_type not in ("anat", "brain_mask"):
        if "{scan}" in path_dct.keys():
            scan_id = path_dct["{scan}"]
        elif data_type == "func":
            scan_id = "func-1"
        else:
            # field map files - keep these open as "None" so that they
            # can be applied to all scans, if there isn't one specified
            scan_id = None

    if inclusion_dct:
        if "sites" in inclusion_dct.keys():
            if site_id not in inclusion_dct["sites"]:
                return data_dct
        if "sessions" in inclusion_dct.keys():
            if ses_id not in inclusion_dct["sessions"]:
                return data_dct
        if "participants" in inclusion_dct.keys():
            if all(
                [
                    sub_id not in inclusion_dct["participants"],
                    f"sub-{sub_id}" not in inclusion_dct["participants"],
                    sub_id.split("sub-")[-1] not in inclusion_dct["participants"],
                ]
            ):
                return data_dct
        if data_type != "anat":
            if "scans" in inclusion_dct.keys():
                if scan_id not in inclusion_dct["scans"]:
                    return data_dct

    if exclusion_dct:
        if "sites" in exclusion_dct.keys():
            if site_id in exclusion_dct["sites"]:
                return data_dct
        if "sessions" in exclusion_dct.keys():
            if ses_id in exclusion_dct["sessions"]:
                return data_dct
        if "participants" in exclusion_dct.keys():
            if any(
                [
                    sub_id in exclusion_dct["participants"],
                    f"sub-{sub_id}" in exclusion_dct["participants"],
                    sub_id.split("sub-")[-1] in exclusion_dct["participants"],
                ]
            ):
                return data_dct
        if data_type != "anat":
            if "scans" in exclusion_dct.keys():
                if scan_id in exclusion_dct["scans"]:
                    return data_dct
    # start the data dictionary updating
    if data_type == "anat":
        if "*" in file_path:
            if "s3://" in file_path:
                err = (
                    "\n\n[!] Cannot use wildcards (*) in AWS S3 bucket "
                    "(s3://) paths!"
                )
                raise Exception(err)
            glob.glob(file_path)

        temp_sub_dct = {
            "subject_id": sub_id,
            "unique_id": ses_id,
            "site": site_id,
            "anat": {"T1w": file_path, "freesurfer_dir": None},
        }
        if aws_creds_path:
            temp_sub_dct.update({"creds_path": str(aws_creds_path)})

        if site_id not in data_dct.keys():
            data_dct[site_id] = {}
        if sub_id not in data_dct[site_id]:
            data_dct[site_id][sub_id] = {}
        if ses_id not in data_dct[site_id][sub_id]:
            data_dct[site_id][sub_id][ses_id] = temp_sub_dct
        else:
            # doubt this ever happens, but just be safe
            logger.warning(
                "\n\n[!] WARNING: Multiple site-participant-session entries found for"
                " anatomical scans in your input data directory.\n\nDuplicate sets:"
                "\n\n%s\n\n%s\n\nOnly adding the first one to the data configuration"
                " file.\n\n",
                data_dct[site_id][sub_id][ses_id],
                temp_sub_dct,
            )

    elif data_type == "freesurfer_dir":
        if site_id not in data_dct.keys():
            return _no_anatomical_found("freesurfer", "site", site_id, file_path)
        if sub_id not in data_dct[site_id]:
            return _no_anatomical_found("freesurfer", "participant", sub_id, file_path)
        if ses_id not in data_dct[site_id][sub_id]:
            return _no_anatomical_found("freesurfer", "session", ses_id, file_path)
        data_dct[site_id][sub_id][ses_id]["anat"]["freesurfer_dir"] = file_path

    elif data_type == "brain_mask":
        if site_id not in data_dct.keys():
            return _no_anatomical_found("brain mask", "site", site_id, file_path)
        if sub_id not in data_dct[site_id]:
            return _no_anatomical_found("brain mask", "participant", sub_id, file_path)
        if ses_id not in data_dct[site_id][sub_id]:
            return _no_anatomical_found("brain mask", "session", ses_id, file_path)

        data_dct[site_id][sub_id][ses_id]["brain_mask"] = file_path

    elif data_type == "func":
        temp_func_dct = {scan_id: {"scan": file_path, "scan_parameters": None}}
        _fp = Path(file_path)

        # scan parameters time
        scan_params = None
        if scan_params_dct:
            scan_params = find_unique_scan_params(
                scan_params_dct, site_id, sub_id, ses_id, scan_id
            )
        else:
            scan_params = str(_fp.absolute()).replace("".join(_fp.suffixes), ".json")

        if scan_params:
            temp_func_dct[scan_id]["scan_parameters"] = scan_params

        if site_id not in data_dct.keys():
            return _no_anatomical_found("functional", "site", site_id, file_path)
        if sub_id not in data_dct[site_id]:
            return _no_anatomical_found("functional", "participant", sub_id, file_path)
        if ses_id not in data_dct[site_id][sub_id]:
            return _no_anatomical_found("functional", "session", ses_id, file_path)

        if "func" not in data_dct[site_id][sub_id][ses_id]:
            data_dct[site_id][sub_id][ses_id]["func"] = temp_func_dct
        else:
            data_dct[site_id][sub_id][ses_id]["func"].update(temp_func_dct)

    else:
        # field map files!
        if "run-" in file_path or "acq-" in file_path:
            # check for run- and acq- tags, for BIDS datasets
            run_id = None
            acq_id = None
            tags = file_path.split("/")[-1].split("_")
            for tag in tags:
                if "run-" in tag:
                    run_id = tag
                if "acq-" in tag:
                    acq_id = tag

            # TODO: re-visit in the future
            # this is a little iffy, because we're checking the contents of
            # the data_dct for already-existing functional entries - this is
            # assuming that all of the functionals have already been populated
            # into the data_dct - this is always the case, but only because of
            # how we use the function in "get_nonBIDS_data" below
            #     but what if we want to use this manually as part of an API?
            try:
                scan_ids = data_dct[site_id][sub_id][ses_id]["func"]
                for func_scan_id in scan_ids:
                    if run_id and acq_id:
                        if run_id and acq_id in func_scan_id:
                            scan_id = func_scan_id
                    elif run_id:
                        if run_id in func_scan_id and "acq-" not in func_scan_id:
                            scan_id = func_scan_id
                    elif acq_id:
                        if acq_id in func_scan_id and "run-" not in func_scan_id:
                            scan_id = func_scan_id
            except KeyError:
                # TODO: error msg
                pass

        temp_fmap_dct = {data_type: file_path}

        if site_id not in data_dct.keys():
            return _no_anatomical_found("field map file", "site", site_id, file_path)
        if sub_id not in data_dct[site_id]:
            return _no_anatomical_found(
                "field map file", "participant", sub_id, file_path
            )
        if ses_id not in data_dct[site_id][sub_id]:
            if verbose:
                for temp_ses in data_dct[site_id][sub_id]:
                    if "anat" in data_dct[site_id][sub_id][temp_ses]:
                        logger.warning(
                            "Field map file found for session %s, but the anatomical"
                            " scan chosen for this participant-session is for session"
                            " %s, so this field map file is being skipped:\n%s\n\n\nIf"
                            " you wish to use the anatomical scan for session %s for"
                            " all participants with this session instead, use the"
                            " 'Which Anatomical Scan?' option in the data"
                            " configuration builder (or populate the 'anatomical_scan'"
                            " field in the data settings file).\n",
                            ses_id,
                            temp_ses,
                            file_path,
                            ses_id,
                        )
                        break
                else:
                    logger.warning(
                        "No anatomical found for field map file for session %s:\n%s\n",
                        ses_id,
                        file_path,
                    )
            return data_dct

        if "fmap" not in data_dct[site_id][sub_id][ses_id]:
            # would this ever fire? the way we're using this function now
            data_dct[site_id][sub_id][ses_id]["fmap"] = {}
        data_dct[site_id][sub_id][ses_id]["fmap"].update(temp_fmap_dct)

    return data_dct


def get_nonBIDS_data(
    anat_template,
    func_template,
    file_list=None,
    anat_scan=None,
    scan_params_dct=None,
    brain_mask_template=None,
    fmap_phase_template=None,
    fmap_mag_template=None,
    fmap_pedir_template=None,
    freesurfer_dir=None,
    aws_creds_path=None,
    inclusion_dct=None,
    exclusion_dct=None,
    sites_dct=None,
):
    """Prepare a data dictionary for the data configuration file...

    ...when given file path templates describing the input data directories.
    """
    import fnmatch
    import glob
    import os

    if not func_template:
        func_template = ""

    # should have the {participant} label at the very least
    if "{participant}" not in anat_template:
        err = (
            "\n[!] The {participant} keyword is missing from your "
            "anatomical path template.\n"
        )
        raise Exception(err)

    if len(func_template) > 0 and "{participant}" not in func_template:
        err = (
            "\n[!] The {participant} keyword is missing from your "
            "functional path template.\n"
        )
        raise Exception(err)

    keywords = ["{site}", "{participant}", "{session}", "{scan}"]

    # make globby templates, to use them to filter down the path_list into
    # only paths that will work with the templates
    anat_glob = anat_template
    func_glob = func_template

    # backwards compatibility
    if "{series}" in anat_glob:
        anat_template = anat_template.replace("{series}", "{scan}")
        anat_glob = anat_glob.replace("{series}", "{scan}")

    if "{series}" in func_glob:
        func_template = func_template.replace("{series}", "{scan}")
        func_glob = func_glob.replace("{series}", "{scan}")

    if "{scan}" in anat_glob:
        err = (
            "\n[!] CPAC does not support multiple anatomical scans. You "
            "are seeing this message because you have a {scan} or "
            "{series} keyword in your anatomical path template.\n\nSee "
            "the help details for the 'Which Anatomical Scan?' "
            "(anatomical_scan) setting for more information.\n\n"
        )
        raise Exception(err)

    if anat_scan:
        if "None" in anat_scan or "none" in anat_scan:
            anat_scan = None

    # replace the keywords with wildcards
    for keyword in keywords:
        if keyword in anat_glob:
            anat_glob = anat_glob.replace(keyword, "*")
        if keyword in func_glob:
            func_glob = func_glob.replace(keyword, "*")

    # presumably, the paths contained in each of these pools should be anat
    # and func files only, respectively, if the templates were set up properly
    anat_pool = []
    func_pool = []

    if file_list:
        # mainly for AWS S3-stored data sets
        for filepath in file_list:
            if fnmatch.fnmatch(filepath, anat_glob):
                anat_pool.append(filepath)
            elif fnmatch.fnmatch(filepath, func_glob):
                func_pool.append(filepath)

    # run it anyway in case we're pulling anat from S3 and func from local or
    # vice versa - and if there is no file_list, this will run normally
    anat_local_pool = glob.glob(anat_glob)
    func_local_pool = glob.glob(func_glob)

    # anat_pool and func_pool are now lists with (presumably) all of the file
    # paths that match the templates entered
    anat_pool = anat_pool + [x for x in anat_local_pool if x not in anat_pool]
    func_pool = func_pool + [x for x in func_local_pool if x not in func_pool]

    if not anat_pool:
        err = (
            "\n\n[!] No anatomical input file paths found given the data "
            "settings provided.\n\nAnatomical file template being used: "
            f"{anat_glob}\n"
        )
        if anat_scan:
            err = f"{err}Anatomical scan identifier provided: {anat_scan}\n\n"
        raise Exception(err)

    # pull out the site/participant/etc. IDs from each path and connect them
    # for the anatomicals
    data_dct = {}
    for anat_path in anat_pool:
        data_dct = update_data_dct(
            anat_path,
            anat_template,
            data_dct,
            "anat",
            anat_scan,
            sites_dct,
            None,
            inclusion_dct,
            exclusion_dct,
            aws_creds_path,
        )

    if not data_dct:
        # this fires if no anatomicals were found
        # collect some possible examples of anat files that got missed
        possible_anats = []
        all_tags = []
        for anat_path in anat_pool:
            if "T1w" in anat_path or "mprage" in anat_path or "anat" in anat_path:
                possible_anats.append(anat_path)
                all_tags += anat_path.replace(".nii", "").replace(".gz", "").split("_")

        from collections import Counter

        count = Counter(all_tags)
        all_tags = [k for k, v in count.items() if v > 1]

        tags = []
        for tag in all_tags:
            if "/" in tag or "ses-" in tag:
                continue
            tags.append(tag)

        err = (
            "\n\n[!] No anatomical input files were found given the "
            "data settings provided.\n\n"
        )
        if possible_anats:
            err = (
                f"{err}There are some file paths found in the directories "
                "described in the data settings that may be anatomicals "
                "that were missed. Here are a few examples:\n"
            )
            for anat in possible_anats[0:5]:
                err = f"{err}{anat}\n"
            err = (
                f"{err}\nAnd here are some of the possible tags that were "
                "found in the anatomical file paths that were grabbed:"
                "\n"
            )
            for tag in tags[0:20]:
                err = f"{err}{tag}\n"
            err = (
                f"{err}\nCPAC only needs one anatomical scan defined for "
                "each participant-session. If there are multiple "
                "anatomical scans per participant-session, you can use "
                "the 'Which Anatomical Scan?' (anatomical_scan) "
                "parameter to choose which anatomical to "
                "select.\n"
            )
            err = (
                f"{err}\nIf you are already using the 'anatomical_scan' "
                "option in the data settings, check the setting to make "
                "sure you are properly selecting which anatomical scan "
                "to use for your analysis.\n\n"
            )
        raise Exception(err)

    # now gather the functionals
    for func_path in func_pool:
        data_dct = update_data_dct(
            func_path,
            func_template,
            data_dct,
            "func",
            None,
            sites_dct,
            scan_params_dct,
            inclusion_dct,
            exclusion_dct,
            aws_creds_path,
        )

    if freesurfer_dir:
        # make globby templates, to use them to filter down the path_list into
        # only paths that will work with the templates

        for keyword in keywords:
            if keyword in freesurfer_dir:
                freesurfer_glob = freesurfer_dir.replace(keyword, "*")

        # presumably, the paths contained in each of these pools should be
        # field map files only, if the templates were set up properly
        freesurfer_pool = []
        if file_list:
            # mainly for AWS S3-stored data sets
            for filepath in file_list:
                if fnmatch.fnmatch(filepath, freesurfer_glob):
                    freesurfer_pool.append(filepath)
        else:
            for fsdir in os.listdir(str(os.path.dirname(freesurfer_glob))):
                freesurfer_pool.append(freesurfer_glob.replace("*", fsdir))

        for freesurfer_path in freesurfer_pool:
            data_dct = update_data_dct(
                freesurfer_path,
                freesurfer_dir,
                data_dct,
                "freesurfer_dir",
                None,
                sites_dct,
                scan_params_dct,
                inclusion_dct,
                exclusion_dct,
                aws_creds_path,
            )
    if brain_mask_template:
        # make globby templates, to use them to filter down the path_list into
        # only paths that will work with the templates
        brain_mask_glob = brain_mask_template

        for keyword in keywords:
            if keyword in brain_mask_glob:
                brain_mask_glob = brain_mask_glob.replace(keyword, "*")

        # presumably, the paths contained in each of these pools should be
        # field map files only, if the templates were set up properly
        if file_list:
            # mainly for AWS S3-stored data sets
            brain_mask_pool = []
            for filepath in file_list:
                if fnmatch.fnmatch(filepath, brain_mask_glob):
                    brain_mask_pool.append(filepath)
        else:
            brain_mask_pool = glob.glob(brain_mask_glob)

        for brain_mask in brain_mask_pool:
            data_dct = update_data_dct(
                brain_mask,
                brain_mask_template,
                data_dct,
                "brain_mask",
                None,
                sites_dct,
                scan_params_dct,
                inclusion_dct,
                exclusion_dct,
                aws_creds_path,
            )

    # do the same for the fieldmap files, if applicable
    if fmap_phase_template and fmap_mag_template:
        # if we're doing the whole field map distortion correction thing

        # make globby templates, to use them to filter down the path_list into
        # only paths that will work with the templates
        fmap_phase_glob = fmap_phase_template
        fmap_mag_glob = fmap_mag_template

        # backwards compatibility
        if "{series}" in fmap_phase_glob:
            fmap_phase_template = fmap_phase_template.replace("{series}", "{scan}")
            fmap_phase_glob = fmap_phase_glob.replace("{series}", "{scan}")
        if "{series}" in fmap_mag_glob:
            fmap_mag_template = fmap_mag_template.replace("{series}", "{scan}")
            fmap_mag_glob = fmap_mag_glob.replace("{series}", "{scan}")

        for keyword in keywords:
            if keyword in fmap_phase_glob:
                fmap_phase_glob = fmap_phase_glob.replace(keyword, "*")
            if keyword in fmap_mag_glob:
                fmap_mag_glob = fmap_mag_glob.replace(keyword, "*")

        # presumably, the paths contained in each of these pools should be
        # field map files only, if the templates were set up properly
        if file_list:
            # mainly for AWS S3-stored data sets
            fmap_phase_pool = []
            fmap_mag_pool = []
            for filepath in file_list:
                if fnmatch.fnmatch(filepath, fmap_phase_glob):
                    fmap_phase_pool.append(filepath)
                elif fnmatch.fnmatch(filepath, fmap_mag_glob):
                    fmap_mag_pool.append(filepath)
        else:
            fmap_phase_pool = glob.glob(fmap_phase_glob)
            fmap_mag_pool = glob.glob(fmap_mag_glob)

        for fmap_phase in fmap_phase_pool:
            data_dct = update_data_dct(
                fmap_phase,
                fmap_phase_template,
                data_dct,
                "diff_phase",
                None,
                sites_dct,
                scan_params_dct,
                inclusion_dct,
                exclusion_dct,
                aws_creds_path,
            )

        for fmap_mag in fmap_mag_pool:
            data_dct = update_data_dct(
                fmap_mag,
                fmap_mag_template,
                data_dct,
                "diff_mag",
                None,
                sites_dct,
                scan_params_dct,
                inclusion_dct,
                exclusion_dct,
                aws_creds_path,
            )

    if fmap_pedir_template:
        # make globby templates, to use them to filter down the path_list into
        # only paths that will work with the templates
        fmap_pedir_glob = fmap_phase_template

        for keyword in keywords:
            if keyword in fmap_pedir_glob:
                fmap_pedir_glob = fmap_pedir_glob.replace(keyword, "*")

        # presumably, the paths contained in each of these pools should be
        # field map files only, if the templates were set up properly
        if file_list:
            # mainly for AWS S3-stored data sets
            fmap_pedir_pool = []
            for filepath in file_list:
                if fnmatch.fnmatch(filepath, fmap_pedir_glob):
                    fmap_pedir_pool.append(filepath)
        else:
            fmap_pedir_pool = glob.glob(fmap_pedir_glob)

        # TODO: must now deal with phase encoding direction!!!!
        # TODO: have to check scan params, first!!!

        for fmap_pedir in fmap_pedir_pool:
            data_dct = update_data_dct(
                fmap_pedir,
                fmap_pedir_template,
                data_dct,
                "fmap_pedir",
                None,
                sites_dct,
                scan_params_dct,
                inclusion_dct,
                exclusion_dct,
                aws_creds_path,
            )

    return data_dct


def util_copy_template(template_type=None):
    """Copy the data settings YAML file template to the current directory."""
    import os
    import shutil

    import pkg_resources as p

    from CPAC.utils.configuration import preconfig_yaml

    template_type = "data_settings" if not template_type else template_type

    settings_template = (
        preconfig_yaml("default")
        if (template_type == "pipeline_config")
        else p.resource_filename(
            "CPAC",
            os.path.join("resources", "configs", f"{template_type}_template.yml"),
        )
    )

    settings_file = os.path.join(os.getcwd(), f"{template_type}.yml")

    try:
        if os.path.exists(settings_file):
            settings_file = os.path.join(os.getcwd(), f"{template_type}_1.yml")
            while os.path.exists(settings_file):
                idx = int(
                    os.path.basename(settings_file).split("_")[2].replace(".yml", "")
                )
                settings_file = os.path.join(
                    os.getcwd(), f"{template_type}_{idx + 1}.yml"
                )
        shutil.copy(settings_template, settings_file)
    except Exception as exception:
        msg = (
            f"\n[!] Could not write the {template_type} file "
            "template to the current directory.\n"
        )
        raise IOError(msg) from exception

    logger.info(
        "\nGenerated a default %s YAML file for editing:\n%s\n\n",
        template_type,
        settings_file,
    )
    if template_type == "data_settings":
        logger.info(
            "This file can be completed and entered into the C-PAC command-line"
            " interface to generate a data configuration file for individual-level"
            " analysis by running 'cpac utils data_config build {data settings file}'."
            "\n"
        )
    elif template_type == "pipeline_config":
        logger.info(
            "This file can be edited and then used in a C-PAC run by running 'cpac run"
            " $BIDS_DIR $OUTPUT_DIR participant --pipeline-file {pipeline config file"
            "}'.\n"
        )


def run(data_settings_yml: str):
    """Generate and write a CPAC data configuration (participant list) YAML file."""
    import os

    import yaml

    import CPAC

    logger.info("\nGenerating data configuration file..")

    settings_dct = yaml.safe_load(open(data_settings_yml, "r"))

    if (
        "awsCredentialsFile" not in settings_dct
        or not settings_dct["awsCredentialsFile"]
    ):
        settings_dct["awsCredentialsFile"] = None
    elif (
        "None" in settings_dct["awsCredentialsFile"]
        or "none" in settings_dct["awsCredentialsFile"]
    ):
        settings_dct["awsCredentialsFile"] = None

    if "anatomical_scan" not in settings_dct or not settings_dct["anatomical_scan"]:
        settings_dct["anatomical_scan"] = None
    elif (
        "None" in settings_dct["anatomical_scan"]
        or "none" in settings_dct["anatomical_scan"]
    ):
        settings_dct["anatomical_scan"] = None

    # inclusion lists
    incl_dct = format_incl_excl_dct(settings_dct.get("siteList", None), "sites")
    incl_dct.update(
        format_incl_excl_dct(settings_dct.get("subjectList", None), "participants")
    )
    incl_dct.update(
        format_incl_excl_dct(settings_dct.get("sessionList", None), "sessions")
    )
    incl_dct.update(format_incl_excl_dct(settings_dct.get("scanList", None), "scans"))

    # exclusion lists
    excl_dct = format_incl_excl_dct(
        settings_dct.get("exclusionSiteList", None), "sites"
    )
    excl_dct.update(
        format_incl_excl_dct(
            settings_dct.get("exclusionSubjectList", None), "participants"
        )
    )
    excl_dct.update(
        format_incl_excl_dct(settings_dct.get("exclusionSessionList", None), "sessions")
    )
    excl_dct.update(
        format_incl_excl_dct(settings_dct.get("exclusionScanList", None), "scans")
    )

    if "bids" in settings_dct["dataFormat"].lower():
        file_list = get_file_list(
            settings_dct["bidsBaseDir"], creds_path=settings_dct["awsCredentialsFile"]
        )

        data_dct = get_BIDS_data_dct(
            settings_dct["bidsBaseDir"],
            file_list=file_list,
            brain_mask_template=settings_dct["brain_mask_template"],
            anat_scan=settings_dct["anatomical_scan"],
            aws_creds_path=settings_dct["awsCredentialsFile"],
            inclusion_dct=incl_dct,
            exclusion_dct=excl_dct,
            config_dir=settings_dct["outputSubjectListLocation"],
        )

    elif "custom" in settings_dct["dataFormat"].lower():
        # keep as None if local data set (not on AWS S3 bucket)
        file_list = None
        base_dir = None

        if "s3://" in settings_dct["anatomicalTemplate"]:
            # hosted on AWS S3 bucket
            if "{site}" in settings_dct["anatomicalTemplate"]:
                base_dir = settings_dct["anatomicalTemplate"].split("{site}")[0]
            elif "{participant}" in settings_dct["anatomicalTemplate"]:
                base_dir = settings_dct["anatomicalTemplate"].split("{participant}")[0]

        elif "s3://" in settings_dct["functionalTemplate"]:
            # hosted on AWS S3 bucket
            if "{site}" in settings_dct["functionalTemplate"]:
                base_dir = settings_dct["functionalTemplate"].split("{site}")[0]
            elif "{participant}" in settings_dct["functionalTemplate"]:
                base_dir = settings_dct["functionalTemplate"].split("{participant}")[0]

        if base_dir:
            file_list = pull_s3_sublist(base_dir, settings_dct["awsCredentialsFile"])

        params_dct = None
        if settings_dct["scanParametersCSV"]:
            if ".csv" in settings_dct["scanParametersCSV"]:
                params_dct = extract_scan_params_csv(settings_dct["scanParametersCSV"])

        data_dct = get_nonBIDS_data(
            settings_dct["anatomicalTemplate"],
            settings_dct["functionalTemplate"],
            file_list=file_list,
            anat_scan=settings_dct["anatomical_scan"],
            scan_params_dct=params_dct,
            brain_mask_template=settings_dct["brain_mask_template"],
            fmap_phase_template=settings_dct["fieldMapPhase"],
            fmap_mag_template=settings_dct["fieldMapMagnitude"],
            freesurfer_dir=settings_dct["freesurfer_dir"],
            aws_creds_path=settings_dct["awsCredentialsFile"],
            inclusion_dct=incl_dct,
            exclusion_dct=excl_dct,
        )

    else:
        err = (
            "\n\n[!] You must select a data format- either 'BIDS' or "
            "'Custom', in the 'dataFormat' field in the data settings "
            "YAML file.\n\n"
        )
        raise Exception(err)

    if len(data_dct) > 0:
        data_config_outfile = os.path.join(
            settings_dct["outputSubjectListLocation"],
            "data_config_{0}.yml".format(settings_dct["subjectListName"]),
        )

        group_list_outfile = os.path.join(
            settings_dct["outputSubjectListLocation"],
            "group_analysis_participants_{0}.txt".format(
                settings_dct["subjectListName"]
            ),
        )

        # put data_dct contents in an ordered list for the YAML dump
        data_list = []
        group_list = []

        included = {"site": [], "sub": []}
        num_sess = num_scan = 0

        for site in sorted(data_dct.keys()):
            for sub in sorted(data_dct[site]):
                for ses in sorted(data_dct[site][sub]):
                    # if there are scans, get some numbers
                    included["site"].append(site)
                    included["sub"].append(sub)
                    num_sess += 1
                    if "func" in data_dct[site][sub][ses]:
                        for scan in data_dct[site][sub][ses]["func"]:
                            num_scan += 1

                    data_list.append(data_dct[site][sub][ses])
                    group_list.append(f"{sub}_{ses}")

        # calculate numbers
        num_sites = len(set(included["site"]))
        num_subs = len(set(included["sub"]))

        with open(data_config_outfile, "wt") as f:
            # Make sure YAML doesn't dump aliases (so it's more human
            # read-able)
            f.write(f"# CPAC Data Configuration File\n# Version {CPAC.__version__}\n")
            f.write(
                "#\n# http://fcp-indi.github.io for more info.\n#\n"
                "# Tip: This file can be edited manually with "
                "a text editor for quick modifications.\n\n"
            )
            noalias_dumper = yaml.dumper.SafeDumper
            noalias_dumper.ignore_aliases = lambda self, data: True
            f.write(
                yaml.dump(data_list, default_flow_style=False, Dumper=noalias_dumper)
            )

        with open(group_list_outfile, "wt") as f:
            # write the inclusion list (mainly the group analysis sublist)
            # text file
            for group_id in sorted(group_list):
                f.write(f"{group_id}\n")

        if os.path.exists(data_config_outfile):
            logger.info(
                "\nCPAC DATA SETTINGS file entered (use this preset file to modify"
                "/regenerate the data configuration file):\n%s\n\nNumber of:"
                "\n...sites: %s\n...participants: %s\n...participant-sessions: %s"
                "\n...functional scans: %s\n\nCPAC DATA CONFIGURATION file created"
                " (use this for individual-level analysis):\n%s\n",
                data_settings_yml,
                num_sites,
                num_subs,
                num_sess,
                num_scan,
                data_config_outfile,
            )

        if os.path.exists(group_list_outfile):
            logger.info(
                "Group-level analysis participant-session list text file created (use"
                " this for group-level analysis):\n%s\n",
                group_list_outfile,
            )

    else:
        err = (
            "\n\n[!] No anatomical input files were found given the data settings"
            " provided.\n\n"
        )
        raise FileNotFoundError(err)
