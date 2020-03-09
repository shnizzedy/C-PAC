# coding=utf-8
import glob
import sys

from itertools import chain

from subjects import fmriprep_sub

def main(argv):
    print('🔬 Test ≟.')

def get_paths(feature, sub_list, run_path, software="C-PAC"):
    """
    Function to generate a list of paths to outputs and working files to compare

    Parameters
    ----------
    feature: str

    sub_list: list of str

    run_path: str

    software: str

    Returns
    -------
    path_list: list of str
    """
    if feature=="nuisance":
        if software.lower() in ["cpac", "c-pac"]:
            return(list(chain.from_iterable([
                glob.glob( # CSF WM GS regressors
                    f'{run_path}/working/'
                    f'resting_preproc_{fmriprep_sub(sub)}{sub[-6:]}/'
                    'nuisance_0_0/_*/*/build*/*1D'
                ) + glob.glob( # frame wise displacement power
                    f'{run_path}/output/*/'
                    f'{fmriprep_sub(sub)}{sub[-6:]}'
                    '/frame_wise_displacement_power/*/*'
                ) for sub in sub_list
            ])))
        elif software.lower()=="fmriprep":
            fmriprep_sub_list = [fmriprep_sub(sub) for sub in sub_list]
            return(list(chain.from_iterable([
                [
                f'{run_path}/output/fmriprep/{sub}/func/'
                f'{sub}_task-rest_run-1_desc-confounds_regressors.tsv'
            ] + [
                f'{run_path}/working/fmriprep_wf/'
                f'single_subject_{sub[4:]}_wf/func_preproc_task_rest_run_1_wf/'
                'bold_confounds_wf/fdisp/fd_power_2012.txt'
            ] for sub in fmriprep_sub_list])))
    return([])


if __name__ == "__main__":
    main(sys.argv)
