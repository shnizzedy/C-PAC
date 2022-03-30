'''Module to import Nipype Pipeline engine and override some Classes.
See https://fcp-indi.github.io/docs/developer/nodes
for C-PAC-specific documentation.
See https://nipype.readthedocs.io/en/latest/api/generated/nipype.pipeline.engine.html
for Nipype's documentation.'''  # noqa: E501
from nipype.pipeline import engine as pe
# import everything in nipype.pipeline.engine.__all__
from nipype.pipeline.engine import *  # noqa: F401,F403
from CPAC.utils.utils import get_interfaces_to_not_override
# import our DEFAULT_MEM_GB and override Node, MapNode
from .engine import DEFAULT_MEM_GB, Node, MapNode, UNDEFINED_SIZE, Workflow

__all__ = get_interfaces_to_not_override(pe, [
    'DEFAULT_MEM_GB', 'Node', 'MapNode', 'UNDEFINED_SIZE', 'Workflow'])

del pe
