import sys
import time  # 新增：导入time模块（用于生成时间戳）
import main_interface
import os
import Upgrade_file_opt
from PyQt6 import QtWidgets, QtCore  # 新增：导入QtCore模块（含QTimer）
from main_interface import Ui_MainWindow  # 导入生成的UI类
import log
from serial_bsp import SerialInterface
from Upgrade_file_opt import get_file_version  # 新增：导入get_file_version方法


log_wp = log.log_wp
serial_if = SerialInterface()

# 新增：创建主窗口逻辑类（继承QMainWindow和Ui_MainWindow）
class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)  # 初始化UI
        self.serial_input = ""  # 存储串口参数
        self.serial_open = False  # 串口状态

        self.file1_path = ""  # 存储文件1路径
        self.file1_name = ""  # 存储文件1名称
        self.file2_path = ""  # 存储文件2路径
        self.file2_name = ""  # 存储文件2名称
        # 绑定文件选择按钮事件
        self.pushButton_ile1.clicked.connect(lambda: self.select_file("file1"))
        self.pushButton_feil2.clicked.connect(lambda: self.select_file("file2"))
        self.pushButtonupgrade.clicked.connect(self.upgrade_start)

        self.spinBox_2.setMaximum(2048)
        # 修复：使用 lambda 传递额外参数（spinbox_type）
        # 修改：将 valueChanged 替换为 editingFinished 信号（输入完成后触发）
        # spinBox 类型1（输入完成后保存）
        self.spinBox.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox.value(), 1))
        # spinBox_2 类型2（输入完成后保存）
        self.spinBox_2.editingFinished.connect(lambda: self.save_spinbox_value(self.spinBox_2.value(), 2))
        # 创建定时器（用于定时读取串口数据）
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
                    # 生成带日期的完整时间戳（与log_wp格式统一，避免重复）
                    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
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
                import config
                self.serial_input = input_str
                # 调用serial_if实例的open_serial方法（而非类方法）
                success, msg = serial_if.open_serial(self.serial_input)
                self.serial_open = success  # 更新状态为打开结果
                if ok and self.serial_open:  # 串口打开成功
                    self.actionNULL1.setText("关闭串口")  # 菜单名称改为“关闭串口”
                    log_wp(f"串口已打开，参数：{self.serial_input}")
                    config.serial_str = input_str
                    log.write_to_plain_text_3(f"串口已打开，参数：{self.serial_input}")
                    self.serial_timer.start()  # 新增：启动定时器（开始读取数据）
                else:
                    log_wp(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    self.serial_open = False  # 打开失败，重置状态
                    config.serial_str = f"{msg}"
                    self.actionNULL1.setText("打开串口")  # 菜单名称恢复为“打开串口”
                    # 添加 f 前缀，解析 {self.serial_input} 和 {msg}
                    log.write_to_plain_text_3(f"串口打开失败，参数：{self.serial_input}，错误信息：{msg}")
                    #添加弹窗打开失败
                    QtWidgets.QMessageBox.critical(self, "打开串口失败", f"串口打开失败，错误信息：{msg}")
        else:
            # 状态：打开 → 关闭串口（重置状态）
            self.serial_open = False  # 更新状态为关闭
            self.actionNULL1.setText("打开串口")  # 菜单名称恢复为“打开串口”
            log_wp(f"串口已关闭")

    # 合并文件1和文件2的选择逻辑（消除冗余）
    def select_file(self, file_type):
        """通用文件选择方法（支持file1/file2）"""
        # 根据文件类型配置参数（标题、标签、变量名）
        config = {
            "file1": {
                "dialog_title": "选择升级文件1",
                "label_widget": self.label_2,  # 文件1对应label_2
                "path_var": "file1_path",       # 存储路径的变量名
                "name_var": "file1_name",       # 存储文件名的变量名
                "log_prefix": "升级文件1"        # 日志前缀
            },
            "file2": {
                "dialog_title": "选择升级文件2",
                "label_widget": self.label_3,  # 文件2对应label_3
                "path_var": "file2_path",
                "name_var": "file2_name",
                "log_prefix": "升级文件2"
            }
        }.get(file_type)

        if not config:
            log.write_to_plain_text_3(f"不支持的文件类型: {file_type}")
            return

        # 打开文件选择对话框（复用核心逻辑）
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, config["dialog_title"], "", "升级文件 (*.dat)"
        )
        if file_path:
            # 动态更新实例变量（文件路径和名称）
            setattr(self, config["path_var"], file_path)  # 等价于 self.file1_path/file2_path = file_path
            file_name = os.path.basename(file_path)
            setattr(self, config["name_var"], file_name)  # 等价于 self.file1_name/file2_name = file_name

            # 更新UI标签和提示
            config["label_widget"].setText(f"{config['log_prefix']} 名称：{file_name}")
            config["label_widget"].setToolTip(f"完整路径：{file_path}")

            # 记录日志
            log.write_to_plain_text_3(f"已选择{config['log_prefix']}：{file_path}")
            if file_name:
                # 新增：调用版本识别函数并区分文件类型
                try:
                    # 获取版本信息元组（版本号、版本日期、内部版本号、内部版本日期）
                    version, version_date, internal_version, internal_date = get_file_version(file_path)

                    # 格式化版本信息字符串
                    info_str = (
                        f"sv：{version}"
                        f"date：{version_date}\n"
                        f"isv：{internal_version}"
                        f"idate：{internal_date}"
                    )

                    # 根据文件类型显示到对应文本框
                    if file_type == "file1":
                        self.plainTextEdit_2.setPlainText(info_str)  # 文件1 → plainTextEdit_2
                    elif file_type == "file2":
                        self.plainTextEdit.setPlainText(info_str)    # 文件2 → plainTextEdit

                    # 日志文本框记录完整信息
                    log.write_to_plain_text_3(f"{config['log_prefix']}版本信息：\n{info_str}")

                    # 新增：检查两个文件版本信息是否完全相同
                    if self.file1_path and self.file2_path:  # 确保两个文件都已选择
                        # 获取两个文件的版本信息
                        try:
                            # 文件1版本信息
                            v1, d1, iv1, id1 = get_file_version(self.file1_path)
                            # 文件2版本信息
                            v2, d2, iv2, id2 = get_file_version(self.file2_path)

                            # 检查所有版本字段是否完全相同
                            if v1 == v2 and d1 == d2 and iv1 == iv2 and id1 == id2:
                                error_msg = "错误：两个升级文件版本信息完全相同！"
                                log.write_to_plain_text_3(error_msg)
                                QtWidgets.QMessageBox.critical(self, "版本重复错误", error_msg)
                        except Exception as e:
                            log.write_to_plain_text_3(f"版本对比失败：{str(e)}")

                except Exception as e:
                    log.write_to_plain_text_3(f"{config['log_prefix']}版本识别失败：{str(e)}")
                    QtWidgets.QMessageBox.critical(self, "版本识别失败", f"版本识别失败，错误信息：{str(e)}")



# 新增：保存spinBox值到全局配置
    # 修复：移至类内部，添加 self 作为第一个参数
    def save_spinbox_value(self, value, spinbox_type):
        """将spinBox当前值保存到全局配置"""
        try:  # 新增：捕获异常避免程序崩溃
            import config  # 新增：导入config模块（访问全局配置变量）
            if spinbox_type == 1:
                config.spin_box_value = value  # 更新全局变量
            elif spinbox_type == 2:
                config.spin_box_2_value = value  # 更新全局变量
            else:
                log.write_to_plain_text_3(f"ERR:不支持的spinBox类型: {spinbox_type}")
                return  # 类型错误时提前返回

            log_wp(f"已保存spinBox{spinbox_type}值：{value}")  # 日志记录
        except Exception as e:
            # 记录异常详情，帮助定位问题
            log.write_to_plain_text_3(f"保存spinBox值失败: {str(e)}")
            print(f"save_spinbox_value异常: {str(e)}")  # 控制台输出辅助调试

    def upgrade_start(self):
        print("升级开始")

# 保留唯一主程序入口
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = MainWindow()  # 实例化自定义窗口类
    MainWindow.show()
    sys.exit(app.exec())



