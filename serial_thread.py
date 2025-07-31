from PyQt6.QtCore import QThread, pyqtSignal
import time
import log
import threading
from kfifo import KFifoAps

global_kfifo = KFifoAps(1024)  #

class SerialThread(QThread):
    """串口线程：使用全局KFIFO缓冲区存储数据"""
    data_received = pyqtSignal(str)  # 发送接收数据信号（主线程更新UI用）

    def __init__(self, serial_if, parent=None):
        super().__init__(parent)
        self.serial_if = serial_if  # 串口接口实例（从主窗口传入）
        self.is_running = False     # 线程运行状态标志

    def run(self):
        """线程主循环：读取串口数据并写入全局KFIFO缓冲区"""
        while self.is_running:
            time.sleep(0.1)

    def start_thread(self):
        """启动串口线程（修复状态赋值错误）"""
        if not self.is_running:
            self.is_running = True
            self.start()
            log.write_to_plain_text_3("串口线程已启动")

    def stop_thread(self):
        """停止串口线程（修复线程阻塞问题）"""
        if self.is_running:
            self.is_running = False  # 终止线程主循环
            # 关键修复：先关闭串口接口，避免read_data()持续阻塞
            if self.serial_if.is_open():
                self.serial_if.close()  # 假设serial_if有close()方法
            self.wait(1000)  # 等待线程退出（超时1秒）
        log.write_to_plain_text_3("串口线程已停止")


