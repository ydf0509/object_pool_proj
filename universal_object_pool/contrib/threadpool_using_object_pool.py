import concurrent.futures
import queue
import threading
import time

import nb_log

from universal_object_pool import AbstractObject, ObjectPool


class ThreadObjectPool(ObjectPool):

    def __init__(self, object_pool_size=10, max_idle_seconds=60):
        self.work_queue = queue.Queue(object_pool_size)  # 使工作队列使有界队列。
        super().__init__(ThreadOperator, {'q': self.work_queue}, object_pool_size, max_idle_seconds)

    def _borrow_a_object(self, block, timeout):
        with self._lock:
            t0 = time.time()
            try:
                if self._has_create_object_num < self.object_pool_size:  # 这行改了。
                    t1 = time.perf_counter()
                    obj = self.object_type(**self._object_init_kwargs)
                    self.logger.info(f'创建对象 {obj} ,耗时 {round(time.perf_counter() - t1, 3)}')
                    self._queue.put(obj)
                    self._has_create_object_num += 1
                    # print(self._queue.qsize())
                t2 = time.time()
                obj = self._queue.get(block, timeout)
                # print(time.time() -t2)
                self.is_using_num += 1
                self.logger.debug(f'获取对象 {obj}')
                obj.the_obj_last_use_time = time.time()
                return obj
            except queue.Empty as e:
                self.logger.critical(f'{e}  对象池暂时没有可用的对象了，请把timeout加大、或者不设置timeout(没有对象就进行永久阻塞等待)、或者设置把对象池的数量加大',
                                     exc_info=True)
                raise e
            except Exception as e:
                self.logger.critical(e, exc_info=True)
                raise e
            finally:
                pass
                # print(time.time() -t0)

    def submit(self, f, *args, **kwargs):
        with self.get() as thread_op:  # type:ThreadOperator
            thread_op.submit(f, *args, **kwargs)


class ThreadOperator(AbstractObject, nb_log.LoggerMixin):
    error_type_list_set_not_available = []  # 出了特定类型的错误，可以设置对象已经无效不可用了，不归还到队列里面。

    def __init__(self, q: queue.Queue):
        self._work_queue = q
        self._thread_term_flag = 0
        self.thread = threading.Thread(target=self._run)
        self.thread.start()

    """ 下面3个是重写的方法"""

    def clean_up(self):
        self._thread_term_flag = 1

    def before_use(self):
        pass

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass

    def submit(self, f, *args, **kwargs):
        item= (f, args, kwargs)
        self._work_queue.put(item)

    def _run(self):
        while 1:
            if self._thread_term_flag == 1:
                break
            try:
                item = self._work_queue.get(block=True, timeout=10)
                f, args, kwargs = item
            except queue.Empty:
                pass
            else:
                try:
                    f(*args, **kwargs)
                except BaseException as e:
                    self.logger.error(e, exc_info=True)


if __name__ == '__main__':

    thread_pool = ThreadObjectPool(100)

    c_pool = concurrent.futures.ThreadPoolExecutor(100)


    def my_fun(x, y):
        z = x + y
        if x % 1 == 0:
            print(x)


    t00 = time.time()
    for i in range(10 * 1000):
        # thread_pool.submit(my_fun, i, i * 2)  # 使用线程池测试求和100万次 30秒

        # threading.Thread(target=my_fun, args=(i, i * 2)).start() #  使用临时启动线程池，测试求和100万次150秒

        c_pool.submit(my_fun, i, i * 2)  # 对比官方是15秒。

    print(time.time() - t00)

    # time.sleep(100)

    for i in range(10 * 1000):
        thread_pool.submit(my_fun, i, i * 2)  # 测试空闲关闭线程后，能否在启动线程
