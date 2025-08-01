from PyQt6.QtCore import QThread, pyqtSignal
import queue
from protocol.gw13762 import gw13762_check, SApsAffair

class ParsingThread(QThread):
    """协议解析线程"""
    parse_result_signal = pyqtSignal(str)  # 解析结果信号

    def __init__(self):
        super().__init__()
        self.data_queue = queue.Queue()  # 数据队列
        self.running = True

    def add_data(self, data):
        """添加待解析数据到队列"""
        self.data_queue.put(data)

    def run(self):
        """线程主函数（伪代码）"""
        self.parse_result_signal.emit("解析线程已启动")

        while self.running:
            try:
                # 1. 从队列获取数据（超时100ms）
                data = self.data_queue.get(timeout=0.1)

                # 2. 调用13762协议解析函数（伪代码）
                # 假设使用之前定义的gw13762_check函数进行解
                affair = SApsAffair()
                # ... 填充数据到affair对象 ...

                success, err = gw13762_check(affair, dir=0)  # 调用校验解析函数

                # 3. 处理解析结果
                if success:
                    frame = affair.p_src.local.frame
                    result = f"解析成功: AFN=0x{frame.afn:02X}, FN=0x{frame.fn:02X}, 数据长度={frame.bufflen}"
                    self.parse_result_signal.emit(result)
                else:
                    self.parse_result_signal.emit(f"解析失败: 错误码=0x{err:02X}")

            except queue.Empty:
                continue  # 队列为空时继续等待
            except Exception as e:
                self.parse_result_signal.emit(f"解析线程异常: {str(e)}")

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()