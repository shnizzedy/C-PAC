
def combine_inputs_into_list(input1, input2, input3):
    inputs_list = [input1, input2, input3]
    return inputs_list


def seperate_warps_list(warp_list, selection):
    for warp in warp_list:
        if selection in warp:
            selected_warp = warp
    return selected_warp


def hardcoded_reg(anatomical_brain, reference_brain, anatomical_skull,
                  reference_skull):

    regcmd = ["antsRegistration",
              "--collapse-output-transforms", "0",
              "--dimensionality", "3",
              "--initial-moving-transform",
              "[{0},{1},0]".format(reference_brain, anatomical_brain),
              "--interpolation", "Linear",
              "--output", "[transform,transform_Warped.nii.gz]",
              "--transform", "Rigid[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.25]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250x100,1e-08,10]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "8x4x2x1",
              "--use-histogram-matching", "1",
              "--transform", "Affine[0.1]",
              "--metric", "MI[{0},{1},1,32," \
              "Regular,0.25]".format(reference_brain, anatomical_brain),
              "--convergence", "[1000x500x250x100,1e-08,10]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "8x4x2x1",
              "--use-histogram-matching", "1",
              "--transform", "SyN[0.1,3.0,0.0]",
              "--metric", "CC[{0},{1},1,4]".format(reference_skull,
                                                   anatomical_skull),
              "--convergence", "[100x100x70x20,1e-09,15]",
              "--smoothing-sigmas", "3.0x2.0x1.0x0.0",
              "--shrink-factors", "6x4x2x1",
              "--use-histogram-matching", "1",
              "--winsorize-image-intensities", "[0.01,0.99]"]

    try:
        retcode = subprocess.check_output(regcmd)
    except Exception as e:
        raise Exception('[!] ANTS registration did not complete successfully.'
                        '\n\nError details:\n{0}\n{1}\n'.format(e, e.output))

    warp_list = []
    warped_image = None

    files = [f for f in os.listdir('.') if os.path.isfile(f)]

    for f in files:
        if ("transform" in f) and ("Warped" not in f):
            warp_list.append(os.getcwd() + "/" + f)
        if "Warped" in f:
            warped_image = os.getcwd() + "/" + f

    if not warped_image:
        raise Exception("\n\n[!] No registration output file found. ANTS "
                        "registration may not have completed "
                        "successfully.\n\n")

    return warp_list, warped_image


def change_itk_transform_type(input_affine_file):
    """
    this function takes in the affine.txt produced by the c3d_affine_tool
    (which converted an FSL FLIRT affine.mat into the affine.txt)

    it then modifies the 'Transform Type' of this affine.txt so that it is
    compatible with the antsApplyTransforms tool and produces a new affine
    file titled 'updated_affine.txt'
    """

    new_file_lines = []

    with open(input_affine_file) as f:
        for line in f:
            if 'Transform:' in line:
                if 'MatrixOffsetTransformBase_double_3_3' in line:
                    transform_line = 'Transform: AffineTransform_double_3_3\n'
                    new_file_lines.append(transform_line)
            else:
                new_file_lines.append(line)

    updated_affine_file = os.path.join(os.getcwd(), 'updated_affine.txt')

    with open(updated_affine_file, 'wt') as f:
        for line in new_file_lines:
            f.write(line)

    return updated_affine_file
