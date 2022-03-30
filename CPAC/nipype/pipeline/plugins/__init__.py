"""Import Nipype's pipeline plugins and selectively override"""
from nipype.pipeline import plugins
from nipype.pipeline.plugins import *  # noqa: F401,F403
from CPAC.utils.utils import get_interfaces_to_not_override
# Override LegacyMultiProc
from .legacymultiproc import LegacyMultiProcPlugin  # noqa: F401
# Override MultiProc
from .multiproc import MultiProcPlugin  # noqa: F401

__all__ = get_interfaces_to_not_override(plugins, [
    'LegacyMultiProcPlugin', 'MultiProcPlugin'])
