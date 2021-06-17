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

        print(self.ssh)

    def clean_up(self):
        self.sftp.close()
        self.ssh.close()

    def before_back_to_queue(self, exc_type, exc_val, exc_tb):
        pass

    def exec_cmd(self, cmd):
        # paramiko.channel.ChannelFile.readlines()
        self.logger.debug('要执行的命令是： ' + cmd)
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        stdout_str = stdout.read().decode('utf8')
        stderr_str = stderr.read().decode('utf8')
        if stdout_str != '':
            self.logger.info('执行 {} 命令的stdout是 -- > \n{}'.format(cmd, stdout_str))
        if stderr_str != '':
            self.logger.error('执行 {} 命令的stderr是 -- > \n{}'.format(cmd, stderr_str))
        return stdout_str, stderr_str


if __name__ == '__main__':
    paramiko_pool = ObjectPool(object_type=ParamikoOperator,
                               object_init_kwargs=dict(host='192.168.6.130', port=22, username='ydf', password='372148', ),
                               max_idle_seconds=60, object_pool_size=20)

    ParamikoOperator(**dict(host='192.168.6.130', port=22, username='ydf', password='372148', ))


    def test_paramiko(cmd):
        with paramiko_pool.get() as paramiko_operator:  # type:ParamikoOperator
            # pass
            print(paramiko_operator.exec_cmd(cmd))


    thread_pool = BoundedThreadPoolExecutor(20)
    with decorator_libs.TimerContextManager():
        for x in range(20, 100):
            thread_pool.submit(test_paramiko, 'date;sleep 20s;date')  # 这个命令单线程for循环顺序执行每次需要20秒，如果不用对象池执行80次要1600秒
            # thread_pool.submit(test_update_multi_threads_use_one_conn, x)
        thread_pool.shutdown()
    time.sleep(10000)  # 这个可以测试验证，此对象池会自动摧毁连接如果闲置时间太长，
