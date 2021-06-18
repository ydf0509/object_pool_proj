import amqpstorm
import amqpstorm
from amqpstorm.basic import Basic as AmqpStormBasic
from amqpstorm.queue import Queue as AmqpStormQueue
import decorator_libs

connection = amqpstorm.UriConnection(
    f'amqp://aartbeat={60 * 10}'
)
channel = connection.channel()  # type:amqpstorm.Channel
channel_wrapper_by_ampqstormbaic = AmqpStormBasic(channel)
queue = AmqpStormQueue(channel)
queue.declare(queue='test_queue555', durable=True)

#
with decorator_libs.TimerContextManager():
    for i in range(1000000):
        channel_wrapper_by_ampqstormbaic.publish(exchange='',
                                                 routing_key='test_queue555',
                                                 body=f'hello {i}',
                                                 properties={'delivery_mode': 2}, )

