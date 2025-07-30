import sys
import time  # 新增：导入time模块（用于生成时间戳）
import main_interface
from PyQt6 import QtWidgets, QtCore  # 新增：导入QtCore模块（含QTimer）
from main_interface import Ui_MainWindow  # 导入生成的UI类
import log
from serial_bsp import SerialInterface

LOG_WP = log.LOG_WP
serial_if = SerialInterface()

# 新增：创建主窗口逻辑类（继承QMainWindow和Ui_MainWindow）
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 初始化UI
        self.serial_input = ""  # 存储串口参数
        self.serial_open = False  # 串口状态

        # 新增：创建定时器（用于定时读取串口数据）
        self.serial_timer = QtCore.QTimer(self)
        self.serial_timer.timeout.connect(self.read_serial_data)  # 绑定定时读取方法
        self.serial_timer.setInterval(100)  # 读取间隔：100ms（0.1秒）

        # 绑定菜单点击事件
        self.actionNULL1.triggered.connect(self.toggle_serial_port)
        self.actionNULL1.setText("打开串口")
        log.set_plain_text_edit_3(self.plainTextEdit_3)  # 传递文本框引用

    # 新增：定时读取串口数据并显示到文本框
    def read_serial_data(self):
        """定时读取串口数据并写入plainTextEdit_3"""
        if self.serial_open:  # 仅在串口打开时读取
            try:
                success, data = serial_if.read_data()  # 调用serial_bsp的读取方法
                if success and data:  # 读取成功且数据非空
                    # 生成带日期的完整时间戳（与LOG_WP格式统一，避免重复）
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                    # 仅保留一个时间戳（删除多余的时间格式）
                    log.write_to_plain_text_3(f"收到数据: {data}")
                    print(data)
            except Exception as e:
                log.write_to_plain_text_3(f"读取数据异常: {str(e)}")

    # 重命名方法：处理打开/关闭串口切换逻辑
    def toggle_serial_port(self):
        """切换串口状态（打开/关闭）并更新菜单名称"""
        if not self.serial_open:
            # 状态：关闭 → 打开串口（显示输入对话框）
            input_str, ok = QtWidgets.QInputDialog.getText(
                self, "打开串口", "请输入串口参数（如COM1:9600）：",
                text=self.serial_input
            )
            if ok and input_str:
                self.serial_input = input_str
                # 调用serial_if实例的open_serial方法（而非类方法）
                success, msg = serial_if.open_serial(self.serial_input)
                self.serial_open = success  # 更新状态为打开结果
                if ok and self.serial_open:  # 串口打开成功
                    self.actionNULL1.setText("关闭串口")  # 菜单名称改为“关闭串口”
                    LOG_WP(f"串口已打开，参数：{self.serial_input}")
                    log.write_to_plain_text_3(f"串口已打开，参数：{self.serial_input}")
                    self.serial_timer.start()  # 新增：启动定时器（开始读取数据）
                else:
                    LOG_WP(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    self.serial_open = False  # 打开失败，重置状态
                    self.actionNULL1.setText("打开串口")  # 菜单名称恢复为“打开串口”
                    # 添加 f 前缀，解析 {self.serial_input} 和 {msg}
                    log.write_to_plain_text_3(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    #添加弹窗打开失败
                    QtWidgets.QMessageBox.critical(self, "打开串口失败", f"串口打开失败，错误信息：{msg}")
        else:
            # 状态：打开 → 关闭串口（重置状态）
            self.serial_open = False  # 更新状态为关闭
            self.actionNULL1.setText("打开串口")  # 菜单名称恢复为“打开串口”
            LOG_WP(f"串口已关闭")


# 保留唯一主程序入口
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MainWindow()  # 实例化自定义窗口类
    MainWindow.show()
    sys.exit(app.exec())



