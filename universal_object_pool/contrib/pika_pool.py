import copy
import time
import typing
import nb_log
import pika
from pika.channel import Channel
from pika.exceptions import AMQPError

from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import decorator_libs


class PikaOperator(AbstractObject, ):
    def __init__(self, host, port, user, password, queue):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._queue = queue
        self._create_channel()
        self.logger = nb_log.get_logger(self.__class__.__name__)

    def _create_channel(self):
        auth = pika.PlainCredentials(self._user, self._password)
        self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=self._host, port=self._port, credentials=auth, heartbeat=20))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=self._queue)
        self.core_obj = self.channel

    def simple_publish(self, body):
        # print(self.channel)
        try:
            self.channel.basic_publish(exchange='',
                                       routing_key=self._queue,
                                       body=body)
        except AMQPError as e:
            self.logger.critical(e, exc_info=True)
            self._create_channel()
            self.channel.basic_publish(exchange='',
                                       routing_key=self._queue,
                                       body=body)

    def clean_up(self):
        self.channel.close()
        self.connection.close()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == '__main__':
    pika_pool = ObjectPool(object_type=PikaOperator, object_pool_size=1, object_init_kwargs=dict(
        host='106.55.244.110', port=5672, user='xxxx', password='xxxx', queue='test_pika_pool_queue7'),
                           max_idle_seconds=60)


    def test_publish():
        with pika_pool.get() as ch:  # type: typing.Union[Channel,PikaOperator]
            # 如果是外网连接mq，就快很多。
            ch.simple_publish('hello')
            # print(ch)
            # time.sleep(1)


    thread_pool = BoundedThreadPoolExecutor(200)
    with decorator_libs.TimerContextManager():
        for x in range(50000):
            thread_pool.submit(test_publish, )
            print(x)
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
    time.sleep(10000)
