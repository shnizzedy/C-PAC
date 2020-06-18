#!/bin/bash
cd code
pip install -r dev/circleci_data/requirements.txt
coverage run --parallel-mode -m pytest --junitxml=test-results/junit-$1-$2.xml --doctest-ignore-import-errors --continue-on-collection-errors --doctest-modules --ignore=CPAC/cwas/tests/test_mdmr_cython.py --ignore=dev/circleci_data/test_install.py dev/circleci_data/test_in_docker --pipeline=$1 --participant_ndx=$2
