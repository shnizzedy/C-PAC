import os, sys, getopt, glob
import numpy as np
import pandas as pd 
import nibabel as nb
import lib_afni1D as LAD
import scipy.io as sio
from scipy.stats import pearsonr
from nipype.interfaces import afni, fsl

def main(argv):
    options = "hc:f:"
    long_options = ["help", "cpac_path", "fmriprep_path"]

    try:
        opts, _ = getopt.getopt(argv, options, long_options)
    except getopt.error as err:
        print str(err)
        print 'pipeline_comp_regressor.py -c <cpac path> -f <fmriprep path>' 
        sys.exit(2) 

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print '-c <cpac path> -f <fmriprep path>'
            sys.exit() 
        elif opt in ("-c", "--cpac_path"):
            cpac_path = arg
        elif opt in ("-f", "--fmriprep_path"): 
            fmriprep_path = arg  
    
    sub_list = range(25427,25457)
    ses_list = ['a']
    regressor_list = ['CSF', 'WM', 'GS', 'tCompCor0', 'aCompCor0', 'aCompCor1', 'aCompCor2', 'aCompCor3', 'aCompCor4']
    movement_list = ['FD']
    var_list = regressor_list + movement_list
    
    corrs = np.zeros((len(sub_list), len(var_list)))

    for num_sub, sub in enumerate(sub_list):

        sub = '00'+str(sub)

        for num_ses, ses in enumerate(ses_list):
        
            cpac_path_list = [glob.glob(cpac_path + '/working/resting_preproc_sub-' + sub + ses + '_ses-1/nuisance_0_0/_*/*/build*/*1D')[0]] * 9 + [ # CSF WM GS regressors
                glob.glob(cpac_path + '/output/*/sub-' + sub + ses + '_ses-1/frame_wise_displacement_power/*/*')[0]] # frame wise displacement power 

            fmriprep_path_list = [fmriprep_path + '/output/fmriprep/sub-' + sub + ses + '/func/sub-' + sub + ses + '_task-rest_run-1_desc-confounds_regressors.tsv'] * 9 + [ # regressor
                fmriprep_path + '/working/fmriprep_wf/single_subject_' + sub + ses + '_wf/func_preproc_task_rest_run_1_wf/bold_confounds_wf/fdisp/fd_power_2012.txt'] 
                        
            for num_var, var in enumerate(var_list):
                print str(num_var) + ' ' + var
                cpac_file = cpac_path_list[num_var]
                fmriprep_file = fmriprep_path_list[num_var]

                print cpac_file
                print fmriprep_file
                # read C-PAC files
                if var in regressor_list:
                    data = LAD.Afni1D(cpac_file)
                    header = data.header[-1]
                    header_list = header.split('\t')
                    if var == 'CSF':
                        cpac_data = data.mat[header_list.index('CerebrospinalFluidMean0')]
                    elif var == 'WM':
                        cpac_data = data.mat[header_list.index('WhiteMatterMean0')]
                    elif var == 'GS':
                        cpac_data = data.mat[header_list.index('GlobalSignalMean0')] # find string start with GS
                    elif 'aCompCor' in var:
                        cpac_data = data.mat[header_list.index(var[:-1]+'PC'+var[-1])]  
                    elif 'tCompCor' in var:
                        cpac_data = data.mat[header_list.index(var[:-1]+'PC'+var[-1])]                        
                elif var in movement_list:
                    c = LAD.Afni1D(cpac_file)
                    cpac_data = c.mat
                    cpac_data = cpac_data[0][1:] # cpac and fmriprep dims are different

                # read fmriprep files
                if '.tsv' in fmriprep_file:
                    data = pd.read_csv(fmriprep_file, sep='\t')
                    if var == 'CSF':
                        fmriprep_data = data['csf']
                    elif var == 'WM':
                        fmriprep_data = data['white_matter']
                    elif var == 'GS':
                        fmriprep_data = data['global_signal']
                    elif 'CompCor' in var:
                        fmriprep_data = data[var[0]+'_comp_cor_0'+var[-1]]
                elif '.txt' in fmriprep_file:
                    with open(fmriprep_file) as f:
                        fmriprep_data = f.readlines()
                    fmriprep_data = [x.strip() for x in fmriprep_data]
                    fmriprep_data = fmriprep_data[1:]
                    fmriprep_data = [float(x) for x in fmriprep_data]

                if isinstance(cpac_data, np.ndarray) and cpac_data.shape == fmriprep_data.shape:
                    corr, _ = pearsonr(cpac_data.flatten(), fmriprep_data.flatten())
                elif len(cpac_data) == len(fmriprep_data):
                    corr, _ = pearsonr(cpac_data, fmriprep_data)
                else:
                    corrs[num_sub][num_var] = float('nan')
                
                print 'Running subject: ' + sub + ' ' + var + ' correlation score: ' + str(corr)
                corrs[num_sub][num_var] = round(corr, 3)

    sio.savemat('corrs.mat', {'corrs':corrs})

if __name__ == "__main__":
   main(sys.argv[1:])    
