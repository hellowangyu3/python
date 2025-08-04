import time

from PyQt6.QtCore import QThread, pyqtSignal
import queue
from protocol.gw13762 import gw13762_check, SApsAffair ,dispatch_by_afn_fn
import log
from serial_thread import serial_recv_fifo
from kfifo import KFifoAps

uart_send_fifo = KFifoAps()

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
        """线程主函数，支持断帧、多帧、混合帧处理"""
        self.parse_result_signal.emit("解析线程已启动")
        buffer = b''  # 缓存未处理完的数据
        last_recv_time = time.time()
        while self.running:
            time.sleep(0.1)
            try:
                fifolen = serial_recv_fifo.get_data_length()
                if fifolen > 0:
                    frame_data = serial_recv_fifo.get(fifolen)
                    # 强制保证 frame_data 和 buffer 都是 bytes 类型
                    if isinstance(frame_data, list):
                        frame_data = bytes(frame_data)
                    if not isinstance(buffer, bytes):
                        buffer = bytes(buffer)
                    buffer += frame_data
                    last_recv_time = time.time()
                else:
                    # 超时判断
                    if time.time() - last_recv_time > 2:
                        # self.parse_result_signal.emit("2秒未收到完整帧，清空缓存")
                        # log.log_info(log.LOG_DEBUG_CMD, "2秒未收到完整帧，清空缓存")
                        buffer = b''
                        last_recv_time = time.time()
                    continue

                while True:
                    # 查找帧头0x68
                    idx = buffer.find(b'\x68')
                    if idx == -1:
                        # 没有帧头，丢弃无效数据
                        if buffer:
                            self.parse_result_signal.emit("未找到帧头0x68，跳过无效数据")
                            log.log_info(log.LOG_DEBUG_CMD, "未找到帧头0x68，跳过无效数据")
                        buffer = b''
                        break
                    # 帧头后至少要有2字节长度
                    if len(buffer) < idx + 3:
                        # 数据不够，等待下次补齐
                        break
                    # 取长度字段（假设小端）
                    length_bytes = buffer[idx+1:idx+3]
                    frame_len = int.from_bytes(length_bytes, 'little')
                    total_len = frame_len
                    # 帧长度大于255，清空缓存
                    if frame_len > 255:
                        self.parse_result_signal.emit(f"帧长度超限({frame_len})，清空缓存")
                        log.log_info(log.LOG_DEBUG_CMD, f"帧长度超限({frame_len})，清空缓存")
                        buffer = b''
                        break
                    # 帧头+长度+数据 = total_len
                    if len(buffer) < idx + total_len:
                        # 数据不够，等待下次补齐
                        break
                    # 取出一帧数据
                    one_frame = buffer[idx:idx+total_len]
                    # 处理一帧
                    print(f"comport recv {one_frame}")
                    frame = affair.p_src.local
                    frame.datalen = len(one_frame)
                    # 拷贝到frame.data，兼容bytearray/c_ubyte_Array类型
                    try:
                        if hasattr(frame, 'data'):
                            # 如果是bytearray或支持切片赋值
                            if isinstance(frame.data, (bytearray, memoryview)):
                                frame.data[:len(one_frame)] = one_frame
                            # 如果是ctypes数组（如c_ubyte_Array_4096）
                            elif hasattr(frame.data, '__setitem__') and hasattr(frame.data, '__len__'):
                                for i in range(len(one_frame)):
                                    frame.data[i] = one_frame[i]
                            else:
                                # 其他类型，尝试直接赋值bytes
                                frame.data = one_frame
                    except Exception as ee:
                        self.parse_result_signal.emit(f"frame.data赋值异常: {str(ee)}")
                    success, err = gw13762_check(affair, 1)
                    print(f"\n校验结果: {'成功' if success else '失败'}")
                    print(f"错误码: 0x{err:02X}")
                    if err != 0xFF or not success:
                        self.parse_result_signal.emit(f"解析失败: 错误码=0x{err:02X}，清空缓存")
                        log.log_info(log.LOG_DEBUG_CMD, f"解析失败: 错误码=0x{err:02X}，清空缓存")
                        buffer = b''
                        break
                    # 处理解析结果
                    frame2 = affair.p_src.local.frame
                    result = f"解析成功: AFN=0x{frame2.afn:02X}, FN=0x{frame2.fn:02X}, 数据长度={frame2.bufflen}"
                    self.parse_result_signal.emit(result)
                    # 移除已处理帧，继续处理剩余
                    buffer = buffer[idx+total_len:]
            except Exception as e:
                self.parse_result_signal.emit(f"解析线程异常: {str(e)}")
                log.log_info(log.LOG_DEBUG_CMD, f"解析线程异常: {str(e)}")

    def stop(self):
        """停止线程"""
        self.running = False
        self.wait()