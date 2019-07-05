import pytest
import math
from typing import Type

from usim import Scope, time, until
from usim.basics import Resources, Capacity
from usim._basics.resource import BaseResources

from ..utility import via_usim


class BaseResourceCase:
    resource_type = None  # type: Type[BaseResources]

    @via_usim
    async def test_misuse(self):
        with pytest.raises(ValueError):
            self.resource_type(a=10, b=-10)
        with pytest.raises(TypeError):
            self.resource_type()
        resources = Capacity(a=10, b=10)
        with pytest.raises(ValueError):
            async with resources.borrow(a=-1, b=-1):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(a=-1):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(b=-1):
                pass

    @via_usim
    async def test_borrow(self):
        resources = Capacity(a=10, b=10)
        async with resources.borrow(a=5, b=5):
            assert True
        async with resources.borrow(a=5):
            assert True
        async with resources.borrow(b=5):
            assert True
        async with resources.borrow(a=7, b=7):
            assert True
        async with resources.borrow(a=10, b=10):
            assert True

    @via_usim
    async def test_nested_borrow(self):
        resources = Capacity(a=10, b=10)
        async with resources.borrow(a=5, b=5):
            async with resources.borrow(a=5, b=5):
                assert True
            async with resources.borrow(a=5):
                assert True
            async with resources.borrow(b=5):
                assert True
        async with resources.borrow(a=7, b=7):
            async with resources.borrow(a=3, b=3):
                assert True
        async with resources.borrow(a=10, b=10):
            assert True

    @via_usim
    async def test_congested(self):
        resources = Capacity(a=10, b=10)

        async def borrow(duration, **amounts):
            async with resources.borrow(**amounts):
                await (time + duration)

        assert time == 0
        async with Scope() as scope:
            scope.do(borrow(10, a=6, b=4))
            scope.do(borrow(10, a=6, b=4))  # not compatible with 1)
            scope.do(borrow(10, a=4, b=6))  # compatible with 1) and 2)
        assert time == 20

    @via_usim
    async def test_release(self):
        """Release resources from cancelled tasks"""
        resources = Capacity(a=10, b=10)

        async def block(**amounts):
            async with resources.borrow(**amounts):
                await (time + math.inf)

        assert time == 0
        async with Scope() as scope:
            task_a = scope.do(block(a=4, b=4))
            task_b = scope.do(block(a=4, b=4))
            await (time + 10)
            task_a.cancel()
            task_b.__close__()
        async with resources.borrow(a=10, b=10):
            assert time == 10


class TestCapacity(BaseResourceCase):
    resource_type = Capacity

    @via_usim
    async def test_borrow_exceed(self):
        resources = Capacity(a=10, b=10)
        with pytest.raises(ValueError):
            async with resources.borrow(a=11, b=11):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(a=11, b=10):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(a=10, b=11):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(a=11):
                pass
        with pytest.raises(ValueError):
            async with resources.borrow(b=11):
                pass


class TestResources(BaseResourceCase):
    resource_type = Resources

    @via_usim
    async def test_increase(self):
        resources = Resources(a=10, b=10)
        async with resources.borrow(a=10, b=10):
            await resources.increase(a=10, b=10)
            async with resources.borrow(a=10, b=10):
                await resources.increase(a=20, b=20)
                async with resources.borrow(a=20, b=20):
                    assert True
        async with resources.borrow(a=40, b=40):
            assert True

    @via_usim
    async def test_increase_misuse(self):
        resources = Resources(a=10, b=10)
        with pytest.raises(ValueError):
            await resources.increase(a=-1, b=-1)
        with pytest.raises(ValueError):
            await resources.increase(a=-1)
        with pytest.raises(ValueError):
            await resources.increase(b=-1)

    @via_usim
    async def test_decrease(self):
        resources = Resources(a=40, b=40)
        async with resources.borrow(a=20, b=20):
            await resources.decrease(a=10, b=10)
            async with until(time == 10):
                async with resources.borrow(a=20, b=20):
                    assert False
            assert time == 10
        async with resources.borrow(a=30, b=30):
            assert True
        async with until(time == 20):
            async with resources.borrow(a=40, b=40):
                assert False
        assert time == 20

    @via_usim
    async def test_decrease_misuse(self):
        resources = Resources(a=10, b=10)
        with pytest.raises(ValueError):
            await resources.decrease(a=-1, b=-1)
        with pytest.raises(ValueError):
            await resources.decrease(a=-1)
        with pytest.raises(ValueError):
            await resources.decrease(b=-1)
        # decrease below zero
        with pytest.raises(ValueError):
            await resources.decrease(a=20, b=20)

    @via_usim
    async def test_set(self):
        resources = Resources(a=10, b=10)
        await resources.set(a=20, b=20)
        async with resources.borrow(a=20, b=20):
            assert True
        await resources.set(a=30)
        async with resources.borrow(a=30, b=20):
            assert True
        await resources.set(b=30)
        async with resources.borrow(a=30, b=30):
            assert True

    @via_usim
    async def test_set_misuse(self):
        resources = Resources(a=10, b=10)
        with pytest.raises(ValueError):
            await resources.set(a=-1, b=-1)
        with pytest.raises(ValueError):
            await resources.set(a=-1)
        with pytest.raises(ValueError):
            await resources.set(b=-1)
