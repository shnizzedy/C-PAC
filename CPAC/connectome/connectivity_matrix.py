#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Functions for creating connectome connectivity matrices."""
from warnings import warn
import numpy as np
from nilearn.connectome import ConnectivityMeasure
from nilearn.input_data import NiftiLabelsMasker
from nipype import logging
from nipype.interfaces import utility as util
from CPAC.pipeline import nipype_pipeline_engine as pe
from CPAC.pipeline.schema import valid_options
from CPAC.utils.datasource import create_roi_mask_dataflow
from CPAC.utils.interfaces.function import Function
from CPAC.utils.interfaces.netcorr import NetCorr

logger = logging.getLogger('workflow')
connectome_methods = {
    'afni': {'Pearson': '',
             'Partial': '-part_corr'},
    'nilearn': {'Pearson': 'correlation',
                'Partial': 'partial correlation'}
}


def connectome_name(time_series, method):
    """Helper function to create connectome file filename

    Parameters
    ----------
    time_series : str
        path to input time series

    method : str
        BIDS entity value for `desc-` key

    Returns
    -------
    str
    """
    method = ''.join(word.capitalize() for word in method.split(' '))
    new_filename_parts = time_series.split('_')[:-1][::-1]
    if any(filename_part.startswith('desc-') for filename_part in
            new_filename_parts):
        for i, filename_part in enumerate(new_filename_parts):
            if filename_part.startswith('desc-'):
                new_filename_parts[-i] = (
                    filename_part + method.capitalize())
                break
    return '_'.join([*new_filename_parts[::-1], 'connectome.tsv'])


def get_connectome_method(method, tool):
    """Helper function to get tool's method string

    Parameters
    ----------
    method : str

    tool : str

    Returns
    -------
    str or NotImplemented

    Examples
    --------
    >>> get_connectome_method('Pearson', 'AFNI')
    ''
    >>> get_connectome_method('Pearson', 'Nilearn')
    'correlation'
    >>> get_connectome_method('Spearman', 'AFNI')
    NotImplemented
    """
    cm_method = connectome_methods[tool.lower()].get(method, NotImplemented)
    if cm_method is NotImplemented:
        warning_message = (
            f'{method} has not yet been implemented for {tool} in C-PAC.')
        if logger:
            logger.warning(NotImplementedError(warning_message))
        else:
            warn(warning_message, category=Warning)
    return cm_method


def compute_connectome_nilearn(in_rois, in_file, method):
    """Function to compute a connectome matrix using Nilearn

    Parameters
    ----------
    in_rois : Niimg-like object
        http://nilearn.github.io/manipulating_images/input_output.html#niimg-like-objects
        Region definitions, as one image of labels.

    in_file : str
        path to timeseries image

    method: str
        'Pearson' or 'Partial'

    Returns
    -------
    numpy.ndarray or NotImplemented
    """
    output = connectome_name(in_file, f'Nilearn{method}')
    method = get_connectome_method(method, 'Nilearn')
    if method is NotImplemented:
        return NotImplemented
    masker = NiftiLabelsMasker(labels_img=in_rois,
                               standardize=True,
                               verbose=True)
    timeser = masker.fit_transform(in_file)
    correlation_measure = ConnectivityMeasure(kind=method)
    corr_matrix = correlation_measure.fit_transform([timeser])[0]
    np.fill_diagonal(corr_matrix, 0)
    np.savetxt(output, corr_matrix, delimiter='\t')
    return output


def create_connectome_afni(name='connectomeAfni'):
    wf = pe.Workflow(name=name)
    inputspec = pe.Node(
        util.IdentityInterface(fields=[
            'in_rois',  # parcellation
            'in_file',  # timeseries
            'method'
        ]),
        name='inputspec'
    )
    outputspec = pe.Node(
        util.IdentityInterface(fields=[
            'connectome',
        ]),
        name='outputspec'
    )
    # timeseries_correlation = pe.Node(
    #     NetCorr(),
    #     name=f'connectomeAFNI{measure}_{pipe_num}')
    # if implementation:
    #     timeseries_correlation.inputs.part_corr = (
    #         measure == 'Partial'
    #     )
    # inputspec = pe.Node(
    #     util.IdentityInterface(fields=[
    #         'in_rois',  # parcellation
    #         'in_file',  # timeseries
    #         'method'
    #     ]),
    #     name='inputspec'
    # )
    # outputspec = pe.Node(
    #     util.IdentityInterface(fields=[
    #         'connectome',
    #     ]),
    #     name='outputspec'
    # )
    # node = pe.Node(Function(input_names=['in_rois', 'in_file', 'method'],
    #                         output_names=['connectome'],
    #                         function=compute_connectome_nilearn,
    #                         as_module=True),
    #                name='connectome')
    # wf.connect([
    #     (inputspec, node, [('in_rois', 'in_rois')]),
    #     (inputspec, node, [('in_file', 'in_file')]),
    #     (inputspec, node, [('method', 'method')]),
    #     (node, outputspec, [('connectome', 'connectome')]),
    # ])
    return wf


def create_connectome_nilearn(name='connectomeNilearn'):
    wf = pe.Workflow(name=name)
    inputspec = pe.Node(
        util.IdentityInterface(fields=[
            'in_rois',  # parcellation
            'in_file',  # timeseries
            'method'
        ]),
        name='inputspec'
    )
    outputspec = pe.Node(
        util.IdentityInterface(fields=[
            'connectome', 
        ]),
        name='outputspec'
    )
    node = pe.Node(Function(input_names=['in_rois', 'in_file', 'method'],
                            output_names=['connectome'],
                            function=compute_connectome_nilearn,
                            as_module=True),
                   name='connectome')
    wf.connect([
        (inputspec, node, [('in_rois', 'in_rois')]),
        (inputspec, node, [('in_file', 'in_file')]),
        (inputspec, node, [('method', 'method')]),
        (node, outputspec, [('connectome', 'connectome')]),
    ])
    return wf
