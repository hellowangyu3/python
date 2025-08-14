import sys
import time
import os
import log 
from log import start_log_thread
import config
from PyQt6 import QtWidgets
import PyQt6.QtCore as QtCore
from PyQt6.QtCore import QThread, pyqtSignal

import main_interface
import Upgrade_file_opt
from main_interface import Ui_MainWindow
from serial_bsp import SerialInterface
from Upgrade_file_opt import get_file_version
from serial_thread import SerialThread
from comport.com_poer import ParsingThread

# 初始化日志和串口接口
log_wp = log.log_wp
serial_if = SerialInterface()
import faulthandler
import sys

import tracemalloc
import sys
from PyQt6.QtCore import QThread

class UpgradeThread(QThread):
    def run(self):
        # 启动内存追踪
        tracemalloc.start()
        # 记录初始快照
        snapshot_initial = tracemalloc.take_snapshot()
        try:
            while self.is_running:
                self.upgrade_state_machine.step()
                time.sleep(0.01)
        except Exception as e:
            # 捕获异常时记录快照
            snapshot_crash = tracemalloc.take_snapshot()
            self.analyze_memory_leak(snapshot_initial, snapshot_crash)
            sys.exit(1)
        finally:
            tracemalloc.stop()

    def analyze_memory_leak(self, initial, crash):
        """对比崩溃前后的内存快照，输出异常增长的代码位置"""
        top_stats = crash.compare_to(initial, 'lineno')
        log.write_to_plain_text_3("===== 崩溃前内存异常增长 =====")
        for stat in top_stats[:10]:  # 取前10个最可能的问题点
            log.write_to_plain_text_3(f"{stat.filename}:{stat.lineno} "
                                     f"内存增长: {stat.size_diff_human} "
                                     f"对象数: {stat.count_diff}")
            
            
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    # 定义升级开始信号（传递配置参数字典给线程）
    start_upgrade_signal = pyqtSignal(dict)
    stop_upgrade_signal = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 初始化UI

        # 串口相关变量
        self.serial_input = ""  # 存储串口参数
        self.serial_open = False  # 串口状态

        # 文件路径相关变量
        self.file1_path = ""  # 存储文件1路径
        self.file1_name = ""  # 存储文件1名称
        self.file2_path = ""  # 存储文件2路径
        self.file2_name = ""  # 存储文件2名称

        # 绑定按钮事件
        self.pushButton_ile1.clicked.connect(lambda: self.select_file("file1"))
        self.pushButton_feil2.clicked.connect(lambda: self.select_file("file2"))
        self.pushButtonupgrade.clicked.connect(self.upgrade_start)

        # 绑定菜单事件
        self.actionNULL1.triggered.connect(self.toggle_serial_port)
        self.actionNULL1.setText("打开串口")
        log.set_plain_text_edit_3(self.plainTextEdit_3)  # 传递文本框引用
        log.set_label_7_text_edit(self.label_7)
                # 初始化串口线程
        self.serial_thread = SerialThread(serial_if)    #把bsp的串口传给线程，让它去循环的读取数据
        self.serial_thread.data_received.connect(log.write_to_plain_text_3)
        self.serial_thread.start_thread()  # 启动串口线程

        # 初始化解析线程
        self.parse_thread = ParsingThread()
        # ✅ 连接解析线程的信号到日志显示（使用正确的信号名称）
        self.parse_thread.parse_result_signal.connect(log.write_to_plain_text_3)
        self.parse_thread.start()  # ✅ 使用QThread内置的start()方法启动线程

        self.log_thread = start_log_thread()

        # 配置SpinBox
        self.spinBox_2.setMaximum(2048)
        self.spinBox.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox.value(), 1))
        self.spinBox_2.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox_2.value(), 2))
        self.spinBox_max_size.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox_max_size.value(), 3))
        self.spinBox_step_size.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox_step_size.value(), 4))



        # 初始化升级线程
        from upgrade_thread import UpgradeThread
        self.upgrade_thread = UpgradeThread()
        self.start_upgrade_signal.connect(self.upgrade_thread.run_upgrade)
        self.stop_upgrade_signal.connect(self.upgrade_thread.stop_upgrade)
        self.upgrade_thread.log_signal.connect(log.write_to_plain_text_3)


        # 在程序入口处开启
        faulthandler.enable(file=open("./crash_log.txt", "w"))  # 崩溃日志写入文件

    def toggle_serial_port(self):
        """切换串口状态（打开/关闭）并更新菜单名称"""
        if not self.serial_open:
            # 状态：关闭 → 打开串口
            input_str, ok = QtWidgets.QInputDialog.getText(
                self, "打开串口", "请输入串口参数（如COM3,9600,E,8,1）",
                text=self.serial_input
            )

            if ok and input_str:
                self.serial_input = input_str
                success, msg = serial_if.open_serial(self.serial_input)
                self.serial_open = success

                if self.serial_open:
                    config.serial_status = "打开"
                    self.actionNULL1.setText("关闭串口")
                    log_wp(f"串口已打开，参数：{self.serial_input}")
                    config.serial_str = input_str
                    log.write_to_plain_text_3(f"串口已打开，参数：{self.serial_input}")
                else:
                    log_wp(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    self.serial_open = False
                    config.serial_status = "关闭"
                    config.serial_str = f"{msg}"
                    self.actionNULL1.setText("打开串口")
                    log.write_to_plain_text_3(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    QtWidgets.QMessageBox.critical(self, "打开串口失败", f"串口打开失败，错误信息：{msg}")
        else:
            # 状态：打开 → 关闭串口
            self.serial_open = False
            self.actionNULL1.setText("打开串口")

            try:
                import threading
                close_thread = threading.Thread(target=serial_if.close_serial)
                close_thread.daemon = True
                close_thread.start()
                close_thread.join(timeout=0.5)
            except Exception as e:
                log.write_to_plain_text_3(f"关闭串口异常: {str(e)}")

            log_wp(f"串口已关闭")

    def select_file(self, file_type):
        """通用文件选择方法（支持file1/file2）"""
        # 文件配置参数
        self_file_config = {
            "file1": {
                "dialog_title": "选择升级文件1",
                "label_widget": self.label_2,
                "path_var": "file1_path",
                "name_var": "file1_name",
                "log_prefix": "升级文件1"
            },
            "file2": {
                "dialog_title": "选择升级文件2",
                "label_widget": self.label_3,
                "path_var": "file2_path",
                "name_var": "file2_name",
                "log_prefix": "升级文件2"
            }
        }.get(file_type)

        if not self_file_config:
            log.write_to_plain_text_3(f"不支持的文件类型: {file_type}")
            return

        # 打开文件选择对话框
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, self_file_config["dialog_title"], "", "升级文件 (*.dat)"
        )

        if file_path:
            # 更新文件路径和名称
            setattr(self, self_file_config["path_var"], file_path)
            file_name = os.path.basename(file_path)
            setattr(self, self_file_config["name_var"], file_name)

            # 更新UI显示
            self_file_config["label_widget"].setText(f"{self_file_config['log_prefix']} 名称：{file_name}")
            self_file_config["label_widget"].setToolTip(f"完整路径：{file_path}")
            log.write_to_plain_text_3(f"已选择{self_file_config['log_prefix']}：{file_path}")

            # 处理版本信息
            if file_name:
                try:
                    version, version_date, internal_version, internal_date = get_file_version(file_path)
                    info_str = (
                        f"sv：   {version}       "
                        f"date： {version_date} \n"
                        f"isv：  {internal_version}       "
                        f"idate： {internal_date}"
                    )

                    # 更新对应文本框
                    if file_type == "file1":
                        config.file1_path = file_path
                        config.file1_version = info_str
                        self.plainTextEdit_2.setPlainText(info_str)
                    elif file_type == "file2":
                        config.file2_path = file_path
                        config.file2_version = info_str
                        self.plainTextEdit.setPlainText(info_str)

                    log.write_to_plain_text_3(f"{self_file_config['log_prefix']}版本信息：\n{info_str}")

                    # 检查两个文件版本是否相同
                    if self.file1_path and self.file2_path:
                        try:
                            v1, d1, iv1, id1 = get_file_version(self.file1_path)
                            v2, d2, iv2, id2 = get_file_version(self.file2_path)

                            if v1 == v2 and d1 == d2 and iv1 == iv2 and id1 == id2:
                                error_msg = "错误：两个升级文件版本信息完全相同！"
                                log.write_to_plain_text_3(error_msg)
                                QtWidgets.QMessageBox.critical(self, "版本重复错误", error_msg)
                        except Exception as e:
                            log.write_to_plain_text_3(f"版本对比失败：{str(e)}")

                except Exception as e:
                    log.write_to_plain_text_3(f"{self_file_config['log_prefix']}版本识别失败：{str(e)}")
                    QtWidgets.QMessageBox.critical(self, "版本识别失败", f"版本识别失败，错误信息：{str(e)}")

    @staticmethod
    def save_spinbox_value(value, spinbox_type):
        """将spinBox当前值保存到全局配置"""
        try:
            if spinbox_type == 1:
                config.test_count = value
            elif spinbox_type == 2:
                config.len_upgrade_frame = value
            elif spinbox_type == 3:
                config.file_step_max_size = value
            elif spinbox_type == 4:
                config.file_step_by_step = value
            else:
                log.write_to_plain_text_3(f"ERR:不支持的spinBox类型: {spinbox_type}")
                return
            log_wp(f"已保存spinBox{spinbox_type}值：{value}")
        except Exception as e:
            log.write_to_plain_text_3(f"保存spinBox值失败: {str(e)}")
            print(f"save_spinbox_value异常: {str(e)}")



    def upgrade_start(self):
        """开始升级流程（添加线程状态检查）"""
        # 检查配置有效性
        config.current_data_len = config.len_upgrade_frame #初始帧长
        if config.current_data_len is None:
            log.write_to_plain_text_3(f"当前传输文件帧长未设置，当前值：{config.current_data_len}")
            return
        config_result = config.config_val_check()
        if config_result is True:
            # 配置有效，准备升级参数
            log_wp("配置值有效，开始升级")
            config.print_config_value()
            #     return  # 格式或数值错误，直接返回

            upgrade_config = {
                "file1_path": config.file1_path,
                "file2_path": config.file2_path,
                "frame_length": config.spin_box_2_value,
                "serial_str": config.serial_str,
                "test_rounds": config.test_count,
                "upgrade_status": self.pushButtonupgrade.text()
            }
            print(self.pushButtonupgrade.text())
            # 切换按钮文本
            if self.pushButtonupgrade.text() == "停止测试":
                # self.horizontalSlider.setEnabled(True)
                self.pushButtonupgrade.setText("开始测试")
                # 发送停止信号
                self.stop_upgrade_signal.emit(upgrade_config)
            else:
                # 新增：检查升级线程状态
                if not self.upgrade_thread.isRunning():
                    self.pushButtonupgrade.setText("停止测试")
                    self.start_upgrade_signal.emit(upgrade_config)
                else:
                    log.write_to_plain_text_3("升级线程已在运行中，请勿重复启动")

            # self.horizontalSlider.setEnabled(False)  # 开始升级后禁止修改
            # 发送升级信号
            self.start_upgrade_signal.emit(upgrade_config)
        else:
            # 配置无效，显示错误信息
            error_items = ", ".join(config_result.keys())
            error_msg = f"配置错误：以下项未设置或无效：\n{error_items}"

            QtWidgets.QMessageBox.critical(self, "配置检查失败", error_msg)
            log_wp(error_msg)
            return


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())