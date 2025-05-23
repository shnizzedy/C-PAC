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
from nipype.interfaces import afni, fsl, utility as util

from CPAC.connectome.connectivity_matrix import (
    create_connectome_afni,
    create_connectome_nilearn,
    get_connectome_method,
)
from CPAC.pipeline import nipype_pipeline_engine as pe
from CPAC.pipeline.nodeblock import nodeblock
from CPAC.utils.datasource import (
    create_roi_mask_dataflow,
    create_spatial_map_dataflow,
    resample_func_roi,
)
from CPAC.utils.interfaces import Function
from CPAC.utils.monitoring import FMLOGGER


def get_voxel_timeseries(wf_name: str = "voxel_timeseries") -> pe.Workflow:
    """
    Extract time series for each voxel in data that are present in the input mask.

    Parameters
    ----------
    wf_name : string
        name of the workflow

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/main/CPAC/timeseries/timeseries_analysis.py>`_

    Workflow Inputs::

        inputspec.rest : string  (nifti file)
            path to input functional data
        inputspec.output_type : string (list of boolean)
            list of boolean for csv and npz file formats
        input_mask.masks : string (nifti file)
            path to ROI mask

    Workflow Outputs::

        outputspec.mask_outputs: string (1D, csv and/or npz files)
            list of time series matrices stored in csv and/or
            npz files.By default it outputs mean of voxels
            across each time point in a afni compatible 1D file.

        High Level Workflow Graph:

    Example
    -------
    >>> import CPAC.timeseries.timeseries_analysis as t
    >>> wf = t.get_voxel_timeseries()
    >>> wf.inputs.inputspec.rest = '/home/data/rest.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.input_mask.mask = '/usr/local/fsl/data/standard/MNI152_T1_2mm_brain.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.output_type = [True,True]
    >>> wf.base_dir = './'
    >>> wf.run()  # doctest: +SKIP

    """
    wflow = pe.Workflow(name=wf_name)

    inputNode = pe.Node(
        util.IdentityInterface(fields=["rest", "output_type"]), name="inputspec"
    )
    inputNode_mask = pe.Node(util.IdentityInterface(fields=["mask"]), name="input_mask")

    outputNode = pe.Node(
        util.IdentityInterface(fields=["mask_outputs"]), name="outputspec"
    )

    timeseries_voxel = pe.Node(
        Function(
            input_names=["data_file", "template"],
            output_names=["oneD_file"],
            function=gen_voxel_timeseries,
        ),
        name="timeseries_voxel",
    )

    wflow.connect(inputNode, "rest", timeseries_voxel, "data_file")
    # wflow.connect(inputNode, 'output_type',
    #              timeseries_voxel, 'output_type')
    wflow.connect(inputNode_mask, "mask", timeseries_voxel, "template")

    wflow.connect(timeseries_voxel, "oneD_file", outputNode, "mask_outputs")

    return wflow


def clean_roi_csv(roi_csv):
    """Remove file path comments from every other row of AFNI's 3dROIstats output.

    3dROIstats has a -nobriklab and a -quiet option, but neither remove the
    file path comments while retaining the ROI label header, which is needed.

    If there are no file path comments to remove, this function simply
    passes the original file as output, instead of unnecessarily opening and
    re-writing it.

    Parameters
    ----------
    roi_csv : str
        path to CSV

    Returns
    -------
    roi_array : numpy.ndarray

    edited_roi_csv: str
        path to CSV
    """
    import os

    import numpy as np
    import pandas as pd

    with open(roi_csv, "r") as f:
        csv_lines = f.readlines()

    # flag whether to re-write
    modified = False

    edited_lines = []
    for line in csv_lines:
        line = line.replace("\t\t\t", "")
        line = line.replace("\t\t", "")
        line = line.replace("\t", ",")
        line = line.replace("#,", "#")
        if "#" in line:
            if "/" in line and "." in line:
                modified = True
                continue
            if "Sub-brick" in line:
                modified = True
                continue
        edited_lines.append(line)

    if modified:
        edited_roi_csv = os.path.join(os.getcwd(), os.path.basename(roi_csv))
        with open(edited_roi_csv, "wt") as f:
            for line in edited_lines:
                f.write(line)
    else:
        edited_roi_csv = roi_csv

    data = pd.read_csv(edited_roi_csv, sep=",", header=1)
    data = data.dropna(axis=1)
    roi_array = np.transpose(data.values)

    return roi_array, edited_roi_csv


def get_roi_timeseries(wf_name: str = "roi_timeseries") -> pe.Workflow:
    """
    Extract timeseries for each node in the ROI mask.

    For each node, mean across all the timepoint is calculated and stored
    in csv and npz format.

    Parameters
    ----------
    wf_name : string
        name of the workflow

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/main/CPAC/timeseries/timeseries_analysis.py>`_

    Workflow Inputs::

        inputspec.rest : string  (nifti file)
            path to input functional data
        inputspec.output_type : string (list of boolean)
            list of boolean for csv and npz file formats
        input_roi.roi : string (nifti file)
            path to ROI mask

    Workflow Outputs::

        outputspec.roi_ts : numpy array
            Voxel time series stored in numpy array, which is used to create ndmg graphs.

        outputspec.roi_outputs : string (list of files)
            Voxel time series stored in 1D (column wise timeseries for each node),
            csv and/or npz files. By default it outputs timeseries in a 1D file.
            The 1D file is compatible with afni interfaces.

    Example
    -------
    >>> import CPAC.timeseries.timeseries_analysis as t
    >>> wf = t.get_roi_timeseries()
    >>> wf.inputs.inputspec.rest = '/home/data/rest.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.input_roi.roi = '/usr/local/fsl/data/atlases/HarvardOxford/HarvardOxford-cort-maxprob-thr0-2mm.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.output_type = [True,True]  # doctest: +SKIP
    >>> wf.base_dir = './'
    >>> wf.run()  # doctest: +SKIP

    """
    wflow = pe.Workflow(name=wf_name)

    inputNode = pe.Node(util.IdentityInterface(fields=["rest"]), name="inputspec")

    inputnode_roi = pe.Node(util.IdentityInterface(fields=["roi"]), name="input_roi")

    outputNode = pe.Node(
        util.IdentityInterface(fields=["roi_ts", "roi_csv"]), name="outputspec"
    )

    timeseries_roi = pe.Node(
        interface=afni.ROIStats(),
        name="3dROIstats",
        mem_gb=0.4,
        mem_x=(756789500459879 / 37778931862957161709568, "in_file"),
    )
    timeseries_roi.inputs.quiet = False
    timeseries_roi.inputs.args = "-1Dformat"
    # TODO: add -mask_f2short for float parcellation mask
    # if parcellation mask has float values
    #     timeseries_roi.inputs.mask_f2short = True

    wflow.connect(inputNode, "rest", timeseries_roi, "in_file")

    wflow.connect(inputnode_roi, "roi", timeseries_roi, "mask_file")

    clean_csv_imports = ["import os"]
    clean_csv = pe.Node(
        Function(
            input_names=["roi_csv"],
            output_names=["roi_array", "edited_roi_csv"],
            function=clean_roi_csv,
            imports=clean_csv_imports,
        ),
        name="clean_roi_csv",
    )

    wflow.connect(timeseries_roi, "out_file", clean_csv, "roi_csv")
    wflow.connect(clean_csv, "roi_array", outputNode, "roi_ts")
    wflow.connect(clean_csv, "edited_roi_csv", outputNode, "roi_csv")

    return wflow


def get_spatial_map_timeseries(wf_name: str = "spatial_map_timeseries") -> pe.Workflow:
    """
    Regress each provided spatial map to the subjects functional 4D file...

    ...in order to return a timeseries for each of the maps.

    Parameters
    ----------
    wf_name : string
        name of the workflow

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/main/CPAC/timeseries/timeseries_analysis.py>`_

    Workflow Inputs::

        inputspec.subject_rest : string  (nifti file)
            path to input functional data
        inputspec.subject_mask : string (nifti file)
            path to subject functional mask
        inputspec.spatial_map : string (nifti file)
            path to Spatial Maps
        inputspec.demean : Boolean
            control whether to demean model and data

    Workflow Outputs::

        outputspec.subject_timeseries: string (txt file)
            list of time series stored in a space separated
            txt file
            the columns are spatial maps, rows are timepoints


    Example
    -------
    >>> import CPAC.timeseries.timeseries_analysis as t
    >>> wf = t.get_spatial_map_timeseries()
    >>> wf.inputs.inputspec.subject_rest = '/home/data/rest.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.subject_mask = '/home/data/rest_mask.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.ICA_map = '/home/data/spatialmaps/spatial_map.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.demean = True
    >>> wf.base_dir = './'
    >>> wf.run()  # doctest: +SKIP

    """
    wflow = pe.Workflow(name=wf_name)

    inputNode = pe.Node(
        util.IdentityInterface(
            fields=["subject_rest", "subject_mask", "spatial_map", "demean"]
        ),
        name="inputspec",
    )

    outputNode = pe.Node(
        util.IdentityInterface(fields=["subject_timeseries"]), name="outputspec"
    )

    spatialReg = pe.Node(
        interface=fsl.GLM(),
        name="spatial_regression",
        mem_gb=0.2,
        mem_x=(1708448960473801 / 302231454903657293676544, "in_file"),
    )

    spatialReg.inputs.out_file = "spatial_map_timeseries.txt"

    wflow.connect(inputNode, "subject_rest", spatialReg, "in_file")
    wflow.connect(inputNode, "subject_mask", spatialReg, "mask")
    wflow.connect(inputNode, "spatial_map", spatialReg, "design")
    wflow.connect(inputNode, "demean", spatialReg, "demean")
    wflow.connect(spatialReg, "out_file", outputNode, "subject_timeseries")

    return wflow


def get_vertices_timeseries(wf_name="vertices_timeseries"):
    """
    Workflow to get vertices time series from a FreeSurfer surface file.

    Parameters
    ----------
    wf_name : string
        name of the workflow

    Returns
    -------
    wflow : workflow object
        workflow object

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/main/CPAC/timeseries/timeseries_analysis.py>`_

    Workflow Inputs::

        inputspec.lh_surface_file : string (nifti file)
            left hemishpere surface file
        inputspec.rh_surface_file : string (nifti file)
            right hemisphere surface file

    Workflow Outputs::

        outputspec.surface_outputs: string (csv and/or npz files)
            list of timeseries matrices stored in csv and/or
            npz files

    Example
    -------
    >>> import CPAC.timeseries.timeseries_analysis as t
    >>> wf = t.get_vertices_timeseries()
    >>> wf.inputs.inputspec.lh_surface_file = '/home/data/outputs/SurfaceRegistration/lh_surface_file.nii.gz'  # doctest: +SKIP
    >>> wf.inputs.inputspec.rh_surface_file = '/home/data/outputs/SurfaceRegistration/rh_surface_file.nii.gz'  # doctest: +SKIP
    >>> wf.base_dir = './'
    >>> wf.run()  # doctest: +SKIP
    """
    wflow = pe.Workflow(name=wf_name)

    inputNode = pe.Node(
        util.IdentityInterface(fields=["lh_surface_file", "rh_surface_file"]),
        name="inputspec",
    )

    timeseries_surface = pe.Node(
        Function(
            input_names=["rh_surface_file", "lh_surface_file"],
            output_names=["out_file"],
            function=gen_vertices_timeseries,
        ),
        name="timeseries_surface",
    )

    outputNode = pe.Node(
        util.IdentityInterface(fields=["surface_outputs"]), name="outputspec"
    )

    wflow.connect(inputNode, "rh_surface_file", timeseries_surface, "rh_surface_file")
    wflow.connect(inputNode, "lh_surface_file", timeseries_surface, "lh_surface_file")

    wflow.connect(timeseries_surface, "out_file", outputNode, "surface_outputs")

    return wflow


def get_normalized_moments(wf_name="normalized_moments"):
    """
    Workflow to calculate the normalized moments for skewedness calculations.

    Parameters
    ----------
    wf_name : string
        name of the workflow

    Returns
    -------
    wflow : workflow object
        workflow object

    Notes
    -----
    `Source <https://github.com/FCP-INDI/C-PAC/blob/main/CPAC/timeseries/timeseries_analysis.py>`_

    Workflow Inputs::

        inputspec.spatial_timeseries : string (nifti file)
            spatial map timeseries

    Workflow Outputs::

        outputspec.moments: list
            list of moment values

    Example
    -------
    >>> import CPAC.timeseries.timeseries_analysis as t
    >>> wf = t.get_normalized_moments()  # doctest: +SKIP
    >>> wf.inputs.inputspec.spatial_timeseries = '/home/data/outputs/SurfaceRegistration/lh_surface_file.nii.gz'  # doctest: +SKIP
    >>> wf.base_dir = './'  # doctest: +SKIP
    >>> wf.run()  # doctest: +SKIP
    """
    wflow = pe.Workflow(name=wf_name)

    inputNode = pe.Node(
        util.IdentityInterface(fields=["spatial_timeseries"]), name="inputspec"
    )

    # calculate normalized moments
    # output of this node is a list, 'moments'
    norm_moments = pe.Node(
        util.CalculateNormalizedMoments(moment="3"), name="norm_moments"
    )

    outputNode = pe.Node(
        util.IdentityInterface(fields=["moments_outputs"]), name="outputspec"
    )

    wflow.connect(inputNode, "spatial_timeseries", norm_moments, "timeseries_file")
    wflow.connect(norm_moments, "moments", outputNode, "moments_outputs")

    return wflow


def gen_roi_timeseries(data_file, template, output_type):
    """
    Extract mean of voxel across all timepoints for each node in roi mask.

    Parameters
    ----------
    data_file : string
        path to input functional data
    template : string
        path to input roi mask in functional native space
    output_type : list
        list of two boolean values suggesting
        the output types - numpy npz file and csv
        format

    Returns
    -------
    out_list : list
        list of 1D file, txt file, csv file and/or npz file containing
        mean timeseries for each scan corresponding
        to each node in roi mask

    Raises
    ------
    Exception

    """
    import csv
    import os
    import shutil

    import numpy as np
    import nibabel as nib

    unit_data = nib.load(template).get_fdata()
    # Cast as rounded-up integer
    unit_data = np.int64(np.ceil(unit_data))
    datafile = nib.load(data_file)
    img_data = datafile.get_fdata()
    img_data.shape[3]

    if unit_data.shape != img_data.shape[:3]:
        msg = (
            "\n\n[!] CPAC says: Invalid Shape Error."
            "Please check the voxel dimensions. "
            "Data and roi should have the same shape.\n\n"
        )
        raise Exception(msg)

    nodes = np.unique(unit_data).tolist()
    sorted_list = []
    node_dict = {}
    out_list = []

    # extracting filename from input template
    tmp_file = os.path.splitext(os.path.basename(template))[0]
    tmp_file = os.path.splitext(tmp_file)[0]
    oneD_file = os.path.abspath("roi_" + tmp_file + ".1D")
    txt_file = os.path.abspath("roi_" + tmp_file + ".txt")
    os.path.abspath("roi_" + tmp_file + ".csv")
    os.path.abspath("roi_" + tmp_file + ".npz")

    nodes.sort()
    for n in nodes:
        if n > 0:
            node_array = img_data[unit_data == n]
            node_str = f"node_{n}"
            avg = np.mean(node_array, axis=0)
            avg = np.round(avg, 6)
            list1 = [n, *avg.tolist()]
            sorted_list.append(list1)
            node_dict[node_str] = avg.tolist()

    # writing to 1Dfile
    FMLOGGER.info("writing 1D file..")
    f = open(oneD_file, "w")
    writer = csv.writer(f, delimiter=",")

    value_list = []

    new_keys = sorted([int(float(key.split("node_")[1])) for key in node_dict])

    roi_number_list = [str(n) for n in new_keys]

    roi_number_str = []
    for number in roi_number_list:
        roi_number_str.append("#" + number)

    for key in new_keys:
        value_list.append(str("{0}\n".format(node_dict[f"node_{key}"])))

    column_list = list(zip(*value_list))

    writer.writerow(roi_number_str)

    for column in column_list:
        writer.writerow(list(column))
    f.close()

    out_list.append(oneD_file)

    # copy the 1D contents to txt file
    shutil.copy(oneD_file, txt_file)
    out_list.append(txt_file)

    # if csv is required
    """
    if output_type[0]:
        FMLOGGER.info("writing csv file..")
        f = open(csv_file, 'wt')
        writer = csv.writer(f, delimiter=',', quoting=csv.QUOTE_MINIMAL)
        headers = ['node/volume'] + np.arange(vol).tolist()
        writer.writerow(headers)
        writer.writerows(sorted_list)
        f.close()
        out_list.append(csv_file)

    # if npz file is required
    if output_type[1]:
        FMLOGGER.info("writing npz file..")
        np.savez(numpy_file, roi_data=value_list, roi_numbers=roi_number_list)
        out_list.append(numpy_file)

    return out_list
    """

    return oneD_file


def gen_voxel_timeseries(data_file: str, template: str) -> str:
    """
    Extract timeseries for each voxel in the data that is present in the input mask.

    Parameters
    ----------
    datafile : string (nifti file)
        path to input functional data
    template : string (nifti file)
        path to input mask in functional native space

    Returns
    -------
    oneD_file : str
        Path to the created .1D file containing the mean timeseries vector.

    Raises
    ------
    Exception

    """
    import csv
    import os

    import numpy as np
    import nibabel as nib

    unit = nib.load(template)
    unit_data = unit.get_fdata()
    datafile = nib.load(data_file)
    img_data = datafile.get_fdata()
    header_data = datafile.header
    qform = header_data.get_qform()
    sorted_list = []

    tmp_file = os.path.splitext(os.path.basename(template))[0]
    tmp_file = os.path.splitext(tmp_file)[0]
    oneD_file = os.path.abspath("mask_" + tmp_file + ".1D")
    f = open(oneD_file, "wt")

    node_array = img_data[unit_data != 0]
    node_array = node_array.T
    time_points = node_array.shape[0]
    for t in range(0, time_points):
        f.write(str(np.round(np.mean(node_array[t]), 6)))
        f.write("\n")
        val = node_array[t].tolist()
        val.insert(0, t)
        sorted_list.append(val)

    f.close()

    csv_file = os.path.abspath("mask_" + tmp_file + ".csv")
    f = open(csv_file, "wt")
    writer = csv.writer(f, delimiter=str(","), quoting=csv.QUOTE_MINIMAL)
    one = np.array([1])
    headers = ["volume/xyz"]
    coordinates = np.argwhere(unit_data != 0)
    for val in range(len(coordinates)):
        ijk_mat = np.concatenate([coordinates[val], one])
        ijk_mat = ijk_mat.T
        product = np.dot(qform, ijk_mat)
        val = tuple(product.tolist()[0:3])
        headers.append(val)
    writer.writerow(headers)
    writer.writerows(sorted_list)
    f.close()

    return oneD_file


def gen_vertices_timeseries(rh_surface_file, lh_surface_file):
    """
    Extract timeseries from vertices of a freesurfer surface file.

    Parameters
    ----------
    rh_surface_file : string (mgz/mgh file)
        left hemisphere FreeSurfer surface file
    lh_surface_file : string (mgz/mgh file)
        right hemisphere FreeSurfer surface file

    Returns
    -------
    out_list : string (list of file)
        list of vertices timeseries csv files

    """
    import os

    import gradunwarp
    import numpy as np

    out_list = []
    rh_file = os.path.splitext(os.path.basename(rh_surface_file))[0] + "_rh.csv"
    mghobj1 = gradunwarp.mgh.MGH()

    mghobj1.load(rh_surface_file)
    vol = mghobj1.vol
    (x, y) = vol.shape
    #        IFLOGGER.info("rh shape %s %s", x, y)

    np.savetxt(rh_file, vol, delimiter="\t")
    out_list.append(rh_file)

    lh_file = os.path.splitext(os.path.basename(lh_surface_file))[0] + "_lh.csv"
    mghobj2 = gradunwarp.mgh.MGH()

    mghobj2.load(lh_surface_file)
    vol = mghobj2.vol
    (x, y) = vol.shape
    #        IFLOGGER.info("lh shape %s %s", x, y)

    np.savetxt(lh_file, vol, delimiter=",")
    out_list.append(lh_file)

    return out_list


def resample_function() -> "Function":
    """
    Return a Function interface for :py:func:`~CPAC.utils.datasource.resample_func_roi`.

    Returns
    -------
    Function
    """
    return Function(
        input_names=["in_func", "in_roi", "realignment", "identity_matrix"],
        output_names=["out_func", "out_roi"],
        function=resample_func_roi,
        as_module=True,
    )


@nodeblock(
    name="timeseries_extraction_AVG",
    config=["timeseries_extraction"],
    switch=["run"],
    inputs=["space-template_desc-preproc_bold", "space-template_desc-bold_mask"],
    outputs=[
        "space-template_desc-Mean_timeseries",
        "space-template_desc-ndmg_correlations",
        "atlas_name",
        "space-template_desc-PearsonAfni_correlations",
        "space-template_desc-PartialAfni_correlations",
        "space-template_desc-PearsonNilearn_correlations",
        "space-template_desc-PartialNilearn_correlations",
    ],
)
def timeseries_extraction_AVG(wf, cfg, strat_pool, pipe_num, opt=None):
    resample_functional_roi = pe.Node(
        resample_function(), name=f"resample_functional_roi_{pipe_num}"
    )
    realignment = cfg.timeseries_extraction["realignment"]
    resample_functional_roi.inputs.realignment = realignment
    resample_functional_roi.inputs.identity_matrix = cfg.registration_workflows[
        "functional_registration"
    ]["func_registration_to_template"]["FNIRT_pipelines"]["identity_matrix"]

    roi_dataflow = create_roi_mask_dataflow(
        cfg.timeseries_extraction["tse_atlases"]["Avg"], f"roi_dataflow_{pipe_num}"
    )

    roi_dataflow.inputs.inputspec.set(
        creds_path=cfg.pipeline_setup["input_creds_path"],
        dl_dir=cfg.pipeline_setup["working_directory"]["path"],
    )

    roi_timeseries = get_roi_timeseries(f"roi_timeseries_{pipe_num}")
    # roi_timeseries.inputs.inputspec.output_type = cfg.timeseries_extraction[
    #    'roi_tse_outputs']

    node, out = strat_pool.get_data("space-template_desc-preproc_bold")
    wf.connect(node, out, resample_functional_roi, "in_func")

    wf.connect(roi_dataflow, "outputspec.out_file", resample_functional_roi, "in_roi")

    # connect it to the roi_timeseries
    # workflow.connect(roi_dataflow, 'outputspec.out_file',
    #                  roi_timeseries, 'input_roi.roi')
    wf.connect(resample_functional_roi, "out_roi", roi_timeseries, "input_roi.roi")
    wf.connect(resample_functional_roi, "out_func", roi_timeseries, "inputspec.rest")

    # create the graphs:
    # - connectivity matrix
    matrix_outputs = {}
    for cm_measure in cfg["timeseries_extraction", "connectivity_matrix", "measure"]:
        for cm_tool in [
            tool
            for tool in cfg["timeseries_extraction", "connectivity_matrix", "using"]
            if tool != "ndmg"
        ]:
            implementation = get_connectome_method(cm_measure, cm_tool)
            if implementation is NotImplemented:
                continue

            if cm_tool == "Nilearn":
                timeseries_correlation = create_connectome_nilearn(
                    name=f"connectomeNilearn{cm_measure}_{pipe_num}"
                )

            elif cm_tool == "AFNI":
                timeseries_correlation = create_connectome_afni(
                    name=f"connectomeAfni{cm_measure}_{pipe_num}",
                    method=cm_measure,
                    pipe_num=pipe_num,
                )
                brain_mask_node, brain_mask_out = strat_pool.get_data(
                    ["space-template_desc-bold_mask"]
                )
                if "func_to_ROI" in realignment:
                    resample_brain_mask_roi = pe.Node(
                        resample_function(), name=f"resample_brain_mask_roi_{pipe_num}"
                    )
                    resample_brain_mask_roi.inputs.realignment = realignment
                    resample_brain_mask_roi.inputs.identity_matrix = (
                        cfg.registration_workflows["functional_registration"][
                            "func_registration_to_template"
                        ]["FNIRT_pipelines"]["identity_matrix"]
                    )
                    wf.connect(
                        [
                            (
                                brain_mask_node,
                                resample_brain_mask_roi,
                                [(brain_mask_out, "in_func")],
                            ),
                            (
                                roi_dataflow,
                                resample_brain_mask_roi,
                                [("outputspec.out_file", "in_roi")],
                            ),
                            (
                                resample_brain_mask_roi,
                                timeseries_correlation,
                                [("out_func", "inputspec.mask")],
                            ),
                        ]
                    )
                else:
                    wf.connect(
                        brain_mask_node,
                        brain_mask_out,
                        timeseries_correlation,
                        "inputspec.mask",
                    )

            timeseries_correlation.inputs.inputspec.method = cm_measure
            wf.connect(
                [
                    (
                        roi_dataflow,
                        timeseries_correlation,
                        [("outputspec.out_name", "inputspec.atlas_name")],
                    ),
                    (
                        resample_functional_roi,
                        timeseries_correlation,
                        [
                            ("out_roi", "inputspec.in_rois"),
                            ("out_func", "inputspec.in_file"),
                        ],
                    ),
                ]
            )

            output_desc = "".join(
                term.lower().capitalize() for term in [cm_measure, cm_tool]
            )
            matrix_outputs[f"space-template_desc-{output_desc}_correlations"] = (
                timeseries_correlation,
                "outputspec.out_file",
            )

    outputs = {
        "space-template_desc-Mean_timeseries": (roi_timeseries, "outputspec.roi_csv"),
        "atlas_name": (roi_dataflow, "outputspec.out_name"),
        **matrix_outputs,
    }
    # - NDMG
    if "ndmg" in cfg["timeseries_extraction", "connectivity_matrix", "using"]:
        # pylint: disable=import-outside-toplevel
        from CPAC.utils.ndmg_utils import ndmg_create_graphs

        ndmg_graph_imports = ["import os", "from CPAC.utils.ndmg_utils import graph"]
        ndmg_graph = pe.Node(
            Function(
                input_names=["ts", "labels"],
                output_names=["out_file"],
                function=ndmg_create_graphs,
                imports=ndmg_graph_imports,
                as_module=True,
            ),
            name=f"ndmg_graphs_{pipe_num}",
            mem_gb=0.664,
            mem_x=(1928411764134803 / 302231454903657293676544, "ts"),
        )

        wf.connect(roi_timeseries, "outputspec.roi_ts", ndmg_graph, "ts")
        wf.connect(roi_dataflow, "outputspec.out_file", ndmg_graph, "labels")
        outputs["space-template_desc-ndmg_correlations"] = (ndmg_graph, "out_file")

    return (wf, outputs)


@nodeblock(
    name="timeseries_extraction_Voxel",
    config=["timeseries_extraction"],
    switch=["run"],
    inputs=["space-template_desc-preproc_bold"],
    outputs=["desc-Voxel_timeseries", "atlas_name"],
)
def timeseries_extraction_Voxel(wf, cfg, strat_pool, pipe_num, opt=None):
    resample_functional_to_mask = pe.Node(
        resample_function(), name=f"resample_functional_to_mask_{pipe_num}"
    )

    resample_functional_to_mask.inputs.realignment = cfg.timeseries_extraction[
        "realignment"
    ]
    resample_functional_to_mask.inputs.identity_matrix = cfg.registration_workflows[
        "functional_registration"
    ]["func_registration_to_template"]["FNIRT_pipelines"]["identity_matrix"]

    mask_dataflow = create_roi_mask_dataflow(
        cfg.timeseries_extraction["tse_atlases"]["Voxel"], f"mask_dataflow_{pipe_num}"
    )

    voxel_timeseries = get_voxel_timeseries(f"voxel_timeseries_{pipe_num}")
    # voxel_timeseries.inputs.inputspec.output_type = cfg.timeseries_extraction[
    #    'roi_tse_outputs']

    node, out = strat_pool.get_data("space-template_desc-preproc_bold")
    # resample the input functional file to mask
    wf.connect(node, out, resample_functional_to_mask, "in_func")
    wf.connect(
        mask_dataflow, "outputspec.out_file", resample_functional_to_mask, "in_roi"
    )

    # connect it to the voxel_timeseries
    wf.connect(
        resample_functional_to_mask, "out_roi", voxel_timeseries, "input_mask.mask"
    )
    wf.connect(
        resample_functional_to_mask, "out_func", voxel_timeseries, "inputspec.rest"
    )

    outputs = {
        "desc-Voxel_timeseries": (voxel_timeseries, "outputspec.mask_outputs"),
        "atlas_name": (mask_dataflow, "outputspec.out_name"),
    }

    return (wf, outputs)


@nodeblock(
    name="spatial_regression",
    config=["timeseries_extraction"],
    switch=["run"],
    inputs=[
        "space-template_desc-preproc_bold",
        ["space-template_desc-bold_mask", "space-template_desc-brain_mask"],
    ],
    outputs=["desc-SpatReg_timeseries", "atlas_name"],
)
def spatial_regression(wf, cfg, strat_pool, pipe_num, opt=None):
    """Perform spatial regression.

    Extracts the spatial map timeseries of the given atlases.

    Note: this is a standalone function for when only spatial regression is
          selected for the given atlases - if dual regression is selected,
          that spatial regression is performed in the dual_regression function
    """
    resample_spatial_map_to_native_space = pe.Node(
        interface=fsl.FLIRT(),
        name=f"resample_spatial_map_to_native_space_{pipe_num}",
        mem_gb=3.4,
        mem_x=(5381614225492473 / 1208925819614629174706176, "in_file"),
    )

    resample_spatial_map_to_native_space.inputs.set(
        interp="nearestneighbour",
        apply_xfm=True,
        in_matrix_file=cfg.registration_workflows["functional_registration"][
            "func_registration_to_template"
        ]["FNIRT_pipelines"]["identity_matrix"],
    )

    spatial_map_dataflow = create_spatial_map_dataflow(
        cfg.timeseries_extraction["tse_atlases"]["SpatialReg"],
        f"spatial_map_dataflow_{pipe_num}",
    )

    spatial_map_dataflow.inputs.inputspec.set(
        creds_path=cfg.pipeline_setup["input_creds_path"],
        dl_dir=cfg.pipeline_setup["working_directory"]["path"],
    )

    spatial_map_timeseries = get_spatial_map_timeseries(
        f"spatial_map_timeseries_{pipe_num}"
    )
    spatial_map_timeseries.inputs.inputspec.demean = True

    node, out = strat_pool.get_data("space-template_desc-preproc_bold")

    # resample the input functional file and functional mask
    # to spatial map
    wf.connect(node, out, resample_spatial_map_to_native_space, "reference")
    wf.connect(
        spatial_map_dataflow,
        "select_spatial_map.out_file",
        resample_spatial_map_to_native_space,
        "in_file",
    )

    wf.connect(node, out, spatial_map_timeseries, "inputspec.subject_rest")

    # connect it to the spatial_map_timeseries
    wf.connect(
        resample_spatial_map_to_native_space,
        "out_file",
        spatial_map_timeseries,
        "inputspec.spatial_map",
    )

    node, out = strat_pool.get_data(
        ["space-template_desc-bold_mask", "space-template_desc-brain_mask"]
    )
    wf.connect(node, out, spatial_map_timeseries, "inputspec.subject_mask")

    # 'atlas_name' will be an iterable and will carry through
    outputs = {
        "desc-SpatReg_timeseries": (
            spatial_map_timeseries,
            "outputspec.subject_timeseries",
        ),
        "atlas_name": (spatial_map_dataflow, "select_spatial_map.out_name"),
    }

    return (wf, outputs)
