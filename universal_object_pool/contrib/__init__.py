import typing
from universal_object_pool.contrib.http_pool import HttpOperator, HTTPConnection
from universal_object_pool.contrib.paramiko_pool import ParamikoOperator
from paramiko import SSHClient
from universal_object_pool.contrib.pymysql_pool import PyMysqlOperator
from pymysql.cursors import DictCursor
from universal_object_pool.contrib.webdriver_pool import WebDriverOperator, PhantomJS, Chrome
