from threading import Thread
import asyncio
import random
from functools import reduce
import threading
from infinity4py import INFINITY
from .utils import String
import math
import datetime
from datetime import datetime as dt
from typing import Optional, Dict
import multiprocessing
import time

class AioCacheBucket():
    """通过threading.Thread运行独立的事件循环来保证其他协程的持续运行.\n
    """
    LocalLoop: asyncio.BaseEventLoop
    ScavengerThread: Thread
    Body: Optional[Dict] = None
    Expire_Datas = None
    LibraryLock: threading.RLock
    DefaultExpireDelta: Optional[Dict] = {}
    ScavengerExitSignal: bool = False
    ScavengerLock: threading.Lock

    def isExpired(self, key):
        """过期返回True, 没有返回False"""
        if key not in self.Expire_Datas:
            raise ValueError(f"{key} has not setted.")

        if self.Expire_Datas[key]["date"] is INFINITY:
            return False

        return self.Expire_Datas[key]["date"] < dt.now()

    def close_scavenger(self):
        self.ScavengerExitSignal = True
        while self.ScavengerLock.locked():
            pass
        else:
            # 核心实现: 使用call_soon_threadsafe
            self.LocalLoop.call_soon_threadsafe(self.LocalLoop.stop)
            self.ScavengerThread.join()

    async def scavenger(self):
        with self.ScavengerLock:
            while True:
                if self.ScavengerExitSignal:
                    break
                await asyncio.sleep(2)
                # print(len(self.Body), end=" ")
                # sys.stdout.flush()

                data_num = len(self.getlib())
                if data_num == 0:
                    continue
                original_keys = list((self.getlib()).keys())
                with self.LibraryLock:
                    result = random.choices(range(len(self.Expire_Datas)), k=math.ceil(data_num / 20))
                    result = reduce(lambda x, y: x if y in x else x + [y], [[], ] + result)
                    if result:
                        for i in [i for i in result if i < data_num]:
                            key = original_keys[i]
                            if self.isExpired(key):
                                del self.Expire_Datas[key]
                                del self.Body[key]

    def count(self):
        with self.LibraryLock:
            return len(self.Body)

    def count_expire_datas(self):
        with self.LibraryLock:
            return len(self.Expire_Datas)

    def delete(self, key):
        with self.LibraryLock:
            del self.Expire_Datas[key]
            del self.Body[key]

    def delete_nowait(self, key):
        del self.Expire_Datas[key]
        del self.Body[key]

    def get(self, key, default=None):
        try:
            if self.isExpired(key):  # 如果在但是过期了
                self.delete(key)
                return default
        except ValueError:  # 不在
            return default
        with self.LibraryLock:
            return self.Body[key]

    def getlib(self):
        with self.LibraryLock:
            return self.Body.copy()

    def set(self, key, value, date=INFINITY):
        """可指定日期, 到时key无效."""
        with self.LibraryLock:
            self.Body[key] = value
            self.Expire_Datas[key] = {"date": date}

    def setByTimedelta(self, key, value, delta={}):
        """通过timedelta实现日期偏移计算"""
        with self.LibraryLock:
            if not delta and self.DefaultExpireDelta:
                delta = self.DefaultExpireDelta
            offset = datetime.timedelta(**delta)
            if offset.total_seconds() == 0:
                self.set(key, value)
            else:
                self.set(key, value, dt.now() + offset)

    def keys(self):
        return self.Body.keys()

    async def has(self, key):
        r = String()
        return (self.get(key, r)) != r

    def __next__(self):
        yield from self.Body.keys()

    def __init__(self, scavenger=True, DefaultExpireDelta={}, LibraryLock=None):
        if scavenger:
            self.LocalLoop = asyncio.new_event_loop()

            def loop_runfunc(loop, coro):
                asyncio.set_event_loop(loop)
                loop.create_task(coro)
                loop.run_forever()

            self.ScavengerThread = Thread(target=loop_runfunc, args=(self.LocalLoop, self.scavenger()))
            self.ScavengerThread.start()

        self.DefaultExpireDelta = DefaultExpireDelta

        # 设置锁
        self.LibraryLock = LibraryLock or threading.RLock()
        self.ScavengerLock = threading.Lock()

        self.Body = {}
        self.Expire_Datas = {}

class AioMultiCacheBucket:
    """AioCacheBucket集群管理.
    """
    BucketsLocks: Dict[str, asyncio.Lock] = {}
    Buckets: Dict[str, AioCacheBucket] = {}
    LocalLoop: asyncio.BaseEventLoop
    ScavengerQueue = None
    ScavengerExitSignal = False
    ScavengerThread: Thread
    ScavengerLock: asyncio.Semaphore
    SemaphoreNumber: int

    def close_scavenger(self):
        self.ScavengerExitSignal = True
        while self.ScavengerLock._value != self.SemaphoreNumber:
            pass
        else:
            # 核心实现: 使用call_soon_threadsafe
            self.LocalLoop.call_soon_threadsafe(self.LocalLoop.stop)
            self.ScavengerThread.join()

    async def scavenger_producer(self, pid):
        async with self.ScavengerLock:
            while True:
                await asyncio.sleep(2)
                bucket = None
                bucket_key = None
                lock = None
                lockable = False
                while not lockable:
                    await asyncio.sleep(0.5)
                    if self.ScavengerExitSignal:
                        break

                    if not list(self.Buckets.keys()):
                        continue

                    bucket_key = random.choice(list(self.Buckets.keys()))
                    lock = self.ScavengerLocks[bucket_key]
                    if not self.Buckets[bucket_key].Expire_Datas:  # 跳过无KEY档案
                        continue

                    if not lock.locked():  # 如果没有锁住, 则跳出循环并开始清理.
                        lockable = True
                        bucket = self.Buckets[bucket_key]
                        break

                if self.ScavengerExitSignal:
                    break
                async with lock:
                    bucket_lib: dict = bucket.getlib()
                    lib_num = len(bucket_lib)
                    lib_keys = list(bucket_lib.keys())
                    result = random.choices(range(len(bucket.Expire_Datas)), k=math.ceil(lib_num / 20))
                    result = reduce(lambda x, y: x if y in x else x + [y], [[], ] + result)
                    # print([i for i in result if bucket.isExpired(lib_keys[i])])
                    if result:
                        # print(choiced_key, lib_num, [i for i in result if i > lib_num])
                        for i in [i for i in result if i < lib_num]:
                            db_key = lib_keys[i]
                            if bucket.isExpired(db_key):
                                with self.BucketsLocks[bucket_key]:
                                    bucket.delete(db_key)
        return

    def __init__(self, buckets_options: dict, scavenger_number=3):
        # 创建事件循环
        self.LocalLoop = asyncio.new_event_loop()
        self.ScavengerLocks = {}

        for key, value in buckets_options.items():
            # 开始根据options创建初始Buckets
            result = {
                "DefaultExpireDelta": value.get("default_expire_delta", {})
            }
            self.ScavengerLocks[key] = asyncio.Lock()
            self.BucketsLocks[key] = threading.RLock()
            self.Buckets[key] = AioCacheBucket(self.RequireApp, **result, scavenger=False, LibraryLock=self.BucketsLocks[key])

        # 构建清道夫
        def loop_runfunc(loop: asyncio.AbstractEventLoop, tasks):
            asyncio.set_event_loop(loop)

            for i in sum(tasks, []):
                loop.create_task(i)

            loop.run_forever()

        self.SemaphoreNumber = scavenger_number
        self.ScavengerLock = asyncio.Semaphore(scavenger_number, loop=self.LocalLoop)
        self.ScavengerThread = Thread(target=loop_runfunc, args=(self.LocalLoop, [
            [self.scavenger_producer(i) for i in range(scavenger_number)]
        ]))
        self.ScavengerThread.start()

        #app.on_event("shutdown")(self.event_shutdown_listener)

    def setup(self, buckets_options: dict):
        for key, value in buckets_options.items():
            # 根据options创建初始Buckets
            result = {
                "DefaultExpireDelta": value.get("default_expire_delta", {})
            }
            self.ScavengerLocks[key] = asyncio.Lock()
            self.BucketsLocks[key] = threading.RLock()
            self.Buckets[key] = AioCacheBucket(**result, scavenger=False, LibraryLock=self.BucketsLocks[key],
            )

    def getBucket(self, bucket_name):
        return self.Buckets.get(bucket_name)
