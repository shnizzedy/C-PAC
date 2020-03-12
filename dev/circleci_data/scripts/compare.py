# coding=utf-8
import glob
import numpy as np
import pandas as pd
import sys

from afni_python.lib_afni1D import Afni1D
from scipy.stats import pearsonr

from defaults import motion_list, regressor_list
from subjects import fmriprep_sub

feature_headers = {
    'GS': {
        'C-PAC': 'GlobalSignalMean0',
        'fmriprep': 'global_signal'
    },
    'CSF': {
        'C-PAC': 'CerebrospinalFluidMean0',
        'fmriprep': 'csf'
    },
    'WM': {
        'C-PAC': 'WhiteMatterMean0',
        'fmriprep': 'white_matter'
    },
    'CompCor': {
        'C-PAC': 'CompCorPC',
        'fmriprep': 'CompCor_comp_cor_0'
    }
}

def main(argv):
    print('🔬 Test ≟.')


def calc_corr(data1, data2):
    """
    Function to calculate Pearson's r between two np.ndarrays or lists

    Parameters
    ----------
    data1: np.ndarray or list

    data2: np.ndarray or list
    """
    if isinstance(data1, np.ndarray) and data1.shape == data2.shape:
        return(pearsonr(data1.flatten(), data2.flatten())[0])
    elif len(data1) == len(data2):
        return(pearsonr(data1, data2)[0])
    else:
        return(float(np.nan))


class Subject_Session_Feature:
    """
    A class for (subject × session) × feature data
    """
    def __init__(self, subject, feature, runs):
        """
        Parameters
        ----------
        subject: str
            (subject × session)

        feature: str

        runs: list of dicts
            [{"software": str, "run_path": str}]
        """
        self.subject = subject
        self.feature = feature
        self.data = [
            self.read_feature(
                self.get_path(
                    subject,
                    feature,
                    runs[0]["run_path"],
                    runs[0]["software"]
                ),
                feature,
                runs[0]["software"]
            ),
            self.read_feature(
                self.get_path(
                    subject,
                    feature,
                    runs[1]["run_path"],
                    runs[1]["software"]
                ),
                feature,
                runs[1]["software"]
            )
        ]

    def get_path(self, subject, feature, run_path, software="C-PAC"):
        """
        Method to find a path to specific outputs

        Parameters
        ----------
        subject: str

        feature: str

        sub_list: list of str

        run_path: str

        software: str

        Returns
        -------
        path: str
        """
        if software.lower() in ["cpac", "c-pac"]:
            if feature in regressor_list:
                paths = glob.glob(
                    f'{run_path}/working/'
                    f'resting_preproc_{fmriprep_sub(subject)}{subject[-6:]}/'
                    'nuisance_0_0/_*/*/build*/*1D'
                )
            elif feature in motion_list:
                # frame wise displacement power
                paths = glob.glob(
                   f'{run_path}/output/*/'
                   f'{fmriprep_sub(subject)}{subject[-6:]}'
                   '/frame_wise_displacement_power/*/*'
                )
        elif software.lower()=="fmriprep":
            fmriprep_subject = fmriprep_sub(subject)
            if feature in regressor_list:
                paths = [
                    f'{run_path}/output/fmriprep/{fmriprep_subject}/func/'
                    f'{fmriprep_subject}_task-rest_run-1'
                    '_desc-confounds_regressors.tsv'
                ]
            elif feature in motion_list:
                paths = [
                    f'{run_path}/working/fmriprep_wf/'
                    f'single_subject_{fmriprep_subject[4:]}_wf/'
                    'func_preproc_task_rest_run_1_wf/'
                    'bold_confounds_wf/fdisp/fd_power_2012.txt'
                ]
        return(paths[0] if len(paths) else None)

    def read_feature(self, file, feature, software="C-PAC"):
        """
        Method to read a feature from a given file

        Parameters
        ----------
        file: str
            path to file

        feature: str

        software: str

        Returns
        -------
        feature: np.ndarray or list or None
        """
        if file is None:
            return(None)
        software = "C-PAC" if software.lower() in [
            "c-pac",
            "cpac"
        ] else software.lower()

        feature_label = feature_headers.get(feature, {}).get(software, '') if (
            "CompCor" not in feature
        ) else f"{feature[:-1]}PC{feature[-1]}" if (
            software=="C-PAC"
        ) else f"{feature[0]}_comp_cor_0{feature[-1]}" if (
            software=="fmriprep"
        ) else ""

        if software=="C-PAC":
            data = Afni1D(file)
            header = data.header[-1] if len(data.header) else ""
            header_list = header.split('\t')
            return(
                data.mat[header_list.index(feature_label)] if (
                    feature_label in header_list
                ) else data.mat[0][1:]
            )

        elif software=="fmriprep":
            if file.endswith('.tsv'):
                data = pd.read_csv(file, sep='\t')
                if feature_label in data.columns:
                    return(data[feature_label])
            elif file.endswith('.txt'):
                with open(file) as f:
                    return([
                        float(x) for x in [x.strip() for x in f.readlines()][1:]
                    ])

        return(None)

class Correlation_Matrix:
    """
    A class for (subject × session) × feature correlation matrices
    """
    def __init__(self, subject_sessions, features, runs):
        """
        Parameters
        ----------
        subject_sessions: list of strings
            ["subject_session", ...]

        features: list of strings
            ["feature", ...]

        runs: list of dicts
            [{"software": str, "run_path": str}]
        """
        self.subjects = subject_sessions
        self.features = features
        self.data = {
            subject: {
                feature: Subject_Session_Feature(
                    subject, feature, runs
                ) for feature in features
            } for subject in subject_sessions
        }
        self.corrs = np.zeros((len(subject_sessions), len(features)))
        self.run_pearsonsr()

    def run_correlation(self, subject, feature, data1, data2):
        """
        A method to fill a cell in a correlation matrix with Pearson's r

        Parameters
        ----------
        subject: int
            subject index

        feature: int
            feature index

        data1: np.ndarray or list

        data2: np.ndarray or list
        """
        corr = calc_corr(data1, data2)
        print(
            f'Running subject: {subject} {feature} '
            f'correlation score: {str(corr)}'
        )
        self.corrs[subject][feature] = round(corr, 3)

    def run_pearsonsr(self):
        for i, subject in enumerate(self.data):
            for j, feature in enumerate(self.data[subject]):
                self.run_correlation(i, j, self.data[subject][feature])

if __name__ == "__main__":
    main(sys.argv)
