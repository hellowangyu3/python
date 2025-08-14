#这个文件在所有配置项都配置完成后，收到开始升级按键，开始升级
# 循环的往upgrade_fifo队列中发送数据，等待upgrade_fifo中数据为空-即被其他线程读完了
#升级完成后调用自身函数3，将数据更新-进行版本比对，


from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal
import PyQt6.QtCore as QtCore
import serial_bsp
from kfifo import KFifoAps
upgrade_fifo = KFifoAps()
import time
import log
import config
from protocol.gw13762 import create_default_frame
from log import log_wp ,LOG_PROTOCOL_CMD,log_info
from log import LOG_PROTOCOL_CMD
import queue
from common import *
from Upgrade_file_opt import get_file_version
from Upgrade_file_opt import crop_file_by_size ,read_line_with_count,create_file_info_bytes,list_to_hex_str
import time

parse_file1_path = "./firmware_output1.txt"
parse_file2_path = "./firmware_output2.txt"

class upgradeStateMachine:
    
    STATE_0 = 0
    STATE_1 = 1
    STATE_2 = 2
    STATE_INIT = 15
    STATE_EXITS = 255

    def __init__(self):
        self.state = self.STATE_INIT
        self.rcnt = 0
        # self.test_cnt = 0   # 测试轮次用于帧长增加
        self.currt_data_file = ""  # 当前升级数据文件路径
        self.dat_count_total = 0  # 当前升级数据总数
        self.currt_data_cnt = 0#当前应该传输哪一行数据了
        self.send_cnt = 0  # 发送次数
        self.currt_file_upgrade_prease = "./currt_file_upgrade_prease.txt"#解析文件放这里
        self.state_table = {
            self.STATE_INIT: self.state_init,
            self.STATE_0: self.state0,
            self.STATE_1: self.state1,
            self.STATE_2: self.state2,
            # self.STATE_3: self.state3,
            self.STATE_EXITS: self.state_exits
        }
    def state_change(self, state):       
        if state == self.STATE_EXITS:
            return
        self.send_cnt = 0  # 发送次数
        print(f"状态机状态切换：{self.state} -> {state}")
        self.state = state
 


    def step(self):
        handler = self.state_table.get(self.state)
        if handler:
            handler()

    def state_init(self):
        # 当前帧长 = 测试轮次*步长+升级包帧长度
        if self.currt_data_file == "":
            self.currt_data_file = config.file1_path
        config.current_data_len = config.test_count * config.file_step_by_step + config.len_upgrade_frame
        if config.current_data_len > config.file_step_max_size:
            print(f"当前帧长{config.current_data_len}大于文件最大长度{config.file_step_max_size}")
            log.write_to_plain_text_3("测试结束！你先重启吧，之后的功能还没做呢")
            self.state_change(self.STATE_EXITS)
            return
        # 裁剪文件
        success, line_count = crop_file_by_size(self.currt_data_file , self.currt_file_upgrade_prease,config.current_data_len)
        if success:
            print(f"文件裁剪完成，共 {line_count} 行")
            log.log_info(LOG_PROTOCOL_CMD, f"文件裁剪完成，共 {line_count} 行, 文件路径: {self.currt_file_upgrade_prease},当前帧长{config.current_data_len}")
            self.dat_count_total = line_count
            self.state_change(self.STATE_0)
        else:
            print(f"文件裁剪失败")
            self.state_change(self.STATE_EXITS)


    def state0(self):
        #查询版本，选择升级文件，如果版本均一致，则直接退出不解释
        # 否则，读取升级文件，将其dat文件拆除
        # if config.file1_version == config.file2_version:
        #     log.write_to_plain_text_3("版本一致，无需升级")
        response_03F1_queue.queue.clear()
        veser_get_dat = create_default_frame(3,1,config.tx_ord,[])#查询版本
        print("hex:", ' '.join(f'{b:02X}' for b in veser_get_dat[0]))
        serial_send_fifo.put(veser_get_dat[0])
        send_len = serial_send_fifo.get_data_length()
        send_data = serial_send_fifo.read(send_len)
        self.send_cnt += 1
        print(f"发送数据长度：{send_len}, 发送数据：{' '.join(f'{b:02X}' for b in send_data)}")
        log_info(LOG_PROTOCOL_CMD, ' '.join(f'{b:02X}' for b in veser_get_dat[0]))
        try:
        # 阻塞等待应答，超时可自定义
            response = response_03F1_queue.get(timeout=5)
            log_info(LOG_PROTOCOL_CMD, "查询版本应答：" + str(response))
            print(f"厂商代码: {response['vendor_code']}, 芯片代码: {response['chip_code']}, 版本日期: {response['version_date']}, 版本号: {response['version']}")
            log_info(LOG_PROTOCOL_CMD, f"查询版本应答：{response}")
            version, version_date, internal_version, internal_date = get_file_version(config.file1_path)
            if int(version) == int(response['version']) and version_date == response['version_date']:
                log.write_to_plain_text_3(f"当前版本与升级文件相同{version}{version_date}")
                # log.info(LOG_PROTOCOL_CMD, f"当前版本与升级文件相同{version}{version_date}")
                if self.currt_data_file == config.file1_path:
                    self.currt_data_file = config.file2_path
                else:
                    self.currt_data_file = config.file1_path
                self.state_change(self.STATE_0)
                return
            self.state_change(self.STATE_1)
            config.tx_ord += 1
            return
        except queue.Empty:
            log.write_to_plain_text_3("查询版本超时")
            log_info(LOG_PROTOCOL_CMD, "查询版本超时")
        self.state_change(self.STATE_0)
        return
        # log.write_to_plain_text_3("TX:", ' '.join(f'{b:02X}' for b in veser_get_dat[0]))

        # ...初始化逻辑...
        # self.state = self.STATE_1

    def state1(self):
        # 准备工作，下发清除下装文件
        response_15F1_queue.queue.clear()
        veser_clean_dat = create_default_frame(0x15,1,config.tx_ord,[00,00,00,00,00,00,00,00,00,00,00,00])
        serial_send_fifo.put(veser_clean_dat[0])
        send_len = serial_send_fifo.get_data_length()
        send_data = serial_send_fifo.read(send_len)
        print(f"发送数据长度：{send_len}, 发送数据：{' '.join(f'{b:02X}' for b in send_data)}")
        try:
        # 阻塞等待应答，超时可自定义
            response = response_15F1_queue.get(timeout=5)
            log_info(LOG_PROTOCOL_CMD, "清除下装文件" + str(response))
            config.tx_ord += 1
            self.state_change(self.STATE_2)
            return
        except queue.Empty:
            log.write_to_plain_text_3("清除下装文件超时")
            log_info(LOG_PROTOCOL_CMD, "清除下装文件超时")
        self.state_change(self.STATE_0)
        return
    
    def state2(self):
        if self.currt_data_cnt >= self.dat_count_total:
            log.write_to_plain_text_3("升级文件发送完毕")
            config.test_count += 1
            self.state_change(self.STATE_INIT)
            time.sleep(10)
            return

        # 发送升级文件
        read_status, read_count, content = read_line_with_count(self.currt_file_upgrade_prease, self.currt_data_cnt)
        print(f"读取状态: {read_status}")
        print(f"读取次数: {read_count}")
        print(f"行内容: {content}")

        # 检查内容是否为空或无效
        if not content or len(content.strip()) == 0:
            log.write_to_plain_text_3(f"无效的文件内容，第{self.currt_data_cnt}行")
            self.state_change(self.STATE_EXITS)
            return

        # 转换内容为字节列表（修复重复代码）
        hex_parts = content.split()
        try:
            content_bytes = [int(hex_part, 16) for hex_part in hex_parts]
        except ValueError as e:
            log.write_to_plain_text_3(f"解析十六进制数据失败: {str(e)}")
            self.state_change(self.STATE_EXITS)
            return

        print(f"文件内容字节列表长度: {len(content_bytes)}")

        # 检查字节长度是否符合预期
        if len(content_bytes) != config.current_data_len:
            log.write_to_plain_text_3(f"字节长度不匹配，预期{config.current_data_len}，实际{len(content_bytes)}")
            self.state_change(self.STATE_EXITS)
            return

        # 生成文件信息字节并与内容合并
        info_bytes = create_file_info_bytes(
            file_identifier=3,  # 对应 03
            file_attribute=0,  # 对应 00
            file_command=0,  # 对应 00
            total_segments=self.dat_count_total,  # 使用实际总段数
            segment_identifier=self.currt_data_cnt,  # 当前段标识
            segment_length=config.current_data_len  # 段长度
        )
        # 合并文件信息和内容字节
        full_bytes = info_bytes + content_bytes

        # 新增：完整数据长度校验（防止堆溢出）
        MAX_FRAME_SIZE = 1024+15  # 根据协议设置最大允许长度
        info_length = len(info_bytes)
        content_length = len(content_bytes)
        total_length = info_length + content_length

        if total_length > MAX_FRAME_SIZE:
            log.write_to_plain_text_3(f"数据长度超过最大限制！总长度:{total_length}, 最大:{MAX_FRAME_SIZE}")
            self.state_change(self.STATE_EXITS)
            return

        # 生成帧并发送（添加异常捕获）
        try:
            gw13762_frame = create_default_frame(0x15, 1, config.tx_ord, full_bytes)
            # 检查帧生成结果是否有效
            if not gw13762_frame or len(gw13762_frame) == 0:
                raise ValueError("生成的协议帧为空")

            # 发送数据（限制单次发送大小）
            frame_data = gw13762_frame[0]
            if len(frame_data) > MAX_FRAME_SIZE:
                raise OverflowError(f"帧数据超出缓冲区大小:{len(frame_data)}")

            serial_send_fifo.put(frame_data)
            # 等待应答
            try:
                response = response_15F1_queue.get(timeout=5)
                # 验证响应是否有效字典
                if not isinstance(response, dict):
                    raise ValueError("响应不是有效的字典对象")

                log_info(LOG_PROTOCOL_CMD, "升级文件应答：" + str(response))

                # 检查响应中的必要键
                if 'serial_num' not in response or 'page_num' not in response:
                    raise KeyError("响应缺少必要的字段")

                if response['serial_num'] == config.tx_ord and response['page_num'] == self.currt_data_cnt:
                    log_info(LOG_PROTOCOL_CMD, f"升级文件发送成功，第{self.currt_data_cnt}行")
                    # 更新序号和计数器
                    config.tx_ord = (config.tx_ord + 1) % 256  # 使用模运算避免溢出
                    self.currt_data_cnt += 1
                    self.state_change(self.STATE_2)
                else:
                    log.log_info(LOG_PROTOCOL_CMD, f"serial_num: {response.get('serial_num')} page_num: {response.get('page_num')} {config.tx_ord} : {self.currt_data_cnt}")
                    log.write_to_plain_text_3(f"升级文件发送失败，第{self.currt_data_cnt}行")
                    self.state_change(self.STATE_EXITS)

            except queue.Empty:
                log.write_to_plain_text_3("15F1发送超时")
                self.send_cnt += 1
                if self.send_cnt >= 3:
                    self.state_change(self.STATE_EXITS)
            except (KeyError, ValueError) as e:
                log.write_to_plain_text_3(f"响应解析错误: {str(e)}")
                self.state_change(self.STATE_EXITS)

        except Exception as e:
            log.write_to_plain_text_3(f"帧生成失败: {str(e)}")
            self.state_change(self.STATE_EXITS)
        return




    def state_wait_ack(self):
        log.write_to_plain_text_3("状态：WAIT_ACK")
        # ...等待应答逻辑...
        self.state_change(self.STATE_0)
        return
    def state_exits(self):
        log.write_to_plain_text_3("状态：EXITS")
        # ...退出逻辑...
        self.state_change(self.STATE_EXITS)
        return



upgrade_addair = upgradeStateMachine()
class UpgradeThread(QThread):
    """升级线程：接收配置参数并执行升级逻辑，通过信号返回日志"""
    log_signal = pyqtSignal(str)  # 发送日志信息给主窗口

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False  # 线程运行状态标志
        self.upgrade_path = None
        self.upgrade_total = 0
        self.upgrade_state_machine = upgradeStateMachine()

    @pyqtSlot(dict)  # 接收主窗口发送的配置参数
    def run_upgrade(self, config):
        # self.config = config
        self.is_running = True
        log.write_to_plain_text_3("升级线程启动，开始执行升级...")
        # self.upgrade_state_machine = upgradeStateMachine()
        self.start()  # 启动线程，自动调用run()


    def run(self):
        while self.is_running:
            self.upgrade_state_machine.step()
            # log.write_to_plain_text_3("升级线程启动，开始执行升级...")
            # time.sleep(0.5)

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
            log.write_to_plain_text_3(f"成功读取升级文件：{file_path}，大小：{len(self.firmware_data)}字节")
            # 按128字节分割数据并打印

            output_path = "./firmware_output.txt"
            with open(output_path, "w") as out_f:
                for i in range(0, len(self.firmware_data), 128):
                    # 截取128字节数据并转换为十六进制字符串
                    chunk = self.firmware_data[i:i + 128]
                    hex_line = ' '.join(f'{byte:02x}' for byte in chunk)
                    out_f.write(hex_line + '\n')
            log.write_to_plain_text_3(f"数据已成功写入文件：{output_path}，共{len(self.firmware_data) // 128 + 1}行")

            return True

        except Exception as e:
            log.write_to_plain_text_3(f"读取升级文件失败: {str(e)}")
            return False

    def _send_firmware_data(self, frame_length):
        """分帧发送固件数据（内部辅助方法）"""
        # ... 实现分帧发送逻辑（使用serial_bsp发送数据）...
        pass

    def stop_upgrade(self):
        """停止升级线程（供主窗口调用）"""
        self.is_running = False
        log.write_to_plain_text_3("升级线程已停止")



class UpgradeThread(QThread):
    """升级线程：接收配置参数并执行升级逻辑，通过信号返回日志"""
    log_signal = pyqtSignal(str)  # 发送日志信息给主窗口

    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False  # 线程运行状态标志
        self.upgrade_state_machine = upgradeStateMachine()
        self.lock = QtCore.QMutex()  # 添加线程锁防止并发问题

    @pyqtSlot(dict)  # 接收主窗口发送的配置参数
    def run_upgrade(self, config):
        """启动升级流程（确保线程安全）"""
        self.lock.lock()
        try:
            if not self.is_running:
                self.is_running = True
                self.config = config
                self.start()  # 启动线程的run()方法
                log.write_to_plain_text_3("升级线程已启动")
            else:
                log.write_to_plain_text_3("升级线程已在运行中")
        finally:
            self.lock.unlock()

    def run(self):
        """线程主循环（仅执行一次）"""
        while self.is_running:
            self.upgrade_state_machine.step()
            time.sleep(0.01)  # 添加微小延迟防止CPU占用过高
        log.write_to_plain_text_3("升级线程已停止")

    def stop_upgrade(self):
        """停止升级线程（线程安全版）"""
        self.lock.lock()
        try:
            self.is_running = False
        finally:
            self.lock.unlock()