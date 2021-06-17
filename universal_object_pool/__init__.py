import abc
import queue
import threading
import time
from queue import LifoQueue
import decorator_libs
import nb_log


class ObjectPool(nb_log.LoggerMixin, nb_log.LoggerLevelSetterMixin):
    def __init__(self, object_type, object_init_kwargs: dict = None, object_pool_size=10, max_idle_seconds=30 * 60):
        """

        :param object_type: 对象类型，将会实例化此类
        :param object_init_kwargs: 对象的__init__方法的初始化参数
        :param object_pool_size: 对象池大小
        :param max_idle_seconds: 最大空闲时间，大于次时间没被使用的对象，将会被自动摧毁和弹出。摧毁是自动调用对象的clean_up方法
        """
        self._object_init_kwargs = {} if object_init_kwargs is None else object_init_kwargs
        self._max_idle_seconds = max_idle_seconds  # 大于此空闲时间没被使用的对象，将会被自动摧毁从对象池弹出。
        self.object_pool_size = object_pool_size
        self.queue = self._queue = LifoQueue(object_pool_size)
        self._lock = threading.Lock()
        self.is_using_num = 0
        self._has_create_object_num = 0
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
                    if time.time() - obj.the_obj_last_use_time > self._max_idle_seconds:
                        self.logger.info(f'此对象空闲时间超过 {self._max_idle_seconds}  秒，使用 {obj.clean_up} 方法 自动摧毁{obj}')
                        obj.clean_up()
                        self._has_create_object_num -= 1
                    else:
                        self._queue.put(obj)

    def _borrow_a_object(self, block, timeout):
        with self._lock:
            try:
                # print(self._queue.qsize(), self._has_create_object_num)
                if self._queue.qsize() == 0 and self._has_create_object_num < self.object_pool_size:
                    t1 = time.perf_counter()
                    obj = self.object_type(**self._object_init_kwargs)
                    self.logger.info(f'创建对象 {obj} ,耗时 {time.perf_counter() - t1}')
                    self._queue.put(obj)
                    self._has_create_object_num += 1
                    # print(self._queue.qsize())
                obj = self._queue.get(block, timeout)
                self.is_using_num += 1
                self.logger.debug(f'获取对象 {obj}')
                obj.the_obj_last_use_time = time.time()
                return obj
            except queue.Empty as e:
                self.logger.critical(f'{e}  对象池暂时没有可用的对象了，请把timeout加大、或者不设置timeout(没有对象就进行永久阻塞等待)、或者设置把对象池的数量加大', exc_info=True)
                raise e
            except Exception as e:
                self.logger.critical(e, exc_info=True)
                raise e

    def _back_a_object(self, obj):
        if getattr(obj, 'is_available', None) is False:
            self.logger.critical(f'{obj} 不可用,不放入')
            self._has_create_object_num -= 1
        else:
            self._queue.put(obj)
            self.logger.debug(f'归还对象 {obj}')
        self.is_using_num -= 1

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
        self.obj.before_use()
        return self.obj

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.logger.info(self.obj)
        if exc_type:
            self.logger.critical(exc_type)
        if exc_type in getattr(self.obj, 'error_type_list_set_not_available', []):
            self.obj._set_not_available()
        if self.obj is not None:
            self.obj.before_back_to_queue(exc_type, exc_val, exc_tb)
            self._pool._back_a_object(self.obj, )
        self.obj = None

    def __del__(self):
        # self.logger.warning(self.obj)
        if self.obj is not None:
            self._pool._back_a_object(self.obj)
        self.obj = None


class AbstractObject(metaclass=abc.ABCMeta, ):
    error_type_list_set_not_available = []  # 可以设置当发生了什么类型的错误，就把对象设置为失效不可用。

    @abc.abstractmethod
    def __init__(self):
        self.core_obj = None  # 这个主要是为了把自定义对象的属性指向的核心对象的方法自动全部注册到自定义对象的方法。

    @abc.abstractmethod
    def clean_up(self):
        """ 这里写关闭操作，如果没有逻辑，可以写 pass """

    def before_use(self):
        """ 可以每次对取出来的对象做一些操作"""
        pass

    def _set_not_available(self):
        self.is_available = False

    @abc.abstractmethod
    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        """ 这里写 with语法退出__exit__前的操作，如果没有逻辑，可以写 pass """

    def __getattr__(self, item):
        """ 这个很强悍，可以使某个官方对象的全部方法和属性自动加到自己的自定义对象上面来。例如 myobj.conn.query(sql) 能直接 myobj.query(sql)"""
        return getattr(self.core_obj, item)
