import fnmatch
import nump
from QPPv0418 import detectqppv
from detectqppv import qpp_wf

def load_config_yml(config_file, individual=False):

    # loads a configuration YAML file
    #
    # input
    #   config_file: full filepath to YAML (.yml) file
    #
    # output
    #   config: Configuration object

    import os
    import yaml
    from CPAC.utils import Configuration

    try:
        config_path = os.path.realpath(config_file)

        with open(config_path,"r") as f:
            config_dict = yaml.load(f)

        config = Configuration(config_dict)

    except Exception as e:
        err = "\n\n[!] CPAC says: Could not load or read the configuration " \
        	  "YAML file:\n%s\nDetails: %s\n\n" % (config_file, e)
        raise Exception(err)

    if individual:
        config.logDirectory = os.path.abspath(config.logDirectory)
        config.workingDirectory = os.path.abspath(config.workingDirectory)
        config.outputDirectory = os.path.abspath(config.outputDirectory)
        config.crashLogDirectory = os.path.abspath(config.crashLogDirectory)

    return config


def load_text_file(filepath, label="file"):

    # loads a text file and returns the lines in a list
    #
    # input
    #   filepath: full filepath to the text file
    #
    # output
    #   lines_list: list of lines from text file

    if not filepath.endswith(".txt"):
        err = "\n\n[!] CPAC says: The %s should be a text file (.txt).\n" \
              "Path provided: %s\n\n" % (label, filepath)
        raise Exception(err)

    try:
        with open(filepath,"r") as f:
            lines_list = f.readlines()
    except Exception as e:
        err = "\n\n[!] CPAC says: Could not load or read the %s:\n%s\n" \
              "Details: %s\n\n" % (label, filepath, e)
        raise Exception(err)

    # get rid of those \n's that love to show up everywhere
    lines_list = [i.rstrip("\n") for i in lines_list]

    return lines_list


def gather_nifti_globs(pipeline_output_folder,resource_list,derivatives=None):
    import os
    import glob
    import pandas as pd
    import pkg_resources as p

    if len(resource_list) == 0:
        err = "\n\n[!] please choose atleast one nusiance stratergy!\n\n"
        raise Exception(err)

    if derivatives is None:

        keys_csv = p.resource_filename('CPAC','resources/cpac_outputs.csv')
        try:
            keys=pd.read_csv(keys_csv)
        except Exception as e:
            err = "\n[!] Could not access or read the cpac_outputs.csv " \
                  "resource file:\n{0}\n\nError details {1}\n".format(keys_csv, e)
            raise Exception(err)
        derivatives = list(keys[keys['Space'] == 'functional'][keys['Functional timeseries'] == 'yes']['Resource'])


    pipeline_output_folder = pipeline_output_folder.rstrip("/")
    #print "\n\nGathering the output file paths from %s..." \
    #% pipeline_output_folder

    search_dir = []
    for derivative_name in derivatives:
        for resource_name in resource_list:
            for resource_name in derivative_name:
                search_dir.append(derivative_name)
    nifti_globs=[]

    for resource_name in search_dir:

        glob_pieces = [pipeline_output_folder, "*", resource_name, "*"]

        glob_query = os.path.join(*glob_pieces)

        found_files = glob.iglob(glob_query)

        exts=['nii','nii.gz']

        still_looking = True
        while still_looking:
            still_looking = False
            for found_file in found_files:

                still_looking = True

                if os.path.isfile(found_file) and any(found_file.endswith('.' + ext) for ext in exts):

                    nifti_globs.append(glob_query)

                    break
            if still_looking:
                glob_query = os.path.join(glob_query, "*")
                found_files = glob.iglob(glob_query)

    if len(nifti_globs) == 0:
        err = "\n\n[!] No output filepaths found in the pipeline output " \
             "directory provided for the derivatives selected!\n\nPipeline " \
             "output directory provided: %s\nDerivatives selected:%s\n\n" \
              % (pipeline_output_folder, resource_list)
        raise Exception(err)

    return nifti_globs,search_dir


def create_output_dict_list(nifti_globs,pipeline_folder,resource_list,search_dir,derivatives=None):
    import os
    import glob
    import itertools
    import pandas as pd
    import pkg_resources as p

    if len(resource_list) == 0:
        err= "\n\n[!] No derivatives selected!\n\n"
        raise Exception(err)
    if derivatives is None:
        keys_csv = p.resource_filename('CPAC', 'resources/cpac_outputs.csv')
        try:
            keys=pd.read_csv(keys_csv)
        except Exception as e:
            err= "\n[!] Could not access or read the cpac_outputs.csv " \
                "resource file:\n{0}\n\nError details {1}\n".format(keys_csv,e)
            raise Exception(err)
    exts=['nii','nii.gz']
    exts = ['.'+ ext.lstrip('.')for ext in exts]
    output_dict_list={}
    for root,_,files in os.walk(pipeline_folder):
        for filename in files:
            filepath=os.path.join(root,filename)

            if not any(fnmatch.fnmatch(filepath,pattern)for pattern in nifti_globs):
                continue
            if not any(filepath.endswith(ext)for ext in exts):
                continue
            relative_filepath=filepath.split(pipeline_folder)[1]
            filepath_pieces=filter(None, relative_filepath.split("/"))
            resource_id = filepath_pieces[1]

            if resource_id not in search_dir:
                continue

            scan_id_string = filepath_pieces[2]
            strat_info = "_".join(filepath_pieces[3:])[:-len(ext)]
            unique_resource_id=(resource_id,strat_info)
            if unique_resource_id not in output_dict_list.keys():

                output_dict_list[unique_resource_id] = []

            unique_id = filepath_pieces[0]

            scan_id = scan_id_string.replace("_scan_", "")
            scan_id = scan_id.replace("_rest", "")

            new_row_dict = {}
            new_row_dict["participant_session_id"] = unique_id
            new_row_dict["participant_id"], new_row_dict["Sessions"] = \
                unique_id.split('_')

            new_row_dict["Scan"] = scan_id
            new_row_dict["Filepath"] = filepath

            print('{0} - {1} - {2}'.format(unique_id, scan_id,
                                           resource_id))
            output_dict_list[unique_resource_id].append(new_row_dict)

        #analysis, grouped either by sessions or scans.
    return output_dict_list

def create_output_df_dict(output_dict_list,inclusion_list):

    import pandas as pd

    output_df_dict={}


    for unique_resource_id in output_dict_list.keys():

        ##This dataframe will give you what is in the C-PAC output directory for individual level analysis outputs##
        new_df = pd.DataFrame(output_dict_list[unique_resource_id])
        col_names = new_df.columns.tolist()

        if inclusion_list:
            #this is for participants only, not scans/sessions/etc
            new_df=new_df[new_df.participant_session_id.isin(inclusion_list)]

        if new_df.empty:
                print("No outputs found for {0} the participants "\
                      "listed in the group manalysis participant list you "\
                      "used. Skipping generating model for this "\
                      "output.".format(unique_resource_id))
                continue

        if unique_resource_id not in output_df_dict.keys():
                output_df_dict[unique_resource_id] = new_df

    return output_df_dict



def gather_outputs(pipeline_folder,resource_list,inclusion_list):



    nifti_globs,search_dir = gather_nifti_globs(pipeline_folder,resource_list,derivatives=None)

    output_dict_list = create_output_dict_list(nifti_globs,pipeline_folder,resource_list,search_dir,derivatives=None)
    # now we have a good dictionary which contains all the filepaths of the files we need to merge later on.
    # Steps after this: 1. This is only a dictionary so let's convert it to a data frame.
    # 2. In the data frame, we're going to only include whatever is in the participant list
    # 3. From the list of included participants, we're going to further prune the output dataframe to only contain the
    # scans included, and/or the sessions included
    # 4. Our final output df will contain, file paths for the .nii files of all the participants that are included in the

    output_df_dict=create_output_df_dict(output_dict_list,inclusion_list)

    return output_df_dict

def prep_inputs(group_config_file):

    import os
    import pandas as pd
    import pkg_resources as p

    keys_csv = p.resource_filename('CPAC','resources/cpac_outputs.csv')
    try:
        keys = pd.read_csv(keys_csv)
    except Exception as e:
        err = "\n[!] Could not access or read the cpac_outputs.csv " \
              "resource file:\n{0}\n\nError details {1}\n".format(keys_csv,e)
        raise Exception(err)

    group_model=load_config_yml(group_config_file)
    pipeline_folder = group_model.pipeline_dir
    #inclusion list function
    if not group_model.participant_list:
        inclusion_list = grab_pipeline_dir_subs(pipeline_folder)
    elif '.' in group_model.participant_list:

        if not os.path.isfile(group_model.participant_list):

            raise Exception('\n[!] C-PAC says: Your participant '
                            'inclusion list is not a valid file!\n\n'
                            'File path: {0}'
                            '\n'.format(group_model.participant_list))
        else:
            inclusion_list = load_text_file(group_model.participant_list,"group-level analysis participant list")

    else:
        inclusion_list = grab_pipeline_dir_subs(pipeline_dir)
    resource_list = ['functional_nuisance_residuals']
    output_df_dict=gather_outputs(pipeline_folder,resource_list,inclusion_list)

    for unique_resource in output_df_dict.keys():


        resource_id = unique_resource[0]

        strat_info=unique_resource[1]
        output_df=output_df_dict[unique_resource]

        #We're going to reduce the size of the output df based on nuisance strat and the
        #participant list that actually is included.
        if not group_model.participant_list:
            inclusion_list = grab_pipeline_dir_subs(pipeline_dir)
            output_df = output_df[output_df["participant_session_id"].isin(inclusion_list)]
        elif os.path.isfile(group_model.participant_list):
            inclusion_list = load_text_file(group_model.participant_list,
                                        "group-level analysis "
                                        "participant list")
            output_df = output_df[output_df["participant_session_id"].isin(inclusion_list)]
        else:
            raise Exception('\nCannot read group-level analysis participant ' \
                        'list.\n')
        if len(output_df) == 0:
            err = "\n\n[!]The output data frame has not been compiled correctly. Please" \
                  "recheck the participants in the participant inclusion list and the" \
                  "pipeline output directory to troubleshoot.\n\n"
            raise Exception(err)
        join_columns = ["participant_id"]

        # We're then going to reduce the Output directory to contain only those scans and or the sessions which are expressed by the user.
        # If the user answers all to the option, then we're obviously not going to do any repeated measures.

        grp_by_sessions = False
        grp_by_scans = False
        grp_by_both = False
        repeated_measures=False
        #multiple sessions, so you're going group by scans
        if len(group_model.qpp_sess_list) > 0:
            grp_by_scans = True
        #Multiple scans so you're going to group by sessions
        if len(group_model.qpp_scan_list) > 0:
            grp_by_sessions = True
        if grp_by_scans or grp_by_sessions:
            repeated_measures=True
        if grp_by_scans and grp_by_sessions:
            grp_by_both=True

        #PSA #both multiple sessions and scans, youre going to do nothing
             #if neither, the output directory will not have any level of grouping, it will be ses1_scan1 --> nuisance strat, etc
        if repeated_measures:
            if grp_by_scans:
                #setting up the output_df for grouping by scans
                #output directory will be scan_1
                #                         scan_2
                new_output_df = op_grp_by_scans(output_df,group_model.qpp_sess_list)
                # drop all the sessions that are not in the sessions list
                new_output_df = new_output_df[new_output_df["Session"].isin(group_model.qpp_sessions_list)]
                join_colums.append("Session")
                # balance the DF
                new_output_df, dropped_parts = balance_df(new_output_df, group_model.qpp_sessions_list, scan_list=None)

            if grp_by_sessions:
                #multilple scans
                #setting up the output_df for grouping by sessions
                new_output_df = op_grp_by_sessions(output_df,group_model.qpp_scan_list,grp_by_scans)

                # drop all the scans that are not in the scan list
                new_output_df = new_output_df[new_output_df["Scan"].isin(group_model.qpp_scan_list)]
                #print(new_output_df)
                join_columns.append("Scan")

                # balance the DF
                sessions_list = None
                scan_list = group_model.qpp_scan_list
                new_output_df, dropped_parts = balance_df(new_output_df,sessions_list,scan_list)


            if grp_by_both:
                new_output_df = new_output_df(new_output_df,group_model.qpp_sessions_list,group_model.qpp_scan_list)

        else:
            for scan_df_tuple in output_df.groupby("Scans"):
                scans = scan_df_tuple[0]
                scan_df=scan_df_tuple[1]
                #if you have multiple sessions
                if 'Sessions' in scan_df:
                    for ses_df_tuple in scan_df.groupby('Sessions'):
                        session = 'ses-{0}'.format(ses_df_tuple[0])
                        ses_df = ses_df_tuple[1]
                        new_output_df=pd.merge(scan_df,ses_df,how='inner',on=['participant_id'])
                #if you don't
                else:
                    session='ses-1'
                    new_output_df = pd.merge(new_output_df,scan_df,how="inner",on=["participant_id"])

        if len(new_output_df) == 0:
            err = '\n\n[!]C-PAC says:Could not find match betterrn the ' \
              'particoants in your pipeline output directory that were ' \
              'included in your analysis, and the particpants in the phenotype ' \
                    'phenotype file provided.\n\n'
            raise Exception(err)

        merge_outfile = out_dir
        merge_file = create_merge_file(new_output_df["Filepath"].tolist(),merge_outfile)
        merge_mask_outfile = '_'.join([model_name, resource_id,
                                       "merged_mask.nii.gz"])
        merge_mask_outfile = os.path.join(model_path, merge_mask_outfile)
        merge_mask = create_merge_mask(merge_file, merge_mask_outfile)

    return merge_file,merge_mask,inclusion_list


def op_grp_by_sessions(output_df,scan_list,grp_by_scans=False):
    import pandas as pd

    #check whether there is an extra sessions column in
    num_partic_cols = 0
    for col_names in output_df.columns:
        if "participant_" in col_names:
            num_partic_cols += 1
    if num_partic_cols > 1 and "Scan" in output_df.columns:
        for part_id in output_df["participant_id"]:
            if "participant_{0}".format(part_id) in output_df.columns:
                continue
            break
        else:
            # if it's already set up properly, then just send the output_df
            # back and bypass all the machinery below
            return output_df

    new_rows = []
    for scan in scan_list:
        sub_op_df = output_df.copy()
        sub_op_df["Scan"] = scan
        new_rows.append(sub_op_df)
    output_df = pd.concat(new_rows)

    if not grp_by_scans:
        # participant IDs new columns
        participant_id_cols = {}
        i = 0

        for participant_unique_id in output_df["participant_id"]:

            part_col = [0] * len(output_df["participant_id"])
            header_title = "participant_%s" % participant_unique_id

            if header_title not in participant_id_cols.keys():
                part_col[i] = 1
                participant_id_cols[header_title] = part_col
            else:
                participant_id_cols[header_title][i] = 1

            i += 1

        for new_col in participant_id_cols.keys():
            output_df[new_col] = participant_id_cols[new_col]

    new_output_df = output_df.astype('object')

    return new_output_df

def op_grp_by_scans(output_df,sessions_list):
    import pandas as pd

    num_partic_cols = 0
    for col_names in output_df.columns:

        if "participant_" in output_df.columns:
            num_partic_cols += 1


    if num_partic_cols > 1 and ("Sessions" in output_df.columns or "Sessions_column_one" in pheno_df.columns):
        for part_id in output_df["participant_id"]:

            if "participant_{0}".format(part_id) in output_df.columns:
                continue
            break
        else:
            # if it's already set up properly, then just send the pheno_df
            # back and bypass all the machinery below
            return output_df
    else:
        # if not an FSL model preset, continue as normal
        new_rows = []
        another_new_row = []

            # grab the ordered sublist before we double the rows
        sublist = output_df['participant_id']

        for session in sessions_list:
            sub_op_df = output_df.copy()
            sub_op_df["Sessions"] = session
            sub_op_df["participant_session_id"] = output_df.participant_id + '_ses-%s' % session
            new_rows.append(sub_op_df)
            another_new_row.append(sub_op_df)
            output_df = pd.concat(new_rows)
            output_df = pd.concat(another_new_row)

    sessions_col = []
    part_ids_col = []

    # participant IDs new columns
    participant_id_cols = {}
    i = 0

    for participant_unique_id in output_df["participant_session_id"]:
        part_col = [0] * len(output_df["participant_session_id"])

        for session in sessions_list:
            session=str(session)
            if session in participant_unique_id.split("_")[1]:
                # print(participant_unique_id)# generate/update sessions categorical column
                part_id = participant_unique_id.split("_")[0]

                part_ids_col.append(str(part_id))
                sessions_col.append(str(session))

                header_title = "participant_%s" % part_id

                # generate/update participant ID column (1's or 0's)
                if header_title not in participant_id_cols.keys():
                    part_col[i] = 1
                    participant_id_cols[header_title] = part_col
                else:
                    participant_id_cols[header_title][i] = 1
        i += 1

    output_df["Sessions"] = sessions_col
    output_df["participant"] = part_ids_col

    # add new participant ID columns
    for sub_id in sublist:
        new_col = 'participant_{0}'.format(sub_id)
        output_df[new_col] = participant_id_cols[new_col]

    output_df = output_df.astype('object')

    return output_df


def balance_df(output_df,sessions_list,scan_list):
    import pandas as pd
    from collections import Counter

    part_ID_count = Counter(output_df["participant_id"])

    if scan_list and sessions_list:
        sessions_x_scans= len(sessions_list)*len(scan_list)
    elif sessions_list:
        sessions_x_scans = len(sessions_list)
    else:
        sessions_x_scans = len(scan_list)
    dropped_parts = []
    for part_ID in part_ID_count.keys():
        if part_ID_count[part_ID] != sessions_x_scans:
            output_df=putput_df[output_df.participant_id != part_ID]
            del output_df["participant_%s" %part_ID]
            dropped_parts.append(part_ID)
    return output_df, dropped_parts

def create_merge_file(list_of_output_files, merged_outfile):
    import subprocess

    merge_string = ["fslmerge", "-t", merged_outfile]
    merge_string = merge_string + list_of_output_files

    try:
        retcode = subprocess.check_output(merge_string)
    except Exception as e:
        err = "\n\n[!] Something went wrong with FSL's fslmerge during the " \
              "creation of the 4D merged file for group analysis.\n\n" \
              "Attempted to create file: %s\n\nLength of list of files to " \
              "merge: %d\n\nError details: %s\n\n" \
              % (merged_outfile, len(list_of_output_files), e)
        raise Exception(err)

    return merged_outfile

def create_merge_mask(merged_file, mask_outfile):

    import subprocess

    mask_string = ["fslmaths", merged_file, "-abs", "-Tmin", "-bin",
                   mask_outfile]

    try:
        retcode = subprocess.check_output(mask_string)
    except Exception as e:
        err = "\n\n[!] Something went wrong with FSL's fslmaths during the " \
              "creation of the merged copefile group mask.\n\nAttempted to " \
              "create file: %s\n\nMerged file: %s\n\nError details: %s\n\n" \
              % (mask_outfile, merged_file, e)
        raise Exception(err)

    return mask_outfile

def run_qpp_group(group_config_file):

    #creating output directory paths

    merge_file,merge_mask,inclusion_list = prep_inputs(group_config_file)
    return merge_file,merge_mask,inclusion_list

def run_qpp(group_config_file):
    group_config_file = '/home/nrajamani/grp/tests_v1/fsl-feat_config_adhd200_test7.yml'
    img, mask, inclusion_list = run_qpp_group(group_config_file)

    group_config_obj = load_yaml(group_config_file)



    pipeline_ID = group_config_obj.pipeline_dir.rstrip('/').split('/')[-1]

    out_dir = os.path.join(group_model.output_dir,
                           'cpac_group_analysis',
                           'CPAC_QPP',
                           '{0}'.format(pipeline_ID),
                           nuisance_strat,  # nuisance strat to initialize
                           session_id,  # initialize
                           scan_or_session_label)  # series or repeated label == same as qpp scan or sessions list)

    wl  = group_config_obj.wl

    nrp = group_config_obj.nrp

    cth = group_config_obj.cth

    n_itr_th = group_config_obj.n_itr_th

    mx_itr = group_config_obj.mx_itr

    nsubj = len(inclusion_list)
    nrn =  group_config_obj.nrn #How many runs have you run each subject by. Please note that this is different from
    #the number of scans or sessions you want to include in the qpp analysis

    qpp_wf(img,mask,wl,nrp,cth,n_itr_th,mx_itr,out_dir,nsubj,nrn)











