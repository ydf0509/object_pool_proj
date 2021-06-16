import abc
import queue
import threading
import time
from queue import LifoQueue
import decorator_libs
import nb_log


class ObjectPool(nb_log.LoggerMixin, nb_log.LoggerLevelSetterMixin):
    def __init__(self, object_type, num=10):
        self.num = num
        self.queue = self._queue = LifoQueue(num)
        self._lock = threading.Lock()
        self._is_using_num = 0
        self.object_type = object_type
        self.logger.setLevel(20)
        self._check_and_cleanup_objects()

    @decorator_libs.keep_circulating(10, block=False, daemon=True)
    def _check_and_cleanup_objects(self):
        with self._lock:
            while 1:
                try:
                    obj = self._queue.get_nowait()
                except queue.Empty:
                    break
                else:
                    # if time.time() - obj.the_obj_last_use_time > 30 * 60:
                    if time.time() - obj.the_obj_last_use_time > 30 * 60:
                        obj.clean_up()
                    else:
                        self._queue.put(obj)

    def _borrow_a_object(self, block, timeout):
        with self._lock:
            self._is_using_num += 1
        try:
            if self._queue.qsize() == 0 and self._is_using_num <= self.num:
                t1 = time.perf_counter()
                obj = self.object_type()
                self.logger.info(f'创建对象 {obj} ,耗时 {time.perf_counter() - t1}')
                self._queue.put(obj)
                # print(self._queue.qsize())
            obj = self._queue.get(block, timeout)
            self.logger.debug(f'获取对象 {obj}')
            obj.the_obj_last_use_time = time.time()
            return obj
        except Exception as e:
            self.logger.critical(e, exc_info=True)
            with self._lock:
                self._is_using_num -= 1

    def _back_a_object(self, obj):
        self._queue.put(obj)
        self.logger.debug(f'归还对象 {obj}')
        with self._lock:
            self._is_using_num -= 1

    def get(self, block=True, timeout=None):
        return _ObjectContext(self, block=block, timeout=timeout)


# noinspection PyProtectedMember
class _ObjectContext(nb_log.LoggerMixin):
    def __init__(self, pool: ObjectPool, block, timeout):
        self._pool = pool
        self._block = block
        self._timeout = timeout
        self.obj = None

    def __enter__(self):
        self.obj = self._pool._borrow_a_object(self._block, self._timeout)
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.logger.info(self.obj)
        if self.obj is not None:
            self._pool._back_a_object(self.obj, )
        self.obj = None

    def __del__(self):
        # self.logger.warning(self.obj)
        if self.obj is not None:
            self._pool._back_a_object(self.obj)
        self.obj = None


class AbstractObject(metaclass=abc.ABCMeta, ):
    @abc.abstractmethod
    def __init__(self):
        self.core_obj = None  # 这个主要是为了把自定义对象的属性指向的核心对象的方法自动全部注册到自定义对象的方法。

    @abc.abstractmethod
    def clean_up(self):
        pass

    def __getattr__(self, item):
        return getattr(self.core_obj, item)
