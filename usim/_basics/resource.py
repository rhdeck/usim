from typing import TypeVar, Dict, Iterable, Generic, Optional, Callable

from .._core.loop import __LOOP_STATE__
from .tracked import Tracked


T = TypeVar('T')


def _kwarg_validator(name, arguments: Iterable[str]) -> Callable:
    """
    Create a validator for a function taking keyword ``arguments``

    :param name: name to use when reporting a mismatch
    :param arguments: names of arguments the function may receive
    """
    assert arguments
    namespace = {}
    exec("""def %s(*, %s=None):...""" % (
        name,
        '=None, '.join(arguments)
    ), namespace)
    return namespace[name]


class NamedVolume(Dict[str, T]):
    """
    Mapping that supports element-wise operations

    :warning: This is for internal use only.
    """
    def __add__(self, other: 'Dict[str, T]'):
        return self.__class__(
            (key, self[key] + other.get(key, 0))
            for key in self.keys()
        )

    def __sub__(self, other: 'Dict[str, T]'):
        return self.__class__(
            (key, self[key] - other.get(key, 0))
            for key in self.keys()
        )

    def __ge__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] >= value for key, value in other.items())

    def __gt__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] > value for key, value in other.items())

    def __le__(self, other: 'Dict[str, T]') -> bool:
        return all(self[key] <= value for key, value in other.items())


class BorrowedResources(Generic[T]):
    def __init__(self, resources: 'ConservedResources', amounts: Dict[str, T]):
        self._resources = resources
        self._requested = amounts

    async def __aenter__(self):
        await (self._resources.__available__ >= self._requested)
        await self._resources.__remove_resources__(self._requested)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is GeneratorExit:
            # we are killed forcefully and cannot perform async operations
            # dispatch a new activity to release our resources eventually
            __LOOP_STATE__.LOOP.schedule(
                self._resources.__insert_resources__(self._requested)
            )
        else:
            await self._resources.__insert_resources__(self._requested)


class ConservedResources(Generic[T]):
    """
    Fixed supply of named resources which can be temporarily borrowed

    The resources and their maximum capacity are defined
    when the resource supply is created.
    Afterwards, it is only possible to temporarily :py:meth:`borrow`
    resources:

    .. code:: python3

        # create a limited supply of resources
        resources = ConservedResources(cores=8, memory=16000)

        # temporarily remove resources
        async with resources.borrow(cores=2, money=4000):
            await computation

    Individual resources are assumed to be indistinguishable,
    i.e. there is merely an *amount* of each.
    As a result, there is no order imposed for borrowing and returning
    resources.
    Resources are borrowed as soon as there are enough available,
    and they are returned without regard to other borrowings.
    """
    def __init__(self, __zero__: Optional[T] = None, **capacity: T):
        if not capacity:
            raise TypeError(
                '%s requires at least 1 keyword-only argument' % self.__class__.__name__
            )
        __zero__ = __zero__ if __zero__ is not None else\
            type(next(iter(capacity.values())))()  # bare type invocation must be zero
        self._zero = NamedVolume(dict.fromkeys(capacity, __zero__))
        self._capacity = NamedVolume(capacity)
        if not self._capacity > self._zero:
            raise ValueError('capacities must be greater than zero')
        self.__available__ = Tracked(NamedVolume(capacity.copy()))
        self._verify_arguments = _kwarg_validator('borrow', arguments=capacity.keys())

    async def __insert_resources__(self, amounts: Dict[str, T]):
        new_levels = self.__available__.value + NamedVolume(amounts)
        await self.__available__.set(new_levels)

    async def __remove_resources__(self, amounts: Dict[str, T]):
        new_levels = self.__available__.value - NamedVolume(amounts)
        await self.__available__.set(new_levels)

    def borrow(self, **amounts: T) -> BorrowedResources[T]:
        """
        Temporarily borrow resources for a given context

        :param amounts:
        :return:
        """
        self._verify_arguments(**amounts)
        if not self._zero <= amounts:
            raise ValueError('cannot borrow negative amounts')
        if not self._capacity >= amounts:
            raise ValueError('cannot borrow beyond capacity')
        return BorrowedResources(self, amounts)
