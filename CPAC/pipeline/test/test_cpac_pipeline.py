"""Tests for cpac_pipeline.py."""

import pytest

from CPAC.pipeline.cpac_pipeline import run_workflow
from CPAC.pipeline.nipype_pipeline_engine.plugins import MultiProcPlugin
from CPAC.utils.configuration import Configuration


@pytest.mark.parametrize("plugin", [MultiProcPlugin(), False, "MultiProc", None])
def test_plugin_param(plugin):
    """We should get an KeyError from our empty `sub_dict`.

    If we pass a non-string to run_workflow, a TypeError should be raised.
    """
    cfg = Configuration()

    with pytest.raises((TypeError, KeyError)) as e:
        exitcode = run_workflow({}, cfg, False, plugin=plugin)
        assert exitcode != 0
    if isinstance(plugin, str) or plugin is None:
        assert e.typename == "KeyError"
    else:
        assert e.typename == "TypeError"
        if isinstance(plugin, MultiProcPlugin):
            assert "MultiProcPlugin" in str(e.value)
        elif isinstance(plugin, bool):
            assert "bool" in str(e.value)
