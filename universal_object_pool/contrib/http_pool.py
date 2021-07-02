import copy
import time
import typing
import http
from http.client import HTTPConnection, HTTPResponse
import socket
import nb_log

from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import decorator_libs


class CustomHTTPResponse(HTTPResponse):  # 为了ide补全
    text: str = None
    content: bytes = None


class HttpOperator(AbstractObject):
    """ 这个请求速度暴击requests，可以自行测试请求nginx网关本身"""
    error_type_list_set_not_available = [http.client.CannotSendRequest]

    def __init__(self, host, port=None, timeout=5,
                 source_address=None):
        self.conn = HTTPConnection(host=host, port=port, timeout=timeout, source_address=source_address, )
        self.core_obj = self.conn

    def clean_up(self):
        self.conn.close()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass

    # noinspection PyDefaultArgument
    def request_and_getresponse(self, method, url, body=None, headers={}, *,
                                encode_chunked=False, encoding="utf-8") -> CustomHTTPResponse:
        self.conn.request(method, url, body=body, headers=headers,
                          encode_chunked=encode_chunked)
        resp = self.conn.getresponse()
        resp.content = resp.read()
        resp.text = resp.content.decode(encoding)
        return resp  # noqa


if __name__ == '__main__':
    http_pool = ObjectPool(object_type=HttpOperator, object_pool_size=100, object_init_kwargs=dict(host='192.168.6.131', port=9999),
                           max_idle_seconds=30)

    import requests

    ss = requests.session()

    import urllib3

    mgr = urllib3.PoolManager(100)


    def test_request():
        # 这个连接池是requests性能5倍。
        # resp = ss.get('http://192.168.6.131:9999/')

        # resp = requests.get('http://192.168.6.131:9999/',headers = {'Connection':'close'}) # 这个请求速度被暴击。win上没有使用连接池如果超大线程并发请求，会造成频繁出现一个端口只能使用一次的错误。
        # print(resp.text)

        # resp=  mgr.request('get','http://192.168.6.131:9999/')  # urllib3 第二快，次代码手动实现的http池是第一快。
        # print(resp.data)

        with http_pool.get() as conn:  # type: typing.Union[HttpOperator,HTTPConnection]  # http对象池的请求速度暴击requests的session和直接requests.get
            r1 = conn.request_and_getresponse('GET', '/')
            print(r1.text[:10], )


    thread_pool = BoundedThreadPoolExecutor(100)
    with decorator_libs.TimerContextManager():
        for x in range(30000):
            # time.sleep(5)  # 这是测试是否是是智能节制新建对象，如果任务不密集，不需要新建那么多对象。
            thread_pool.submit(test_request, )
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
    time.sleep(10000)
