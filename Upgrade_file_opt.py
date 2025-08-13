import os
from protocol.gw13762 import *  # 假设该模块提供帧处理功能
import tkinter as tk
from tkinter import filedialog, messagebox


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
    version = ""  # 版本号（sv前缀）
    version_date = ""  # 版本日期（date前缀）
    internal_version = ""  # 内部版本号（isv前缀）
    internal_date = ""  # 内部版本日期（idate前缀）

    # 遍历分割后的部分，匹配关键字前缀
    for part in parts:
        if part.startswith('sv'):  # 版本号：sv开头
            version = part[2:]  # 截取sv后的内容（如sv030028 → 030028）
        elif part.startswith('date'):  # 版本日期：date开头
            version_date = part[4:]  # 截取date后的内容（如date250616 → 250616）
        elif part.startswith('isv'):  # 内部版本号：isv开头
            internal_version = part[3:]  # 截取isv后的内容（如isv010008 → 010008）
        elif part.startswith('idate'):  # 内部版本日期：idate开头
            internal_date = part[5:]  # 截取idate后的内容（如idate250424 → 250424）

    return (version, version_date, internal_version, internal_date)


def read_line_with_count(file_path, target_line):
    """
    读取指定行内容，更新状态为OK并递增读取次数
    :param file_path: 文件路径
    :param target_line: 目标行号
    :return: (读取状态, 读取次数, 内容) - 状态为"成功"或错误信息
    """
    try:
        # 读取所有行并定位目标行
        with open(file_path, 'r') as f:
            lines = f.readlines()

            if target_line < 0 or target_line >= len(lines):
                return "行号超出范围", 0, ""  # 状态, 次数, 内容

            # 解析目标行（格式：行数,状态,读取次数,字节内容）
            target_line_content = lines[target_line].strip()
            parts = target_line_content.split(',', 3)  # 分割为4个部分
            if len(parts) < 4:
                return "文件格式错误", 0, ""

            line_num, status, read_count_str, content = parts
            read_count = int(read_count_str)  # 转换读取次数为整数

        # 更新状态为OK，读取次数+1
        with open(file_path, 'w') as f:
            for i, line in enumerate(lines):
                if i == target_line:
                    # 构建更新后的行内容
                    updated_parts = [line_num, "OK", str(read_count + 1), content]
                    line = ','.join(updated_parts) + '\n'
                f.write(line)

        return "OK", read_count + 1, content  # 返回新的读取次数和内容

    except Exception as e:
        return f"读取失败: {str(e)}", 0, ""


def crop_file_by_size(input_path, output_path, chunk_size):
    """
    按指定字节数裁剪文件，每行格式：行数,状态,读取次数,字节内容
    :param input_path: 输入文件路径
    :param output_path: 输出文件路径
    :param chunk_size: 每个字节数为一行
    :return: 成功标志、总行数
    """
    try:
        with open(input_path, 'rb') as infile, open(output_path, 'w') as outfile:
            line_number = 0

            # 优化循环结构：确保最后一块数据被正确处理
            chunk = infile.read(chunk_size)  # 先读取第一块
            while chunk:  # 当chunk不为空时持续处理
                # 不足chunk_size的块用0xFF补全
                original_length = len(chunk)
                if original_length < chunk_size:
                    chunk += bytes([0xFF] * (chunk_size - original_length))

                # 写入行（初始状态:Ready，初始读取次数:0）
                hex_content = ' '.join(f'{byte:02X}' for byte in chunk)
                outfile.write(f"{line_number},Ready,0,{hex_content}\n")
                line_number += 1

                # 读取下一块（循环条件在while处判断）
                chunk = infile.read(chunk_size)

        return True, line_number  # 仅返回成功标志和总行数

    except Exception as e:
        return False, f"文件裁剪失败: {str(e)}"


def select_dat_file_and_convert():
    """
    打开文件选择弹窗选择.dat文件，将其内容按128字节一行写入./temp.txt
    """
    # 创建隐藏的主窗口
    root = tk.Tk()
    root.withdraw()  # 隐藏主窗口

    # 打开文件选择对话框，只允许选择.dat文件
    file_path = filedialog.askopenfilename(
        title="选择DAT文件",
        filetypes=[("DAT文件", "*.dat"), ("所有文件", "*.*")]
    )

    # 如果用户取消选择，直接返回
    if not file_path:
        return False, "未选择文件"

    try:
        # 确保输出目录存在
        output_dir = os.path.dirname("./temp.txt")
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 读取DAT文件并按128字节一行写入temp.txt
        with open(file_path, 'rb') as dat_file, open("./temp.txt", 'w', encoding='utf-8') as txt_file:
            chunk_size = 128
            while True:
                # 每次读取128字节
                chunk = dat_file.read(chunk_size)
                if not chunk:
                    break  # 文件读取完毕

                # 将字节转换为十六进制字符串，每个字节用两位表示，空格分隔
                hex_str = ' '.join(f'{byte:02X}' for byte in chunk)
                txt_file.write(hex_str + '\n')

        # 显示成功消息
        messagebox.showinfo("成功", f"文件已成功转换并保存到：\n{os.path.abspath('./temp.txt')}")
        return True, "转换成功"

    except Exception as e:
        # 显示错误消息
        error_msg = f"处理文件时出错：\n{str(e)}"
        messagebox.showerror("错误", error_msg)
        return False, error_msg


def list_to_hex_str(num_list, uppercase=True, prefix=True, separator=' '):
    """
    将整数列表转换为十六进制字符串
    :param num_list: 整数列表（元素范围0-255）
    :param uppercase: 是否使用大写字母
    :param prefix: 是否添加'0x'前缀
    :param separator: 元素间的分隔符
    :return: 转换后的十六进制字符串
    """
    format_str = '0x%02X' if (prefix and uppercase) else '%02X'
    if not uppercase:
        format_str = '0x%02x' if prefix else '%02x'

    return separator.join([format_str % num for num in num_list])


def create_file_info_list(
        file_identifier,
        file_attribute,
        file_command,
        total_segments,  # 总段数（自动转换为小端字节）
        segment_identifier,
        segment_length  # 段长度（自动转换为小端字节）
):
    """
    根据参数创建文件信息列表，自动处理大小端转换
    :param file_identifier: 文件标识（整数）
    :param file_attribute: 文件属性（整数）
    :param file_command: 文件指令（整数）
    :param total_segments: 总段数（整数，会转换为小端2字节）
    :param segment_identifier: 段标识（整数，会转换为小端4字节）
    :param segment_length: 段长度（整数，会转换为小端2字节）
    :return: 包含所有信息的列表
    """

    # 辅助函数：将整数转换为指定字节数的小端字节列表
    def to_little_endian(value, byte_count):
        return [(value >> (8 * i)) & 0xFF for i in range(byte_count)]

    # 构建信息列表
    info_list = [
        # 文件标识
        to_little_endian(file_identifier, 1),
        f"文件标识:{file_identifier}:本地通信模块升级文件[BIN]",

        # 文件属性
        to_little_endian(file_attribute, 1),
        f"文件属性:{file_attribute}:起始帧、中间帧[BIN]",

        # 文件指令
        to_little_endian(file_command, 1),
        f"文件指令:{file_command}:报文方式下装[BIN]",

        # 总段数（2字节小端）
        to_little_endian(total_segments, 2),
        f"总段数n:{total_segments}:[BIN]",

        # 段标识（4字节小端）
        to_little_endian(segment_identifier, 4),
        f"第i段标识（i=0~n）:{segment_identifier}:[BIN]",

        # 段长度（2字节小端）
        to_little_endian(segment_length, 2),
        f"第i段数据长度Lf:{segment_length}:[BIN]"
    ]

    return info_list


def create_file_info_bytes(
        file_identifier,
        file_attribute,
        file_command,
        total_segments,  # 总段数（小端2字节）
        segment_identifier,  # 段标识（小端4字节）
        segment_length  # 段长度（小端2字节）
):
    """
    生成文件信息的字节序列（仅保留二进制数据，无描述）
    :return: 拼接后的字节列表
    """

    # 辅助函数：整数转小端字节列表（指定字节数）
    def to_little_endian(value, byte_count):
        return [(value >> (8 * i)) & 0xFF for i in range(byte_count)]

    # 按顺序定义各部分字节（仅保留二进制数据）
    parts = [
        to_little_endian(file_identifier, 1),  # 文件标识（1字节）
        to_little_endian(file_attribute, 1),  # 文件属性（1字节）
        to_little_endian(file_command, 1),  # 文件指令（1字节）
        to_little_endian(total_segments, 2),  # 总段数（2字节小端）
        to_little_endian(segment_identifier, 4),  # 段标识（4字节小端）
        to_little_endian(segment_length, 2)  # 段长度（2字节小端）
    ]

    # 拼接所有字节列表为一个连续列表
    return [byte for part in parts for byte in part]


if __name__ == "__main__":
    # 创建Tkinter隐藏窗口
    root = tk.Tk()
    root.withdraw()

    # 选择升级文件
    input_file = filedialog.askopenfilename(
        title="选择升级文件",
        filetypes=[("升级文件", "*.dat"), ("所有文件", "*.*")]
    )

    if not input_file:
        print("未选择文件，程序退出")
        exit()

    # 提取文件版本信息
    version_info = get_file_version(input_file)
    print(f"文件版本信息:")
    print(f"  版本号: {version_info[0]}")
    print(f"  版本日期: {version_info[1]}")
    print(f"  内部版本号: {version_info[2]}")
    print(f"  内部版本日期: {version_info[3]}")

    chunk_size = 128
    # 裁剪文件（生成包含读取次数的新格式文件）
    success, line_count = crop_file_by_size(input_file, "./cropped_file.txt", chunk_size)
    if success:
        print(f"文件裁剪完成，共 {line_count} 行")

        # 读取第5行（示例：目标行号4）
        read_status, read_count, content = read_line_with_count("./cropped_file.txt", 0)
        print(f"读取状态: {read_status}")
        print(f"读取次数: {read_count}")
        print(f"行内容: {content}")

        # 再次读取同一行，验证次数递增
        read_status2, read_count2, content2 = read_line_with_count("./cropped_file.txt", 0)
        print(f"再次读取状态: {read_status2}")
        print(f"再次读取次数: {read_count2}")

        # 转换内容为字节列表
        hex_parts = content2.split()
        content2_bytes = [int(hex_part, 16) for hex_part in hex_parts]
        print(f"文件内容字节列表长度: {len(content2_bytes)}")
        # 生成文件信息字节并与内容合并
        info_bytes = create_file_info_bytes(
            file_identifier=3,  # 对应 03
            file_attribute=0,  # 对应 00
            file_command=0,  # 对应 00
            total_segments=line_count,  # 使用实际总段数
            segment_identifier=4,  # 当前段标识（第5行）
            segment_length=chunk_size  # 段长度128
        )

        # 合并文件信息和内容字节
        full_bytes = info_bytes + content2_bytes
        hex_result = ' '.join(f'{b:02X}' for b in full_bytes)
        print("完整字节序列：", hex_result)
        # 生成帧并打印
        gw13762_frame = create_default_frame(0x15, 1, 1, full_bytes)
        hex_str2 = list_to_hex_str(gw13762_frame[0], uppercase=False, prefix=False, separator=' ')
        print("帧内容（小写无前缀）：", hex_str2)
    else:
        print(f"文件处理失败: {line_count}")


