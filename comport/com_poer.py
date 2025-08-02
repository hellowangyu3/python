import time

from PyQt6.QtCore import QThread, pyqtSignal
import queue
from protocol.gw13762 import gw13762_check, SApsAffair
import log
from serial_thread import serial_fifo

affair = SApsAffair()

class ParsingThread(QThread):
    """协议解析线程"""
    parse_result_signal = pyqtSignal(str)  # 解析结果信号
    data_received = pyqtSignal(str)
    def __init__(self):
        super().__init__()

        self.data_queue = queue.Queue()  # 数据队列
        self.running = True

    def add_data(self, data):
        """添加待解析数据到队列"""
        self.data_queue.put(data)
    def start_thread(self):
        if not self.is_running:
            self.is_running = True
            self.start()
            log.write_to_plain_text_3("协议解析线程已启动")

    def run(self):
        """线程主函数（伪代码）"""
        self.parse_result_signal.emit("解析线程已启动")
        start_idx = 0  # 帧头起始索引
        found = False  # 是否找到帧头标志
        while self.running:
            try:
                # 1. 从队列获取数据（超时100ms）
                fifolen = serial_fifo.get_data_length()
                if fifolen > 0:
                    frame_data = serial_fifo.get(fifolen)
                else:
                    time.sleep(0.01)
                    continue

                # self.data_received.emit(data)
                print(f"comport recv{frame_data}")
                frame = affair.p_src.local
                frame.datalen = len(frame_data)

                # 1. 查找帧头0x68的位置
                for i in range(len(frame_data)):
                    if frame_data[i] == 0x68:  # ✅ 修复全角冒号为半角 :
                        start_idx = i  # 记录帧头位置
                        found = True
                        break
                # 2. 未找到帧头时跳过处理
                if not found:
                    self.parse_result_signal.emit("未找到帧头0x68，跳过无效数据")
                    log.log_info(log.LOG_DEBUG_CMD, "未找到帧头0x68，跳过无效数据")
                    continue

                # 3. 仅复制帧头（0x68）之后的数据到frame.data
                valid_length = len(frame_data) - start_idx  # 有效数据长度（从0x68开始）
                frame.datalen = valid_length  # 更新实际数据长度

                for i in range(valid_length):
                    # 从帧头位置开始复制，填充到frame.data缓冲区
                    frame.data[i] = frame_data[start_idx + i]
                success, err = gw13762_check(affair, 1)
                print(f"\n校验结果: {'成功' if success else '失败'}")
                print(f"错误码: 0x{err:02X}")
                if err != 0xFF:
                    log_wp(frame_data)
                    log_wp(f"校验失败: 错误码=0x{err:02X}")
                    continue

                # ... 填充数据到affair对象 ...

                # success, err = gw13762_check(affair, dir=0)  # 调用校验解析函数

                # 3. 处理解析结果
                if success:
                    frame = affair.p_src.local.frame
                    result = f"解析成功: AFN=0x{frame.afn:02X}, FN=0x{frame.fn:02X}, 数据长度={frame.bufflen}"
                    self.parse_result_signal.emit(result)
                else:
                    self.parse_result_signal.emit(f"解析失败: 错误码=0x{err:02X}")
            except Exception as e:
                self.parse_result_signal.emit(f"解析线程异常: {str(e)}")
                log_wp(f"解析线程异常: {str(e)}")

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()