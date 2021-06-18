import threading, time
from random import randint


class Producer(threading.Thread):
    def run(self):
        global L
        while True:
            val = randint(0, 100)
            # if lock_con.acquire():
            #     L.append(val)
            #     print(f"生产者:{self.name}, Append:{val},队列：{L}")
            #     lock_con.notify()
            #     lock_con.release()
            with lock_con:
                L.append(val)
                print(f"生产者:{self.name}, Append:{val}, L = {L}")
                lock_con.notify()
            time.sleep(3)


class Consumer(threading.Thread):
    def run(self):
        global L
        while True:
            with lock_con:
                if len(L) == 0:
                    print("队列为空，请等待。。。")
                    lock_con.wait()
                print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
                print(f"消费者: {self.name}, Delete: {L[0]}")
                del L[0]
            time.sleep(0.5)


if __name__ == '__main__':
    import nb_log
    L = []  # 消费物队列
    lock_con = threading.Condition()
    threads = []
    # 若干个生产者线程
    for i in range(3):
        threads.append(Producer())
    threads.append(Consumer())
    for t in threads:
        t.start()
    for t in threads:
        t.join()