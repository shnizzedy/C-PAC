# -*- coding: utf-8 -*-
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
from nipype.interfaces import afni
import nipype.interfaces.utility as util

from CPAC.pipeline import nipype_pipeline_engine as pe
from CPAC.utils.interfaces import Function


def inverse_lesion(lesion_path):
    """Replace non-zeroes with zeroes and zeroes with ones.

    Check if the image contains more zeros than non-zeros, if so,
    replaces non-zeros by zeros and zeros by ones.

    Parameters
    ----------
    lesion_path : str
        path to the nifti file to be checked and inverted if needed

    Returns
    -------
    lesion_out : str
        path to the output file, if the lesion does not require to be inverted
        it returns the unchanged lesion_path input
    """
    import ntpath
    import os
    import shutil

    import nibabel as nib

    import CPAC.utils.nifti_utils as nu

    lesion_out = lesion_path

    if nu.more_zeros_than_ones(image=lesion_path):
        lesion_out = os.path.join(os.getcwd(), ntpath.basename(lesion_path))
        shutil.copyfile(lesion_path, lesion_out)
        nii = nu.inverse_nifti_values(image=lesion_path)
        nib.save(nii, lesion_out)
        return lesion_out
    return lesion_out


def create_lesion_preproc(cfg=None, wf_name="lesion_preproc"):
    """Process lesions masks.

    Lesion mask file is deobliqued and reoriented in the same way as the T1 in
    the anat_preproc function.

    Returns
    -------
    lesion_preproc : workflow
        Lesion preprocessing Workflow

    Workflow Inputs::
        inputspec.lesion : string
            User input lesion mask, in any of the 8 orientations

    Workflow Outputs::

        outputspec.refit : string
            Path to deobliqued anatomical image

        outputspec.reorient : string
            Path to RPI oriented anatomical image

    Order of commands:
    - Deobliqing the scans. ::
        3drefit -deoblique mprage.nii.gz

    - Re-orienting the Image into Right-to-Left Posterior-to-Anterior
    Inferior-to-Superior  (RPI) orientation ::
        3dresample -orient RPI
                   -prefix mprage_RPI.nii.gz
                   -inset mprage.nii.gz

    Examples
    --------
    >>> from CPAC.anat_preproc.lesion_preproc import create_lesion_preproc
    >>> preproc = create_lesion_preproc()
    >>> preproc.inputs.inputspec.lesion = 'sub1/anat/lesion-mask.nii.gz'
    >>> preproc.run() #doctest: +SKIP
    """
    preproc = pe.Workflow(name=wf_name)

    inputnode = pe.Node(util.IdentityInterface(fields=["lesion"]), name="inputspec")

    outputnode = pe.Node(
        util.IdentityInterface(fields=["refit", "reorient"]), name="outputspec"
    )

    lesion_deoblique = pe.Node(interface=afni.Refit(), name="lesion_deoblique")

    lesion_deoblique.inputs.deoblique = True

    lesion_inverted = pe.Node(
        interface=Function(
            input_names=["lesion_path"],
            output_names=["lesion_out"],
            function=inverse_lesion,
        ),
        name="inverse_lesion",
    )
    # We first check and invert the lesion if needed to be used by ANTs
    preproc.connect(inputnode, "lesion", lesion_inverted, "lesion_path")

    preproc.connect(lesion_inverted, "lesion_out", lesion_deoblique, "in_file")

    preproc.connect(lesion_deoblique, "out_file", outputnode, "refit")

    # Anatomical reorientation
    lesion_reorient = pe.Node(
        interface=afni.Resample(),
        name="lesion_reorient",
        mem_gb=0,
        mem_x=(0.0115, "in_file", "t"),
    )

    lesion_reorient.inputs.orientation = (
        cfg.pipeline_setup["desired_orientation"] if cfg else "RPI"
    )
    lesion_reorient.inputs.outputtype = "NIFTI_GZ"

    preproc.connect(lesion_deoblique, "out_file", lesion_reorient, "in_file")
    preproc.connect(lesion_reorient, "out_file", outputnode, "reorient")

    return preproc
