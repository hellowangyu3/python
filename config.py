# 全局配置变量存储
# 删除错误的PyQt6导入语句（QWidget是类而非模块，且update是实例方法无需导入）
# from PyQt6.QtWidgets.QWidget import update
# from Tools.scripts.generate_token import update_file  # 若无需此导入也可删除

spin_box_value = 0  # 保存spinBox的值
spin_box_2_value = 0  # 可选：保存spinBox_2的值（如需）
#串口参数保存
serial_str = ""  # 串口名称
serial_status = 0  # 串口状态
file1_path = ""  # 存储文件1路径
file1_name = ""  # 存储文件1名称
file2_path = ""  # 存储文件2路径
file2_name = ""  # 存储文件2名称


def config_val_check():
    """检查配置值是否有效"""
    return True

