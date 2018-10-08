import pika
import uuid


class ShodanRpcClient(object):
    def __init__(self):
        rmq_creds = pika.PlainCredentials('guest', 'guest')
        rmq_params = pika.ConnectionParameters('localhost', 5672, '/', rmq_creds)
        self.connection = pika.BlockingConnection(rmq_params)
        self.channel = self.connection.channel()

        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.response = None
        self.corr_id = int()
        self.channel.basic_consume(self.on_response, no_ack=True, queue=self.callback_queue)

    def on_response(self, ch, method, props, body):
        if self.corr_id == props.correlation_id:
            self.response = body

    def call(self, ip):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(exchange='',
                                   routing_key='shodan_rpc_queue',
                                   properties=pika.BasicProperties(
                                         reply_to=self.callback_queue,
                                         correlation_id=self.corr_id,
                                   ),
                                   body=str(ip))
        while self.response is None:
            self.connection.process_data_events()

        return str(self.response.decode('utf8'))