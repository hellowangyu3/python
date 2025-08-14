import queue
from kfifo import KFifoAps

serial_recv_fifo = KFifoAps()
serial_send_fifo = KFifoAps()
response_queue = queue.Queue()
response_03F1_queue = queue.Queue()
response_15F1_queue = queue.Queue()