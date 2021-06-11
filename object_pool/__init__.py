import time
import typing
import nb_log
from queue import Queue
import threading


class ObjectPool(nb_log.LoggerMixin, nb_log.LoggerLevelSetterMixin):
    def __init__(self, object_type, num=10):
        self.num = num
        self.queue = self._queue = Queue(num)
        self._create_object_fun = None  # type: typing.Callable
        self._lock = threading.Lock()
        self._is_using_num = 0
        self.object_type = object_type
        self.logger.setLevel(20)

    def specify_create_object_fun(self, fun):
        self._create_object_fun = fun

    def borrow_a_object(self, block, timeout):
        with self._lock:
            self._is_using_num += 1
        try:
            if self._queue.qsize() == 0 and self._is_using_num <= self.num:
                if self._create_object_fun is None or not isinstance(self._create_object_fun, typing.Callable):
                    self.logger.critical(f'必须使用 specify_create_object_fun方法设置一个创建对象的函数')
                    raise ValueError('必须使用 specify_create_object_fun方法设置一个创建对象的函数')
                t1 = time.perf_counter()
                obj = self._create_object_fun()
                self.logger.info(f'创建对象 {obj} ,耗时 {time.perf_counter() - t1}')
                if not isinstance(obj, self.object_type):
                    raise ValueError(f' {self._create_object_fun} 函数必须return返回一个 {self.object_type} 类型的对象')
                self._queue.put(obj)
                # print(self._queue.qsize())
            obj = self._queue.get(block, timeout)
            self.logger.warning(f'获取对象 {obj}')
            return obj
        except Exception as e:
            self.logger.critical(e, exc_info=True)
            with self._lock:
                self._is_using_num -= 1

    def back_a_object(self, obj):
        self._queue.put(obj)
        self.logger.debug(f'归还对象 {obj}')
        with self._lock:
            self._is_using_num -= 1


class ObjectContext(nb_log.LoggerMixin):
    def __init__(self, pool: ObjectPool, block=True, timeout=None):
        self._pool = pool
        self._block = block
        self._timeout = timeout
        self.obj = None

    def __enter__(self):
        self.obj = self._pool.borrow_a_object(self._block, self._timeout)
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.logger.info(self.obj)
        if self.obj is not None:
            self._pool.back_a_object(self.obj, )
        self.obj = None

    def __del__(self):
        # self.logger.warning(self.obj)
        if self.obj is not None:
            self._pool.back_a_object(self.obj)
        self.obj = None
