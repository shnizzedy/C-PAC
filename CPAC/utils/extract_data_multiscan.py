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
import glob
import os
import string

import yaml

from CPAC.utils.monitoring import UTLOGGER


def extract_data(c, param_map):
    """
    Method to generate a CPAC input subject list
    python file. The method extracts anatomical
    functional data and scan parameters for each
    site( if multiple site) and for each scan
    and put it into a data structure read by python.

    Note:
    -----
    Use this tool only if the scan parameters are different
    for each scan as shown in the example below.

    Example:
    --------
    subjects_list = [
        {
            'subject_id': '0021001',
            'unique_id': 'session2',
            'anat': '/home/data/multiband_data/NKITRT/0021001/anat/mprage.nii.gz',
            'rest':{
              'RfMRI_mx_1400_rest': '/home/data/multiband_data/NKITRT/0021001/session2/RfMRI_mx_1400/rest.nii.gz',
              'RfMRI_mx_645_rest': '/home/data/multiband_data/NKITRT/0021001/session2/RfMRI_mx_645/rest.nii.gz',
              'RfMRI_std_2500_rest': '/home/data/multiband_data/NKITRT/0021001/session2/RfMRI_std_2500/rest.nii.gz',
              },
            'scan_parameters':{
                'TR':{
                    'RfMRI_mx_1400_rest': '1.4',
                    'RfMRI_mx_645_rest': '1.4',
                    'RfMRI_std_2500_rest': '2.5',
                    },
                'Acquisition':{
                    'RfMRI_mx_1400_rest': '/home/data/1400.txt',
                    'RfMRI_mx_645_rest': '/home/data/645.txt',
                    'RfMRI_std_2500_rest': '/home/data/2500.txt',
                    },
                'Reference':{
                    'RfMRI_mx_1400_rest': '32',
                    'RfMRI_mx_645_rest': '20',
                    'RfMRI_std_2500_rest': '19',
                    },
                'FirstTR':{
                    'RfMRI_mx_1400_rest': '7',
                    'RfMRI_mx_645_rest': '15',
                    'RfMRI_std_2500_rest': '4',
                    },
                'LastTR':{
                    'RfMRI_mx_1400_rest': '440',
                    'RfMRI_mx_645_rest': '898',
                    'RfMRI_std_2500_rest': 'None',
                    },
                }
        },

    ]
    """

    # method to read each line of the file into list
    # returns list
    def get_list(arg):
        if isinstance(arg, list):
            ret_list = arg
        else:
            ret_list = [fline.rstrip("\r\n") for fline in open(arg, "r").readlines()]

        return ret_list

    exclusion_list = []
    if c.exclusionSubjectList is not None:
        exclusion_list = get_list(c.exclusionSubjectList)

    subject_list = []
    if c.subjectList is not None:
        subject_list = get_list(c.subjectList)

    # check if Template is correct
    def checkTemplate(template):
        if template.count("%s") != 2:
            msg = (
                "Please provide '%s' in the template"
                "where your site and subjects are present"
                "Please see examples"
            )
            raise Exception(msg)

        filename, ext = os.path.splitext(os.path.basename(template))
        ext = os.path.splitext(filename)[1] + ext

        if ext not in [".nii", ".nii.gz"]:
            msg = "Invalid file name"
            raise Exception(msg, os.path.basename(template))

    def get_site_list(path):
        base = path.split("%s")[0]
        return os.listdir(base)

    def check_length(scan_name, file_name):
        if len(file_name) > 30:
            msg = (
                "filename- %s is too long."
                "It should not be more than 30 characters." % (file_name)
            )
            raise Exception(msg)

        if (
            len(scan_name) - len(os.path.splitext(os.path.splitext(file_name)[0])[0])
            >= 20
        ):
            msg = (
                "scan name %s is too long."
                "It should not be more than 20 characters"
                % (
                    scan_name.replace(
                        "_" + os.path.splitext(os.path.splitext(file_name)[0])[0], ""
                    )
                )
            )
            raise Exception(msg)

    def create_site_subject_mapping(base, relative):
        # mapping between site and subject
        site_subject_map = {}
        base_path_list = []

        if c.siteList is not None:
            site_list = get_list(c.siteList)
        else:
            site_list = get_site_list(base)

        for site in site_list:
            paths = glob.glob(string.replace(base, "%s", site))
            base_path_list.extend(paths)
            for path in paths:
                for sub in os.listdir(path):
                    # check if subject is present in subject_list
                    if subject_list:
                        if sub in subject_list and sub not in exclusion_list:
                            site_subject_map[sub] = site
                    elif sub not in exclusion_list:
                        if sub not in ".DS_Store":
                            site_subject_map[sub] = site

        return base_path_list, site_subject_map

    # method to split the input template path
    # into base, path before subject directory
    # and relative, path after subject directory
    def getPath(template):
        checkTemplate(template)
        base, relative = template.rsplit("%s", 1)
        base, subject_map = create_site_subject_mapping(base, relative)
        base.sort()
        relative = relative.lstrip("/")
        return base, relative, subject_map

    # get anatomical base path and anatomical relative path
    anat_base, anat_relative = getPath(c.anatomicalTemplate)[:2]

    # get functional base path, functional relative path and site-subject map
    func_base, func_relative, subject_map = getPath(c.functionalTemplate)

    if not anat_base:
        msg = (
            f"No such file or directory {anat_base}"
            "\nAnatomical Data template incorrect"
        )
        raise FileNotFoundError(msg)

    if not func_base:
        msg = (
            f"No such file or directory {func_base}"
            "Functional Data template incorrect"
        )
        raise FileNotFoundError(msg)

    if len(anat_base) != len(func_base):
        msg = (
            f"Some sites are missing, Please check your template {anat_base} !="
            f" {func_base}\nBase length Unequal. Some sites are missing. extract_data"
            " doesn't script support this. Please provide your own subjects_list file"
        )
        raise FileNotFoundError(msg)

    # calculate the length of relative paths(path after subject directory)
    func_relative_len = len(func_relative.split("/"))
    anat_relative_len = len(anat_relative.split("/"))

    def check_for_sessions(relative_path, path_length):
        """Method to check if there are sessions present."""
        # default
        session_present = False
        session_path = "session_1"

        # session present if path_length is equal to 3
        if path_length == 3:
            relative_path_list = relative_path.split("/")
            session_path = relative_path_list[0]
            relative_path = string.join(relative_path_list[1:], "/")
            session_present = True
        elif path_length > 3:
            msg = (
                "extract_data script currently doesn't support"
                "this directory structure.Please provide the"
                "subjects_list file to run CPAC."
                "For more information refer to manual"
            )
            raise Exception(msg)

        return session_present, session_path, relative_path

    #    if func_relative_len!= anat_relative_len:
    #        raise Exception(" extract_data script currently doesn't"\
    #                          "support different relative paths for"\
    #                          "Anatomical and functional files")

    func_session_present, func_session_path, func_relative = check_for_sessions(
        func_relative, func_relative_len
    )

    anat_session_present, anat_session_path, anat_relative = check_for_sessions(
        anat_relative, anat_relative_len
    )

    f = open(os.path.join(c.outputSubjectListLocation, "CPAC_subject_list.yml"), "wb")

    def fetch_path(i, anat_sub, func_sub, session_id):
        """
        Method to extract anatomical and functional
        path for a session and print to file.

        Parameters
        ----------
        i : int
            index of site
        anat_sub : string
            string containing subject/ concatenated
            subject-session path for anatomical file
        func_sub : string
            string containing subject/ concatenated
            subject-session path for functional file
        session_id : string
            session

        Raises
        ------
        Exception
        """
        try:

            def print_begin_of_file(sub, session_id):
                print("-", file=f)
                print("    subject_id: '" + sub + "'", file=f)
                print("    unique_id: '" + session_id + "'", file=f)

            def print_end_of_file(sub, scan_list):
                if param_map is not None:

                    def print_scan_param(index):
                        try:
                            for scan in scan_list:
                                print(
                                    "            "
                                    + scan[1]
                                    + ": '"
                                    + param_map.get((subject_map.get(sub), scan[0]))[
                                        index
                                    ]
                                    + "'",
                                    file=f,
                                )

                        except:
                            raise Exception(
                                " No Parameter values for the %s site and %s scan is defined in the scan"
                                " parameters csv file" % (subject_map.get(sub), scan[0])
                            )

                    UTLOGGER.info("site for sub %s -> %s", sub, subject_map.get(sub))
                    print("    scan_parameters: ", file=f)
                    print("        tr:", file=f)
                    print_scan_param(4)
                    print("        acquisition:", file=f)
                    print_scan_param(0)
                    print("        reference:", file=f)
                    print_scan_param(3)
                    print("        first_tr:", file=f)
                    print_scan_param(1)
                    print("        last_tr:", file=f)
                    print_scan_param(2)

            # get anatomical file
            anat_base_path = os.path.join(anat_base[i], anat_sub)
            func_base_path = os.path.join(func_base[i], func_sub)

            anat = None
            func = None

            anat = glob.glob(os.path.join(anat_base_path, anat_relative))
            func = glob.glob(os.path.join(func_base_path, func_relative))
            scan_list = []
            if anat and func:
                print_begin_of_file(anat_sub.split("/")[0], session_id)
                print("    anat: '" + anat[0] + "'", file=f)
                print("    rest: ", file=f)

                # iterate for each rest session
                for iter in func:
                    # get scan_id
                    iterable = os.path.splitext(
                        os.path.splitext(iter.replace(func_base_path, "").lstrip("/"))[
                            0
                        ]
                    )[0]
                    scan_name = iterable.replace("/", "_")
                    scan_list.append((os.path.dirname(iterable), scan_name))
                    check_length(scan_name, os.path.basename(iter))
                    print("      " + scan_name + ": '" + iter + "'", file=f)
                print_end_of_file(anat_sub.split("/")[0], scan_list)

        except Exception:
            raise

    def walk(index, sub):
        """
        Method which walks across each subject
        path in the data site path.

        Parameters
        ----------
        index : int
            index of site
        sub : string
            subject_id

        Raises
        ------
        Exception
        """
        try:
            if func_session_present:
                # if there are sessions
                if "*" in func_session_path:
                    session_list = glob.glob(
                        os.path.join(
                            func_base[index], os.path.join(sub, func_session_path)
                        )
                    )
                else:
                    session_list = [func_session_path]

                for session in session_list:
                    session_id = os.path.basename(session)
                    if anat_session_present:
                        if func_session_path == anat_session_path:
                            fetch_path(
                                index,
                                os.path.join(sub, session_id),
                                os.path.join(sub, session_id),
                                session_id,
                            )
                        else:
                            fetch_path(
                                index,
                                os.path.join(sub, anat_session_path),
                                os.path.join(sub, session_id),
                                session_id,
                            )
                    else:
                        fetch_path(
                            index, sub, os.path.join(sub, session_id), session_id
                        )
            else:
                UTLOGGER.info("No sessions")
                session_id = ""
                fetch_path(index, sub, sub, session_id)

        except Exception as e:
            msg = "Please make sessions are consistent across all subjects"
            raise ValueError(msg) from e

    try:
        for i in range(len(anat_base)):
            for sub in os.listdir(anat_base[i]):
                # check if subject is present in subject_list
                if subject_list:
                    if sub in subject_list and sub not in exclusion_list:
                        UTLOGGER.info("extracting data for subject: %s", sub)
                        walk(i, sub)
                # check that subject is not in exclusion list
                elif sub not in exclusion_list and sub not in ".DS_Store":
                    UTLOGGER.info("extracting data for subject: %s", sub)
                    walk(i, sub)

        name = os.path.join(c.outputSubjectListLocation, "CPAC_subject_list.yml")
        UTLOGGER.info("Extraction Complete...Input Subjects_list for CPAC - %s", name)
    except Exception:
        raise
    finally:
        f.close()


def generate_suplimentary_files(output_path):
    """
    Method to generate phenotypic template file
    and subject list for group analysis.
    """
    import csv

    subjects_list = yaml.safe_load(
        open(os.path.join(output_path, "CPAC_subject_list.yml"), "r")
    )

    subject_scan_set = set()
    subject_set = set()
    scan_set = set()
    data_list = []

    for sub in subjects_list:
        if sub["unique_id"]:
            subject_id = sub["subject_id"] + "_" + sub["unique_id"]
        else:
            subject_id = sub["subject_id"]

        for scan in list(sub["rest"]):
            subject_scan_set.add((subject_id, scan))
            subject_set.add(subject_id)
            scan_set.add(scan)

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

    # prepare data for phenotypic file
    if len(scan_set) > 1:
        list1 = ["subject_id/Scan"]
        list1.extend(list(subject_set))
        list1.extend(list(scan_set))

    file_name = os.path.join(output_path, "phenotypic_template.csv")
    f = open(file_name, "wb")
    writer = csv.writer(f)

    if len(scan_set) > 1:
        writer.writerow(list1)
        writer.writerows(data_list)
    else:
        writer.writerow(["subject_id"])
        for sub in subject_set:
            writer.writerow([sub])

    f.close()

    UTLOGGER.info("Template Phenotypic file for group analysis - %s", file_name)

    file_name = os.path.join(output_path, "subject_list_group_analysis.txt")
    f = open(file_name, "w")

    for sub in subject_set:
        print(sub, file=f)

    UTLOGGER.info("Subject list required later for group analysis - %s", file_name)
    f.close()


def read_csv(csv_input):
    """
    Method to read csv file
     'Acquisition'
     'Reference'
     'Site'
     'TR (seconds)'.

    """
    from collections import defaultdict
    import csv

    try:
        reader = csv.DictReader(open(csv_input, "U"))
        dict_labels = defaultdict(list)
        for line in reader:
            csv_dict = {k.lower(): v for k, v in line.items()}
            dict_labels[csv_dict.get("site"), csv_dict.get("scan")] = [
                csv_dict[key]
                for key in sorted(csv_dict.keys())
                if key not in ("site", "scan")
            ]

        if len(dict_labels) < 1:
            msg = "Scan Parameters File is either empty or missing header"
            raise ValueError(msg)
    except:
        msg = "Error reading scan parameters csv"
        raise ValueError(msg)

    return dict_labels


"""
Class to set dictionary keys as map attributes
"""


class Configuration(object):
    def __init__(self, config_map):
        for key in config_map:
            if config_map[key] == "None":
                config_map[key] = None
            setattr(self, key, config_map[key])


def run(data_config):
    """
    Run method takes data_config
    file as the input argument.
    """
    c = Configuration(yaml.safe_load(open(os.path.realpath(data_config), "r")))

    if c.scanParametersCSV is not None:
        s_param_map = read_csv(c.scanParametersCSV)
    else:
        UTLOGGER.warning(
            "no scan parameters csv included. make sure you turn off slice timing"
            " correction option in CPAC configuration"
        )
        s_param_map = None

    extract_data(c, s_param_map)
    generate_suplimentary_files(c.outputSubjectListLocation)
