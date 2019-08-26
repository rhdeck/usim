"""
This module defines the exceptions exclusive to the SimPy compatibility layer.
These are used as shutdown signals between the environment and processes.
Note that with the exception of :py:exc:`~usim.py.exceptions.Interrupt`,
all signals should be considered internal and not meant to be handled manually.
"""


class NotEmulatedError(NotImplementedError):
    """An operation of the 'simpy' API is not emulated by the 'usim.py' API"""


class StopSimulation(BaseException):
    """Signal to stop a simulation"""


class SimPyException(Exception):
    """Base case for all exceptions of ``usim.py`` that can safely be handled"""


class StopProcess(SimPyException):
    """
    Signal to stop a process

    .. warning::

        This exceptions exists for historical compatibility only.
        See :py:meth:`usim.py.Environment.exit` for details.
    """
    def __init__(self, value):
        super().__init__(value)
        self.value = value


class Interrupt(SimPyException):
    """Exception used to :py:meth:`~usim.py.events.Process.interrupt` a process"""
    @property
    def cause(self):
        """The ``cause`` passed to :py:meth:`~usim.py.events.Process.interrupt`"""
        return self.args[0]
