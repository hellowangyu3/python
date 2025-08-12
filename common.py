import queue
from kfifo import KFifoAps
serial_recv_fifo = KFifoAps()
serial_send_fifo = KFifoAps()
response_queue = queue.Queue()