import pytest

from usim import time, Lock, Scope

from ..utility import via_usim


class TestLock:
    @via_usim
    async def test_misuse(self):
        with pytest.raises(AttributeError):
            with Lock():
                ...

    @via_usim
    async def test_acquire_single(self):
        lock = Lock()
        async with lock:
            await (time + 5)
        assert time == 5

    @via_usim
    async def test_acquire_reentry(self):
        lock = Lock()
        async with lock:
            async with lock:
                async with lock:
                    await (time + 5)
        async with lock, lock, lock:
            await (time + 5)
        assert time == 10

    @via_usim
    async def test_acquire_multiple(self):
        lock_a, lock_b, lock_c = Lock(), Lock(), Lock()
        async with lock_a:
            async with lock_b:
                async with lock_c:
                    await (time + 5)
        async with lock_a, lock_b, lock_c:
            await (time + 5)
        assert time == 10

    @via_usim
    async def test_contended(self):
        lock = Lock()

        async def mutext_sleep(delay):
            async with lock:
                await (time + delay)
        async with Scope() as scope:
            scope.do(mutext_sleep(5))
            scope.do(mutext_sleep(5))
            scope.do(mutext_sleep(10))
        assert time == 20

    @via_usim
    async def test_available(self):
        lock = Lock()

        async def hold_lock():
            async with lock:
                await (time + 10)
        assert lock.available
        async with lock:
            assert lock.available
        async with Scope() as scope:
            scope.do(hold_lock())
            await (time + 5)
            assert not lock.available
        assert lock.available
