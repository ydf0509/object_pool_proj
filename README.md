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
这是万能对象池，所以可以实现webdriver浏览器池。对象并不是需要严格实实在在的外部cocket或者浏览器什么的，也可以是python语言的一个普通对象。
只要这个对象创建代价大，并且它的核心方法是非线程安全的，就很适合使用对象池来使用它。




```

## 1.常问问题回答

### 1.1 对象池是线程安全的吗？

```
这个问题牛头不对马嘴 ，对象池就是为多线程或者并发而生的。
你想一下，如果你的操作只有一个主线程，那直接用一个对象一直用就是了，反正不会遇到多线程要使用同一个对象。

你花脑袋想想，如果你的代码是主线程单线程的，你有必要用dbutils来搞mysql连接池吗。
直接用pymysql的conn不是更简单更香吗。
web后端是uwsgi gunicorn来自动开多线程或者协程是自动并发的，虽然你没亲自开多线程，但也是多线程的，需要使用连接池。

任何叫池的东西都是为并发而生的，如果不能多线程安全，那存在的意义目的何在？

```

### 1.2 对象池 连接池 线程池有什么区别。

```
连接池就是对象池，连接池一般是链接数据库 或者中间件或者socket的对象，比如mysql的connection，有的对象并不是链接什么socket，
但是创建代价大，方法非线程安全，就是对象池。连接池是对象池的一个子集。

线程池和对象池关系很小，此对象池可以实现了一切对象池化，但并不能拿来实现线程池。
如果要看线程池，https://github.com/ydf0509/threadpool_executor_shrink_able 此项目实现了线程池。


https://blog.csdn.net/Alan_Mathison_Turing/article/details/78512410 这个讲得对象池和线程池区别，讲的不错。

一个对象池的基本行为包括：

创建对象newObject()
借取对象getObject()
归还对象freeObject()

线程池
首先摆出结论：线程池糅合了对象池模型，但是核心原理是生产者-消费者模型。

线程池并不是像多线程把某个线程借出去使用然后利用完了归还，线程池里面的线程都是while true的死循环，
不会像对象池例如mysql的conn查询一下几十毫秒钟就用完了，线程池里面的线程对象是永不结束的，没有借出去使用用完了后归还这种事情。

任何线程池实现都是有个queue，生产者往queue里面submit任务，
消费者是例如100个线程，每个线程里面跑的函数都是while True的死循环函数，while 1里面不断的用queue.get从queue里面拉取任务，
拉取一个任务，就立即fun(x,y)这么去运行。任何语言任何人实现线程池一定是这个思路这么写的，没有例外。

说到死循环那就很有趣了，这里是线程池设计的一个难点重点，如果while True死循环，那线程池不是无敌了无解了，代码那不是永远结束不了？
线程池里面设计的一个难点就包括这里，所以很多人写的线程池都很难用，要么程序永不结束，要么设计成了线程池的queue里面还有任务没完成，
程序就结束了，所以pool.submit，很多人搞的线程池在代码最结尾要加上pool.termit什么玩意的，可以百度博客园python线程池好多就是这样的，
没有几个人设计的手写线程池达到了 concurrent.futures.Threadpoolexecutor那么好用的程度，最主要是不了解守护线程，
很多人都是搞的非守护线程，导致发明的线程池比内置的concurrent.futures.Threadpoolexecutor好用程度差十万八千里。
如果把while 1死循环的线程设置为守护线程，那么当主线程结束后，守护线程就会自动随程序结束了。当然了光设置守护线程还不够，
如果主线程把任务都submit到queue里面了，实际上线程池应该还需要运行queue里面的任务，所以还需要加个判断，要加上 atexit.register的钩子，
让任务执行完成才关闭。设计一个好用的线程池还是很难的，设计一个死循环导致代码永不能自动结束的线程池就简单很多了。线程池的思路于对象池不同。



```

## 2.利用对象池来封装任意类型的池演示

contrib 文件夹自带演示了4个封装，包括http pymsql webdriver paramiko(操作linux的python包)的池化。

### 2.1 mysql 池化
以下是pymysql_pool的池化代码，使用has a模式封装的PyMysqlOperator对象，你也可以使用is a来继承方式来写，但要实现clean_up等方法。

```python
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
    error_type_list_set_not_available = []  # 有待考察，出了特定类型的错误，可以设置对象已近无效不可用了。

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
    time.sleep(10000)  # 这个可以测试验证，此对象池会自动摧毁连接如果闲置时间太长，会自动摧毁对象


``` 

### 2.2 linux 操作神库 paramiko 的池化，例如可以大幅度加快文件传输和大幅度加快有io的命令。

比如有很多几kb的小文件需要上传，对象池 + 线程池可以大幅度提升上传速度

比如让linux执行有io耗时的curl命令，对象池 + 线程池可以大幅度提升命令执行效率。

所以此对象池可以池化一切python对象，不仅是是数据库连接。

```python
import time

import decorator_libs
import paramiko
import nb_log
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor

from universal_object_pool import AbstractObject, ObjectPool

"""
 t = paramiko.Transport((self._host, self._port))
        t.connect(username=self._username, password=self._password)
        self.sftp = paramiko.SFTPClient.from_transport(t)

        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self._host, port=self._port, username=self._username, password=self._password, compress=True)
        self.ssh = ssh
"""


class ParamikoOperator(nb_log.LoggerMixin, nb_log.LoggerLevelSetterMixin, AbstractObject):
    """
    这个是linux操作包的池化。例如执行的shell命令耗时比较长，如果不采用池，那么一个接一个的命令执行将会很耗时。
    如果每次临时创建和摧毁linux连接，会很多耗时和耗cpu开销。

    """

    def __init__(self, host, port, username, password):
        # self.logger = nb_log.get_logger('ParamikoOperator')

        t = paramiko.Transport((host, port))
        t.connect(username=username, password=password)
        self.sftp = paramiko.SFTPClient.from_transport(t)

        ssh = paramiko.SSHClient()
        # ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, port=port, username=username, password=password, compress=True)  # 密码方式

        # private = paramiko.RSAKey.from_private_key_file('C:/Users/Administrator/.ssh/id_rsa')  # 秘钥方式
        # ssh.connect(host, port=port, username=username, pkey=private)
        self.ssh = self.core_obj = ssh

        self.ssh_session = self.ssh.get_transport().open_session()


    def clean_up(self):
        self.sftp.close()
        self.ssh.close()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass

    def exec_cmd(self, cmd):
        # paramiko.channel.ChannelFile.readlines()
        self.logger.debug('要执行的命令是： ' + cmd)
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        stdout_str = stdout.read().decode()
        stderr_str = stderr.read().decode()
        if stdout_str != '':
            self.logger.info('执行 {} 命令的stdout是 -- > \n{}'.format(cmd, stdout_str))
        if stderr_str != '':
            self.logger.error('执行 {} 命令的stderr是 -- > \n{}'.format(cmd, stderr_str))
        return stdout_str, stderr_str


if __name__ == '__main__':
    paramiko_pool = ObjectPool(object_type=ParamikoOperator,
                               object_init_kwargs=dict(host='192.168.6.130', port=22, username='ydf', password='372148', ),
                               max_idle_seconds=120, object_pool_size=20)

    ParamikoOperator(**dict(host='192.168.6.130', port=22, username='ydf', password='372148', ))


    def test_paramiko(cmd):
        with paramiko_pool.get() as paramiko_operator:  # type:ParamikoOperator
            # pass
            ret = paramiko_operator.exec_cmd(cmd)
            print(ret[0])
            print(ret[1])


    thread_pool = BoundedThreadPoolExecutor(20)
    with decorator_libs.TimerContextManager():
        for x in range(20, 100):
            thread_pool.submit(test_paramiko, 'date;sleep 20s;date')  # 这个命令单线程for循环顺序执行每次需要20秒，如果不用对象池执行80次要1600秒
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
    time.sleep(10000)  # 这个可以测试验证，此对象池会自动摧毁连接如果闲置时间太长，会自动摧毁对象


```

### 2.3 一般性任意python对象的池化

```python
import typing
from universal_object_pool import ObjectPool, AbstractObject
from threadpool_executor_shrink_able import BoundedThreadPoolExecutor
import threading
import time

"""
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
这是万能对象池，所以可以实现webdriver浏览器池。对象并不是需要严格实实在在的外部cocket或者浏览器什么的，也可以是python语言的一个普通对象。
只要这个对象创建代价大，并且它的核心方法是非线程安全的，就很适合使用对象池来使用它。

"""

"""
此模块演示一般常规性任意对象的池化
"""


class Core:  # 一般假设这是个三方包大神写的包里面的某个重要公有类,你需要写的是用has a 模式封装他，你当然也可以使用is a模式来继承它并加上clean_up before_back_to_queue 方法。
    def insert(self, x):
        time.sleep(0.5)
        print(f'插入 {x}')

    def close(self):
        print('关闭连接')


class MockSpendTimeObject(AbstractObject):

    def __init__(self, ):
        time.sleep(0.1)  # 模拟创建对象耗时

        s = 0  # 模拟创建对象耗费cpu
        for j in range(10000 * 500):
            s += j

        self.conn = self.core_obj = Core()  # 这个会造成obj.xx  自动调用 obj.core_obj.xx，很好用。

        self._lock = threading.Lock()

    def do_sth(self, x):
        with self._lock:
            self.conn.insert(x)
            print(f' {x} 假设做某事同一个object只能同时被一个线程调用此方法，是排他的')

    def clean_up(self):
        self.core_obj.close()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass


if __name__ == '__main__':
    pool = ObjectPool(object_type=MockSpendTimeObject, object_pool_size=40).set_log_level(10)


    def use_object_pool_run(y):
        """ 第1种 使用对象池是正解"""
        # with ObjectContext(pool) as mock_obj:
        #     mock_obj.do_sth(y)
        with pool.get() as mock_obj:  # type:typing.Union[MockSpendTimeObject,Core]
            # mock_obj.insert(y)  # 可以直接使用core_obj的方法
            mock_obj.do_sth(y)


    def create_object_every_times_for_run(y):
        """第2种 多线程函数内部每次都采用临时创建对象，创建对象代价大，导致总耗时很长"""
        mock_obj = MockSpendTimeObject()
        mock_obj.do_sth(y)


    global_mock_obj = MockSpendTimeObject()
    global_mock_obj.insert(6666)  # 自动拥有self.core_object的方法。


    def use_globle_object_for_run(y):
        """
        第3种 ，多线程中，使用全局唯一对象。少了创建对象的时间，但是操作是独占时间排他的，这种速度是最差的。
        """
        global_mock_obj.do_sth(y)


    t1 = time.perf_counter()
    threadpool = BoundedThreadPoolExecutor(50)

    for i in range(1000):  # 这里随着函数的调用次数越多，对象池优势越明显。假设是运行10万次，三者耗时差距会更大。
        # 这里演示三种调用，1是多线程里用使用对象池 2是使用多线程函数内部每次临时创建关闭对象 3是多线程函数内部使用全局唯一对象。

        threadpool.submit(use_object_pool_run, i)  # 6秒完成
        # threadpool.submit(create_object_every_times_for_run, i)  # 82秒完成
        # threadpool.submit(use_globle_object_for_run, i)  # 耗时100秒

    threadpool.shutdown()
    print(time.perf_counter() - t1)

    time.sleep(100)

```