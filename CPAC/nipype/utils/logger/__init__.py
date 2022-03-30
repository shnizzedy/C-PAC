"""Module to override Nipype's logger"""
from nipype.utils import logger as nipype_logger
from nipype.utils.logger import *  # pylint: disable=wildcard-import

from CPAC.utils.utils import get_interfaces_to_not_override
from .logger import Logging

__all__ = get_interfaces_to_not_override(nipype_logger, ['Logging'])
