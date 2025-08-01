from PyQt6.QtCore import QThread, pyqtSignal
import time
import log
import threading
from kfifo import KFifoAps

serial_fifo = KFifoAps()

class SerialThread(QThread):
    """串口线程：使用全局KFIFO缓冲区存储数据"""
    data_received = pyqtSignal(str)

    def __init__(self, serial_if, parent=None):
        super().__init__(parent)
        self.serial_if = serial_if  # 使用传入的实例
        self.is_running = False

    def run(self):
        """线程主循环：读取串口数据并写入全局KFIFO缓冲区"""
        while self.is_running:
            if self.serial_if.is_open:
                success, data = self.serial_if.read_data(1024)
                if success and data:
                    print(f"接收数据{data}")
                    serial_fifo.put(data)
                    data_with_prefix = f"[收]{data}"
                    # fifo_data = serial_fifo.get(serial_fifo.get_data_length())
                    # print(f"获取到的数据: {[hex(x) for x in fifo_data]}")
                    self.data_received.emit(data_with_prefix)
            time.sleep(0.01)

    def start_thread(self):
        if not self.is_running:
            self.is_running = True
            self.start()
            log.write_to_plain_text_3("串口线程已启动")

    def stop_thread(self):
        if self.is_running:
            self.is_running = False  # 终止线程主循环
            # 关键修复：先关闭串口接口，避免read_data()持续阻塞
            if self.serial_if.is_open:
                self.serial_if.close()  # 假设serial_if有close()方法
            self.wait(1000)  # 等待线程退出（超时1秒）
        log.write_to_plain_text_3("串口线程已停止")


