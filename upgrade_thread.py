#这个文件在所有配置项都配置完成后，收到开始升级按键，开始升级
# 循环的往upgrade_fifo队列中发送数据，等待upgrade_fifo中数据为空-即被其他线程读完了
#升级完成后调用自身函数3，将数据更新-进行版本比对，


from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal
import serial_bsp
import log
from kfifo import KFifoAps
upgrade_fifo = KFifoAps()
class UpgradeThread(QThread):
    """升级线程：接收配置参数并执行升级逻辑，通过信号返回日志"""
    log_signal = pyqtSignal(str)  # 发送日志信息给主窗口

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False  # 线程运行状态标志
        self.upgrade_path = None
        self.upgrade_total = 0

    @pyqtSlot(dict)  # 接收主窗口发送的配置参数
    def run_upgrade(self, config):
        """执行升级逻辑（通过主窗口信号触发）"""
        self.is_running = True
        self.log_signal.emit("升级线程启动，开始执行升级...")
        print("代码还没写，先打印一下配置参数")
        print(config)
        return True

    # def read_upgrade_file(self,num_of_bytes):
    #
    #     try:
    #         with open(file_path, "rb") as f:
    #             self.firmware_data = f.read()
    #         self.log_signal.emit(f"成功读取升级文件：{file_path}，大小：{len(self.firmware_data)}字节")


    def _read_upgrade_file(self, file_path):
        """读取升级文件内容（内部辅助方法）"""
        try:
            with open(file_path, "rb") as f:
                self.firmware_data = f.read()
            self.log_signal.emit(f"成功读取升级文件：{file_path}，大小：{len(self.firmware_data)}字节")
            # 按128字节分割数据并打印

            output_path = "./firmware_output.txt"
            with open(output_path, "w") as out_f:
                for i in range(0, len(self.firmware_data), 128):
                    # 截取128字节数据并转换为十六进制字符串
                    chunk = self.firmware_data[i:i + 128]
                    hex_line = ' '.join(f'{byte:02x}' for byte in chunk)
                    out_f.write(hex_line + '\n')
            self.log_signal.emit(f"数据已成功写入文件：{output_path}，共{len(self.firmware_data) // 128 + 1}行")

            return True

        except Exception as e:
            self.log_signal.emit(f"读取升级文件失败: {str(e)}")
            return False

    def _send_firmware_data(self, frame_length):
        """分帧发送固件数据（内部辅助方法）"""
        # ... 实现分帧发送逻辑（使用serial_bsp发送数据）...
        pass

    def stop_upgrade(self):
        """停止升级线程（供主窗口调用）"""
        self.is_running = False
        self.log_signal.emit("升级线程已停止")