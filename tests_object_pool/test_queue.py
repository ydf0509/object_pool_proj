from queue import Queue,LifoQueue,PriorityQueue


q  = LifoQueue()

for i in range(10):
    q.put(i)

while not q.empty():
    print(q.get())