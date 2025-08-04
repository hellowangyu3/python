# 全局配置变量存储
# 删除错误的PyQt6导入语句（QWidget是类而非模块，且update是实例方法无需导入）
# from PyQt6.QtWidgets.QWidget import update
# from Tools.scripts.generate_token import update_file  # 若无需此导入也可删除
from log import log_wp
test_count = 0  # 测试轮次 保存spinBox的值

#串口参数保存
serial_str = ""  # 串口名称
serial_status = "关闭"  # 串口状态
file1_path = ""  # 存储文件1路径
file1_version = ""  # 存储文件1名称
file2_path = ""  # 存储文件2路径
file2_version = ""  # 存储文件2名称

rx_ord = 1
tx_ord = 1

#升级进度-文件包大小
file1_size = 0
file2_size = 0
#升级进度-当前帧
current_frame = 0
#升级进度-当前数据
current_data = b""
#升级进度-当前数据长度
current_data_len = 0
#升级进度-总帧数
total_frame = 0
# 升级方式 递增
file_step_by_step = 0
len_upgrade_frame = 0  # 升级包帧长度：保存spinBox_2的值（如需）
spin_box_2_value = 0
def print_config_value():
    log_wp(f"test_count: {test_count}")
    log_wp(f"len_upgrade_frame: {len_upgrade_frame}")
    log_wp(f"serial_str: {serial_str}")
    log_wp(f"serial_status: {serial_status}")
    log_wp(f"file1_path: {file1_path}")
    log_wp(f"file1_version: {file1_version}")
    log_wp(f"file2_path: {file2_path}")
    log_wp(f"file2_version: {file2_version}")




def config_val_check():
    """检查配置值是否有效，返回所有无效项或True"""  # 移动文档字符串到函数顶部
    errors = {}  # 收集所有无效配置项

    # 检查所有配置项，收集所有错误（而非遇到第一个错误就返回）
    # if test_count == 0:
    #     errors["测试轮次"] = False
    if serial_status == "关闭":
        errors["串口未打开"] = False
    if file1_path == "":
        errors["升级文件1路径"] = False
    if file2_path == "":
        errors["升级文件2路径"] = False
    if file1_version == "":
        errors["升级文件1版本信息"] = False
    if file2_version == "":
        errors["升级文件2版本信息"] = False
    if len_upgrade_frame == 0:
        errors["升级包帧长度"] = False
    if not errors:
        total_frame = file1_size // len_upgrade_frame

    # 统一返回格式：无错误返回True，有错误返回错误字典
    return True if not errors else errors

