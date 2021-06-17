import pymysql
import typing
from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import threading
import time
import decorator_libs


class PymysqlOperator(AbstractObject):
    def __init__(self):
        self.conn = pymysql.Connection(host='192.168.6.130', user='root', password='123456', cursorclass=pymysql.cursors.DictCursor, autocommit=False)

    def clean_up(self):
        self.conn.close()

    def extra_init(self):
        self.cursor = self.conn.cursor()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.cursor.close()  # 也可以不要，因为每次的cusor都是不一样的。

    def execute(self, query, args):
        self.cursor.execute(query, args)


mysql_pool = ObjectPool(object_type=PymysqlOperator, num=1)


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
    with mysql_pool.get(timeout=1000) as operator:  # type: PymysqlOperator
        print(id(operator.cursor), id(operator.conn))
        operator.execute(sql, args=(f'name_{i}', i * 3))


operator_global = PymysqlOperator()


def test_update_use_one_conn(i):
    """
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

    operator_global.extra_init()
    print(id(operator_global.cursor), id(operator_global.conn))
    operator_global.execute(sql, args=(f'name_{i}', i * 3))
    operator_global.cursor.close()
    operator_global.conn.commit()


if __name__ == '__main__':
    thread_pool = BoundedThreadPoolExecutor(100)
    with decorator_libs.TimerContextManager():
        for x in range(20000, 30000):
            thread_pool.submit(test_update_use_one_conn, x)
        thread_pool.shutdown()
