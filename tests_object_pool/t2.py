
import threading

from http.client import HTTPConnection

conn = HTTPConnection('127.0.0.1')

def f():
    conn.request('GET','/')
    r1 = conn.getresponse()
    print(r1.status, r1.reason)
    data1 = r1.read()
    print(data1)

t = threading.Thread(target=f)
t.start()

