import os
import sys

from unittest import mock
sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), f'{os.pardir}/'*3, 'dev', 'docker_data'
)))

import run
# This script is intended to be run in a Docker container via the shell script
# `test_full_run.sh`. Running in other ways may have unexpected results.

def test_run_one_subject(capsys, participant_ndx, pipeline):
    # create the output directory if it doesn't exist yet
    os.makedirs(f'/home/circleci/project/outputs/{pipeline}', exist_ok=True)
    
    # simulate a commandline run within the container
    with mock.patch.object(sys, 'argv', [
        'run', '/home/circleci/project',
        f'/home/circleci/project/outputs/{pipeline}', 'participant',
        '--save_working_dir', '--data_config_file',
        '/test_configs/data-test_4-projects_5-subjects.yml', *([
            '--pipeline_file', '/configs/default_pipeline.yml'
        ] if pipeline == 'default' else [
            '--preconfig', pipeline
        ]), '--n_cpus', '1', '--mem_gb', '12', '--participant_ndx',
        participant_ndx
    ]):
        run.main()
        # capture the output
        captured = capsys.readouterr()
        # check for a successful run
        assert "CPAC run complete" in captured.out