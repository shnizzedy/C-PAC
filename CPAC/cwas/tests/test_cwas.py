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
"""Test the CWAS pipeline."""

import pytest
import nibabel as nib

from CPAC.pipeline.nipype_pipeline_engine.plugins import MultiProcPlugin
from CPAC.utils.monitoring.custom_logging import getLogger

logger = getLogger("CPAC.cwas.tests")


@pytest.mark.skip(reason="requires RegressionTester")
def test_adhd04():
    """Test CWAS with ADHD04 data."""
    rt = RegressionTester("adhd04", "diagnosis", "diagnosis")
    rt.run()


@pytest.mark.skip(reason="requires RegressionTester")
def test_adhd40():
    """Test CWAS with ADHD40 data."""
    rt = RegressionTester("adhd40", "diagnosis", "diagnosis + age + sex + meanFD")
    rt.run()


@pytest.mark.skip(reason="requires specific local directory")
class RegressionTester(object):
    """Test the CWAS pipeline in Python and R, and compare the results.

    tmp = RegressionTester('adhd04', 'diagnosis', 'diagnosis')
    tmp.run().
    """

    def __init__(
        self,
        name,
        factor,
        formula,
        base="/home2/data/Projects/CPAC_Regression_Test/2013-05-30_cwas",
    ):
        super(RegressionTester, self).__init__()
        self.base = base
        self.name = name
        self.factor = factor
        self.formula = formula

    def run(self):
        """Run the CWAS pipeline in Python and R, and compare the results."""
        logger.info("Python-Based CWAS")
        self.run_cwas()

        logger.info("R-Based CWAS")
        self.run_connectir()

        logger.info("Compare Python and R")
        self.compare_py_vs_r()

    def run_cwas(self):
        """Run the CWAS pipeline in Python."""
        import os

        os.chdir("%s/C-PAC" % self.base)

        from os import path as op
        import time

        import numpy as np

        from CPAC.cwas import create_cwas

        ###
        # Paths and Other Inputs
        # - ideally this section can be changed with the rest staying the same
        #   however, we aren't there yet
        ###

        # File with initial grey matter mask
        roi_file = op.join(self.base, "rois/grey_matter_4mm.nii.gz")

        # File with list of subject functionals
        sfile = op.join(self.base, "configs", "%s_funcpaths_4mm.txt" % self.name)

        # File with regressors
        rfile = op.join(self.base, "configs", "%s_regressors.txt" % self.name)

        # Column(s) of interest in regressors
        cols = [1]

        # Number of permutations
        nperms = 1000

        ###
        # Setup
        ###

        # Read in list of subject functionals
        with open(sfile) as _f:
            subjects_list = [l.strip().strip('"') for l in _f.readlines()]  # noqa: E741

        # Read in design/regressor file
        regressors = np.loadtxt(rfile)

        # Setup the inputs
        c = create_cwas()
        c.inputs.inputspec.roi = roi_file
        c.inputs.inputspec.subjects = subjects_list
        c.inputs.inputspec.cols = cols
        c.inputs.inputspec.regressor = regressors
        c.inputs.inputspec.f_samples = nperms
        c.inputs.inputspec.parallel_nodes = 4
        # c.base_dir = op.join(obase, 'results_fs%i_pn%i' % \
        #                (c.inputs.inputspec.f_samples, c.inputs.inputspec.parallel_nodes))  # pylint: disable=line-too-long
        c.base_dir = op.join(self.base, "results_%s.py" % self.name)

        # export MKL_NUM_THREADS=X # in command line
        # import mkl
        # mkl.set_num_threads(X)

        # try:
        #     import mkl
        #     mkl.set_num_threads(nthreads)
        # except ImportError:
        #     pass

        # Run it!
        start = time.clock()
        plugin_args = {"n_procs": 4}
        c.run(plugin=MultiProcPlugin(plugin_args), plugin_args=plugin_args)
        end = time.clock()
        logger.info("time: %.2gs", end - start)

    def run_connectir(self):
        """Distances and MDMR with connectir.

        This should be run after run_cwas().
        """
        import os
        import time

        start = time.clock()

        logger.info("Subject Distances")
        cmd = (
            "connectir_subdist.R --infuncs1 %(basedir)s/configs/"
            "%(outbase)s_funcpaths_4mm.txt --brainmask1 %(basedir)s/"
            "results_%(outbase)s.py/cwas/joint_mask/joint_mask.nii.gz "
            "--bg %(basedir)s/rois/standard_4mm.nii.gz --memlimit 12 "
            "--forks 1 --threads 12 %(basedir)s/results_%(outbase)s.r"
            % {"basedir": self.base, "outbase": self.name}
        )
        logger.info("RUNNING: %s", cmd)
        os.system(cmd)

        logger.info("MDMR")
        cmd = (
            "connectir_mdmr.R --indir %(basedir)s/results_%(outbase)s.r "
            "--formula '%(formula)s' --model "
            "%(basedir)s/configs/%(outbase)s_model.csv --permutations "
            "%(nperms)s --factors2perm '%(factor)s' --save-perms "
            "--memlimit 12 --forks 1 --threads 12 %(factor)s.mdmr"
            % {
                "basedir": self.base,
                "outbase": self.name,
                "formula": self.formula,
                "factor": self.factor,
                "nperms": 1000,
            }
        )
        logger.info("RUNNING: %s", cmd)
        os.system(cmd)

        end = time.clock()
        logger.info("time: %.2gs", end - start)

    @pytest.mark.skip(reason="No R installation in C-PAC image")
    def compare_py_vs_r(self):
        """Compare the output from the CPAC python vs the R connectir."""
        import os

        os.chdir("%s/C-PAC" % self.base)

        from os import path as op

        import numpy as np
        from rpy2 import robjects
        from rpy2.robjects.numpy2ri import numpy2ri
        from rpy2.robjects.packages import importr
        import nibabel as nib

        robjects.conversion.py2ri = numpy2ri

        from hamcrest import assert_that

        ###
        # Paths and Other Inputs
        # - ideally this section can be changed with the rest staying the same
        #   however, we aren't there yet
        ###

        mask_file = op.join(
            self.base,
            "results_%s.py" % self.name,
            "cwas",
            "joint_mask",
            "joint_mask.nii.gz",
        )

        pybase = op.join(self.base, "results_%s.py" % self.name, "cwas", "cwas_volumes")
        py_fs_file = op.join(pybase, "pseudo_F_volume.nii.gz")
        py_ps_file = op.join(pybase, "p_significance_volume.nii.gz")

        sdir = op.join(self.base, "results_%s.r" % self.name)
        conv_file = op.join(sdir, "mask_r2py.nii.gz")
        rbase = op.join(sdir, "%s.mdmr" % self.factor)
        r_fs_file = op.join(rbase, "fperms_%s.desc" % self.factor)
        r_ps_file = op.join(rbase, "pvals.desc")

        ###
        # Get regressors and represent as hat matrices
        ###

        from pandas import read_csv

        from CPAC.cwas.hats import hatify

        x = np.loadtxt(op.join(self.base, "configs", "%s_regressors.txt" % self.name))
        py_hat = hatify(x)

        y = read_csv(op.join(rbase, "model_evs.txt"))
        r_hat = hatify(y.ix[:, 1:])

        ###
        # Create R=>Py Indices
        ###

        mfile = conv_file
        inds_r2py = nib.load(mfile).get_fdata().astype("int")
        inds_r2py = inds_r2py[inds_r2py.nonzero()] - 1

        ###
        # Read in data
        ###

        mask = nib.load(mask_file).get_fdata().nonzero()

        py_fs = nib.load(py_fs_file).get_fdata()[mask]
        py_ps = nib.load(py_ps_file).get_fdata()[mask]

        importr("bigmemory")
        r_fs = np.array(robjects.r("attach.big.matrix('%s')[1,]" % r_fs_file))
        r_ps = np.array(robjects.r("as.matrix(attach.big.matrix('%s'))" % r_ps_file))

        ###
        # Compare
        ###

        comp = np.allclose(py_hat, r_hat)
        assert_that(comp, "regressors as hat matrices")

        comp = np.corrcoef(py_fs, r_fs[inds_r2py])[0, 1] > 0.99  # noqa: PLR2004
        assert_that(comp, "Fstats similarity")

        comp = np.corrcoef(py_ps, r_ps[inds_r2py])[0, 1] > 0.99  # noqa: PLR2004
        assert_that(comp, "p-values similarity ")

        comp = abs(py_fs - r_fs[inds_r2py]).mean() < 0.01  # noqa: PLR2004
        assert_that(comp, "Fstats difference")

        comp = abs(py_ps - r_ps[inds_r2py]).mean() < 0.05  # noqa: PLR2004
        assert_that(comp, "p-values difference")

        logger.info("tests were all good")


def test_cwas_connectir():
    # add the code to run the same cwas with connectir
    pass


@pytest.mark.skip(reason="No R installation in C-PAC image")
def test_mdmr_with_connectir_distances():
    """Uses the distances from output of connectir to specifically test the mdmr portion of things."""
    import os

    os.chdir("../C-PAC")

    from os import path as op

    import numpy as np
    from rpy2 import robjects
    from rpy2.robjects.numpy2ri import numpy2ri
    from rpy2.robjects.packages import importr

    from CPAC.cwas.mdmr import mdmr

    robjects.conversion.py2ri = numpy2ri

    importr("bigmemory")
    importr("base")

    sdir = "/home/data/Projects/CPAC_Regression_Test/2013-05-30_cwas/results_adhd04.r"
    sfile = op.join(sdir, "subdist.desc")
    dmats = np.array(robjects.r("as.matrix(attach.big.matrix('%s'))" % sfile))
    np.sqrt(dmats.shape[0])

    rfile = "/home2/data/Projects/CPAC_Regression_Test/2013-05-30_cwas/configs/adhd04_regressors.txt"
    regressors = np.loadtxt(rfile)

    ps, Fs, _, _ = mdmr(dmats[:, :10], regressors, [1], 1000)


@pytest.mark.skip(reason="dmats is undefined ")
def test_distances():
    from os import path as op

    import numpy as np
    from pandas import read_csv

    n = 10

    sdir = "/home/data/Projects/Z_CPAC_Regression_Test/2013-05-30_cwas/results_nki.r"
    mask_file = op.join(sdir, "mask.nii.gz")

    sfile = "/home2/data/Projects/CWAS/share/nki/subinfo/40_Set1_N104/short_compcor_funcpaths_4mm_smoothed.txt"
    subjects_list = [
        l.strip().strip('"')
        for l in open(sfile).readlines()  # noqa: E741
    ]
    subjects_list = subjects_list[:n]
    subjects_file_list = subjects_list

    mask = nib.load(mask_file).get_fdata().astype("bool")
    mask_indices = np.where(mask)

    subjects_data = [
        nib.load(subject_file).get_fdata().astype("float64")[mask_indices].T
        for subject_file in subjects_file_list
    ]
    subjects_data = np.array(subjects_data)

    rfile = "/home2/data/Projects/CWAS/share/nki/subinfo/40_Set1_N104/subject_info_with_iq_and_gcors.csv"
    df = read_csv(rfile)
    np.array(
        [
            np.ones(n),
            df.FSIQ[:n] - df.FSIQ[:n].mean(),
            df.short_meanGcor[:n] - df.short_meanGcor[:n].mean(),
            df.Age[:n] - df.Age[:n].mean(),
            (df.Sex[:n] == "M") * 1,
        ]
    ).T

    # run parts of the subdist code base to get...

    sdir = "/home/data/Projects/Z_CPAC_Regression_Test/2013-05-30_cwas/results_nki.r"
    ffile = op.join(sdir, "iq_meanFD+age+sex.mdmr", "fperms_FSIQ.desc")
    np.array(robjects.r("as.matrix(attach.big.matrix('%s'))" % ffile))
    n = np.sqrt(dmats.shape[0])
