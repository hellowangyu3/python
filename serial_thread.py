from PyQt6.QtCore import QThread, pyqtSignal
import time
import log
import threading
from kfifo import KFifoAps

serial_fifo = KFifoAps()
uart_send_fifo = KFifoAps()

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
                    hex_data = ' '.join(f"{b:02X}" for b in data)  # 新增：字节转十六进制
                    data_with_prefix = f"[uart]{hex_data}"  # 修改：使用十六进制数据
                    # [收]68 2C 00 03 04 00 00 00 00 0C 55 55 55 55 55 55 01 00 02 00 00 66 14 04 00 10 68 01 00 02
                    # 00 00 66 68 11 04 34 34 39 38 27 16 06 16[收]68 2C 00 03 04 00 00 00 00 0C 55 55 55 55 55 55 01 00 02 00 00 66 14 04 00 10 68 01 00 02 00 00 66 68 11 04 34 34 39 38 27 16 06 16
                    self.data_received.emit(data_with_prefix)
                    print(data_with_prefix)
                    log.log_info(log.LOG_DEBUG_CMD, data_with_prefix)
                    serial_fifo.put(data)
                    # fifo_data = serial_fifo.get(serial_fifo.get_data_length())
                    # print(f"获取到的数据: {fifo_data}")
                    # 获取到的数据: [104, 44, 0, 3, 4, 0, 0, 0, 0, 12, 85, 85, 85, 85, 85, 85, 1, 0, 2, 0, 0, 102, 20, 4,
                    #                0, 16, 104, 1, 0, 2, 0, 0, 102, 104, 17, 4, 52, 52, 57, 56, 39, 22, 6, 22]
                fifolen = uart_send_fifo.get_data_length()
                if fifolen > 0:
                    send_data = uart_send_fifo.get(fifolen)
                    log.log_info(log.LOG_DEBUG_CMD, f"发送数据: {send_data}")
                    success, msg = self.serial_if.send_data(send_data, is_hex=True)
                    if success:
                        log.log_info(log.LOG_DEBUG_CMD, f"发送成功: {msg}")
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


