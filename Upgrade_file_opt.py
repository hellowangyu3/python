#这个文件主要是提供文件操作功能，识别升级文件版本号，裁剪升级文件
#先做一个方法，识别文件版本号信息

import os  # 新增：用于提取文件名


def get_file_version(file_name):
    """
    从升级文件中提取版本号信息
    :param file_name: 升级文件的路径
    :return: 版本号字符串+版本日期+内部版本号+内部版本日期（元组形式）
    """
    # 提取文件名（去除路径和扩展名）
    base_name = os.path.basename(file_name)  # 获取文件名（含扩展名）
    file_prefix = os.path.splitext(base_name)[0]  # 去除扩展名，得到纯文件名部分
    parts = file_prefix.split('_')  # 按下划线分割文件名

    # 初始化提取结果
    version = ""          # 版本号（sv前缀）
    version_date = ""     # 版本日期（date前缀）
    internal_version = "" # 内部版本号（isv前缀）
    internal_date = ""    # 内部版本日期（idate前缀）

    # 遍历分割后的部分，匹配关键字前缀
    for part in parts:
        if part.startswith('sv'):          # 版本号：sv开头
            version = part[2:]             # 截取sv后的内容（如sv030028 → 030028）
        elif part.startswith('date'):      # 版本日期：date开头
            version_date = part[4:]        # 截取date后的内容（如date250616 → 250616）
        elif part.startswith('isv'):       # 内部版本号：isv开头
            internal_version = part[3:]    # 截取isv后的内容（如isv010008 → 010008）
        elif part.startswith('idate'):     # 内部版本日期：idate开头
            internal_date = part[5:]       # 截取idate后的内容（如idate250424 → 250424）

    # 返回提取结果（按顺序：版本号、版本日期、内部版本号、内部版本日期）
    return (version, version_date, internal_version, internal_date)    # upgrade_cco_LIAO_NING_hv0201_sv030028_date250616_9600_E_FC_F8_isv010008_idate250424.dat
    print(file_name)
