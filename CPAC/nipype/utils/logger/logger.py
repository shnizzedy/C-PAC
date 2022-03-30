"""Module to override Nipype's logger"""
import logging

from nipype.utils.logger import Logging as NipypeLogging

from CPAC.utils.monitoring.config import MOCK_LOGGERS

class Logging(NipypeLogging):
    """Class to override nipype.utils.logger.Logging"""
    def __init__(self, config):
        __doc__ = getattr(NipypeLogging.__init__, '__doc__', '')
        NipypeLogging.__init__(self, config)
        self._callback = logging.getLogger('callback')
        self._verbose_engine = logging.getLogger('engine')
        self._random_seed = logging.getLogger('random')
        self.loggers.update({
            'callback': self._callback,
            'engine': self._verbose_engine,
            'random': self._random_seed,
        })

    __doc__ = getattr(NipypeLogging, '__doc__', '')

    def getLogger(self, name):
        """Method to get a Nipype logger if one exists, falling back on
        a mock logger if one exists, falling back on native loggers.

        Parameters
        ----------
        name : str
            name of the logger to get

        Returns
        -------
        logger : logging.Logger or CPAC.utils.monitoring.MockLogger
            the logger
        """
        if name == "filemanip":
            warn(
                'The "filemanip" logger has been deprecated and replaced by '
                'the "utils" logger as of nipype 1.0'
            )
        print(name)
        print(self.loggers.get(name))
        print(MOCK_LOGGERS.get(name))
        print(logging.getLogger(name))
        if name in self.loggers:
            return self.loggers[name]
        elif name in MOCK_LOGGERS:
            return MOCK_LOGGERS[name]
        return logging.getLogger(name)
