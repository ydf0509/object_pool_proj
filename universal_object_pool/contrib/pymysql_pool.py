import copy

import pymysql
import typing
from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import threading
import time
import decorator_libs

"""
这个是真正的用pymsql实现连接池的例子，完全没有依赖dbutils包实现的连接池。
比dbutils嗨好用，实际使用时候不需要操作cursor的建立和关闭。

dbutils官方用法是

pool= PooledDB()
db = pool.connection()
cur = db.cursor()
cur.execute(...)
res = cur.fetchone()
cur.close()  # or del cur
db.close()  # or del db

"""


class PyMysqlOperator(AbstractObject):
    error_type_list_set_not_available = []  # 有待考察。

    # error_type_list_set_not_available = [pymysql.err.InterfaceError]

    def __init__(self, host='192.168.6.130', user='root', password='123456', cursorclass=pymysql.cursors.DictCursor, autocommit=False, **pymysql_connection_kwargs):
        in_params = copy.copy(locals())
        in_params.update(pymysql_connection_kwargs)
        in_params.pop('self')
        in_params.pop('pymysql_connection_kwargs')
        self.conn = pymysql.Connection(**in_params)

    """ 下面3个是重写的方法"""

    def clean_up(self):  # 如果一个对象最近30分钟内没被使用，那么对象池会自动将对象摧毁并从池中删除，会自动调用对象的clean_up方法。
        self.conn.close()

    def before_use(self):
        self.cursor = self.conn.cursor()
        self.core_obj = self.cursor  # 这个是为了operator对象自动拥有cursor对象的所有方法。

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()  # 也可以不要，因为每次的cusor都是不一样的。

    """以下可以自定义其他方法。
    因为设置了self.core_obj = self.cursor ，父类重写了__getattr__,所以此对象自动拥有cursor对象的所有方法,如果是同名同意义的方法不需要一个个重写。
    """

    def execute(self, query, args):
        """
        这个execute由于方法名和入参和逻辑与官方一模一样，可以不需要，因为设置了core_obj后，operator对象自动拥有cursor对象的所有方法，可以把这个方法注释了然后测试运行不受影响。
        :param query:
        :param args:
        :return:
        """
        return self.cursor.execute(query, args)


if __name__ == '__main__':
    mysql_pool = ObjectPool(object_type=PyMysqlOperator, object_pool_size=100, object_init_kwargs={'port': 3306})


    def test_update(i):
        sql = f'''
            INSERT INTO db1.table1(uname ,age)
        VALUES(
            %s ,
            %s)
        ON DUPLICATE KEY UPDATE
            uname = values(uname),
            age = if(values(age)>age,values(age),age);
        '''
        with mysql_pool.get(timeout=2) as operator:  # type: typing.Union[PyMysqlOperator,pymysql.cursors.DictCursor] #利于补全
            print(id(operator.cursor), id(operator.conn))
            operator.execute(sql, args=(f'name_{i}', i * 4))
            print(operator.lastrowid)  # opererator 自动拥有 operator.cursor 的所有方法和属性。 opererator.methodxxx 会自动调用 opererator.cursor.methodxxx


    operator_global = PyMysqlOperator()


    def test_update_multi_threads_use_one_conn(i):
        """
        这个是个错误的例子，多线程运行此函数会疯狂报错,单线程不报错
        这个如果运行在多线程同时操作同一个conn，就会疯狂报错。所以要么狠low的使用临时频繁在函数内部每次创建和摧毁mysql连接，要么使用连接池。
        :param i:
        :return:
        """
        sql = f'''
            INSERT INTO db1.table1(uname ,age)
        VALUES(
            %s ,
            %s)
        ON DUPLICATE KEY UPDATE
            uname = values(uname),
            age = if(values(age)>age,values(age),age);
        '''

        operator_global.before_use()
        print(id(operator_global.cursor), id(operator_global.conn))
        operator_global.execute(sql, args=(f'name_{i}', i * 3))
        operator_global.cursor.close()
        operator_global.conn.commit()


    thread_pool = BoundedThreadPoolExecutor(20)
    with decorator_libs.TimerContextManager():
        for x in range(200000, 300000):
            thread_pool.submit(test_update, x)
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
