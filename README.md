## pip install object_pool

<pre style="color: darkgreen;font-size: medium">
python 通用对象池，socket连接池、mysql连接池归根结底都是对象池。
mysql连接池就是pymsql.Connection类型的对象池，一切皆对象。
只是那些很常用的功能的包都有相关的池库，池都是为他们特定的功能定制服务的，不够通用。

编码中很多创建代价大的对象（耗时耗cpu），但是他们的核心操作方法只能是被一个线程占用。

例如mysql，你用同一个conn在不同线程同时去高并发去执行插入修改删除操作就会报错，而且就算包不自带报错，
带事务的即使不报错在多线程也容易混乱，例如线程1要吧conn roallback，线程2要commit，conn中的事务到底听谁的。
解决类似这种抓狂的场景，如果不想再函数内部频繁创建和摧毁，那么就要使用池化思想。

</pre>

```

编码中有时候需要使用一种创建代价很大的对象，而且这个对象不能被多线程同时调用他的操作方法，

比如mysql连接池，socket连接池。
很多这样的例子例典型如mysql的插入，如果多线程高并发同时操作同一个全局connection去插入，很快就会报错了。
那么你可能会为了解决这个问题的方式有如下：

1.你可能这么想，操作mysql的那个函数里面每一次都临时创建mysql连接，函数的末尾关闭coonection，
  这样频繁创建和摧毁连接，无论是服务端还是客户端开销cpu和io高出很多。

2.或者不使用方案1，你是多线程的函数里面用一个全局connection，但是每一个操作mysql的地方都加一个线程锁，
  使得不可能线程1和线程2同时去操作这个connction执行插入，如果假设插入耗时1秒，那么100线程插入1000次要1000秒。

正确的做法是使用mysql连接池库。如果设置开启的连接池中的数量是大于100，100线程插入1000次只需要10秒，节省时间100倍。
mysql连接池已经有知名的连接池包了。如果没有大佬给我们开发mysql连接池库或者一个小众的需求还没有大神针对这个耗时对象开发连接池。
那么可以使用 ObjectPool 实现对象池，连接池就是对象池的一种子集，connection就是pymysql.Connection类型的对象，连接也是对象。


```

## 常问问题回答

### 1 对象池是线程安全的吗？

```
这个问题牛头不对马嘴  ，对象池就是为多线程或者并发而生的。
你想一下，如果你的操作只有一个主线程，那直接用一个对象一直用就是了，反正不会遇到多线程要使用同一个对象。

你花脑袋想想，如果你的代码是主线程单线程的，你有必要用dbutils来搞mysql连接池吗。
直接用pymysql的conn不是更简单更香吗。

任何叫池的东西都是为并发而生的，如果不能多线程安全，那存在的意义目的何在？

```

## 测试代码

tests_object_pool/test_mock_spend_time_object.py

```python
from object_pool import ObjectPool, ObjectContext
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import threading
import time


class MockSpendTimeObject:

    def __init__(self, ):
        time.sleep(0.5)  # 模拟创建对象耗时

        sum = 0  # 模拟创建对象耗费cpu
        for i in range(10000 * 100):
            sum += i

        self._lock = threading.Lock()

    def do_sth(self, x):
        with self._lock:
            time.sleep(0.1)
            print(f'打印 {x} 。  假设做某事同一个object只能同时被一个线程调用此方法，是排他的')


pool = ObjectPool(object_type=MockSpendTimeObject, num=40).set_log_level(10)
# 这里可以指定为一个创建对象的函数对象，由于创建此对象比较简单就用lamada了。
pool.specify_create_object_fun(lambda: MockSpendTimeObject())  


def use_object_pool_run(y):
    """ 第1种 使用对象池是正解"""
    with ObjectContext(pool) as mock_obj:
        mock_obj.do_sth(y)


def create_object_every_times_for_run(y):
    """第2种 多线程函数内部每次都采用临时创建对象，创建对象代价大，导致总耗时很长"""
    mock_obj = MockSpendTimeObject()
    mock_obj.do_sth(y)


global_mock_obj = MockSpendTimeObject()


def use_globle_object_for_run(y):
    """
    第3种 ，多线程中，使用全局唯一对象。少了创建对象的时间，但是操作是独占时间排他的，这种速度是最差的。
    """
    global_mock_obj.do_sth(y)


if __name__ == '__main__':
    t1 = time.perf_counter()
    threadpool = BoundedThreadPoolExecutor(50)

    for i in range(1000):  # 这里随着函数的调用次数越多，对象池优势越明显。假设是运行10万次，三者耗时差距会更大。
        # 这里演示三种调用，1是多线程里用使用对象池 2是使用多线程函数内部每次临时创建关闭对象 3是多线程函数内部使用全局唯一对象。

        # threadpool.submit(use_object_pool_run, i)  # 6秒完成
        threadpool.submit(create_object_every_times_for_run, i)  # 82秒完成
        # threadpool.submit(use_globle_object_for_run, i)  # 耗时100秒

    threadpool.shutdown()
    print(time.perf_counter() - t1)

``` 

