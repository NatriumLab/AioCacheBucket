## AioCacheBucket
这并非一个使用类似 `result = await cache.get("xxxxxx")` 的所谓" IO密集型" 应用.  
AioCacheBucket 是使用了 `asyncio` 模块的多种技巧实现的一个Python缓存模块.  

### Example

``` python
# 单实例:
from AioCacheBucket import AioCacheBucket

bucket = AioCacheBucket()
bucket.set("message", "Hello World!")
print(bucket.get("message"))

# 多实例:
from AioCacheBucket import AioMultiCacheBucket

multibuckets = AioMultiCacheBucket({})
multibuckets.setup({
    "hello-world": {}
})
hello_world_bucket: AioCacheBucket = multibuckets.getBucket("hello-world")
hello_world_bucket.set("message".encode("utf-8"), "sth.") # 除了键必须是hashable, 值则可以是任何PyObject.

# 即时过期机制:
from datetime import datetime as dt, timedelta as td
bucket.set("ttl-test", "sth", date=dt.now() + td(seconds=10))
# ttl-test这个键会在10秒后被删除. ACB会在你使用get方法时检查键的过期情况, 并根据其进行一定处理.

multibuckets.close_scavenger() 
# 在执行完所有代码后, 请先通过该方法停止内置的清道夫线程, 否则可能导致假死
# 在这之后我们可能会使用atexit等模块实现自动执行该方法.
```

ACB主要将 `asyncio` 模块用于清道夫线程的实现, 对于用户接口尽量做到简单方便.

强烈推荐在Python 3.7.10及以上版本使用该模块.