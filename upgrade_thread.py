#这个文件在所有配置项都配置完成后，收到开始升级按键，开始升级
# 循环的往upgrade_fifo队列中发送数据，等待upgrade_fifo中数据为空-即被其他线程读完了
#升级完成后调用自身函数3，将数据更新-进行版本比对，


from PyQt6.QtCore import QThread, pyqtSlot, pyqtSignal
import serial_bsp
import log
from kfifo import KFifoAps
upgrade_fifo = KFifoAps()
import log
import time
import config
from protocol.gw13762 import gw13762_build_frame, SApsAffair,create_default_frame


class upgradeStateMachine:
    STATE_INIT = 0
    STATE_SEND = 1
    STATE_WAIT_ACK = 2

    def __init__(self):
        self.state = self.STATE_INIT
        self.state_table = {
            self.STATE_INIT: self.state_init,
            self.STATE_SEND: self.state_send,
            self.STATE_WAIT_ACK: self.state_wait_ack,
            self.STATE_EXITS: self.state_exits
        }

    def step(self):
        handler = self.state_table.get(self.state)
        if handler:
            handler()

    def state_init(self):
        #查询版本，选择升级文件，如果版本均一致，则直接退出不解释
        # 否则，读取升级文件，将其dat文件拆除
        # if config.file1_version == config.file2_version:
        #     log.write_to_plain_text_3("版本一致，无需升级")

        veser_get_dat = create_default_frame(3,1,config.tx_ord,[])#查询版本
        print("hex:", ' '.join(f'{b:02X}' for b in veser_get_dat[0]))
        log.write_to_plain_text_3("TX:", ' '.join(f'{b:02X}' for b in veser_get_dat[0]))

        # ...初始化逻辑...
        self.state = self.STATE_SEND

    def state_send(self):
        log.write_to_plain_text_3("状态：SEND")
        # ...发送逻辑...
        self.state = self.STATE_WAIT_ACK

    def state_wait_ack(self):
        log.write_to_plain_text_3("状态：WAIT_ACK")
        # ...等待应答逻辑...
        self.state = self.STATE_INIT    
    def state_exits(self):
        log.write_to_plain_text_3("状态：EXITS")
        # ...退出逻辑...
        self.state = self.STATE_EXITS



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
            time.sleep(1)

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
