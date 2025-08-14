import os
from protocol.gw13762 import *  # 假设该模块提供帧处理功能
import tkinter as tk
from tkinter import filedialog, messagebox
import re  # 正则模块用于过滤


def get_file_version(file_name):
    """从升级文件中提取版本号信息"""
    base_name = os.path.basename(file_name)
    file_prefix = os.path.splitext(base_name)[0]
    parts = file_prefix.split('_')

    version = ""
    version_date = ""
    internal_version = ""
    internal_date = ""

    for part in parts:
        if part.startswith('sv'):
            version = part[2:]
        elif part.startswith('date'):
            version_date = part[4:]
        elif part.startswith('isv'):
            internal_version = part[3:]
        elif part.startswith('idate'):
            internal_date = part[5:]

    return (version, version_date, internal_version, internal_date)


def _file_line_generator(file_path):
    """生成器：逐行读取文件，返回(行号, 原始行内容)"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line_num, line in enumerate(f):
            yield line_num, line.strip()  # 去除首尾空白和换行符


def read_line_with_count(file_path, target_line):
    """使用生成器读取指定行内容（只读，不修改文件）"""
    try:
        # 使用生成器逐行查找目标行（内存中只保留当前行）
        target_line_content = None
        for line_num, content in _file_line_generator(file_path):
            if line_num == target_line:
                target_line_content = content
                break

        # 检查目标行是否存在
        if target_line_content is None:
            return "行号超出范围", 0, ""

        # 清理内容中的非法字符（仅保留十六进制相关字符）
        if ',' in target_line_content:
            # 分割为前缀部分和内容部分
            prefix_part, content_part = target_line_content.rsplit(',', 1)
            # 过滤内容部分：只保留0-9、A-F、a-f和空格
            content_part = re.sub(r'[^0-9A-Fa-f ]', '', content_part)
            target_line_content = f"{prefix_part},{content_part}"
        else:
            return "文件格式错误", 0, ""

        # 解析行内容
        parts = target_line_content.split(',', 3)
        if len(parts) < 4:
            return "文件格式错误", 0, ""

        line_num_str, status, read_count_str, content = parts

        # 解析读取次数（如果格式错误则返回0）
        try:
            read_count = int(read_count_str)
        except ValueError:
            read_count = 0

        # 仅返回结果，不修改文件
        return "OK", read_count, content

    except Exception as e:
        return f"读取失败: {str(e)}", 0, ""


def crop_file_by_size(input_path, output_path, chunk_size):
    """按指定字节数裁剪文件"""
    try:
        with open(input_path, 'rb') as infile, open(output_path, 'w') as outfile:
            line_number = 0
            chunk = infile.read(chunk_size)
            while chunk:
                # 不足chunk_size的块用0xFF补全
                original_length = len(chunk)
                if original_length < chunk_size:
                    chunk += bytes([0xFF] * (chunk_size - original_length))

                # 写入行（初始状态:Ready，初始读取次数:0）
                hex_content = ' '.join(f'{byte:02X}' for byte in chunk)
                outfile.write(f"{line_number},Ready,0,{hex_content}\n")
                line_number += 1

                chunk = infile.read(chunk_size)

        return True, line_number

    except Exception as e:
        return False, f"文件裁剪失败: {str(e)}"


def select_dat_file_and_convert():
    """选择DAT文件并转换为指定格式"""
    root = tk.Tk()
    root.withdraw()

    file_path = filedialog.askopenfilename(
        title="选择DAT文件",
        filetypes=[("DAT文件", "*.dat"), ("所有文件", "*.*")]
    )

    if not file_path:
        return False, "未选择文件"

    try:
        output_dir = os.path.dirname("./temp.txt")
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(file_path, 'rb') as dat_file, open("./temp.txt", 'w', encoding='utf-8') as txt_file:
            chunk_size = 128
            while True:
                chunk = dat_file.read(chunk_size)
                if not chunk:
                    break
                hex_str = ' '.join(f'{byte:02X}' for byte in chunk)
                txt_file.write(hex_str + '\n')

        messagebox.showinfo("成功", f"文件已成功转换并保存到：\n{os.path.abspath('./temp.txt')}")
        return True, "转换成功"

    except Exception as e:
        error_msg = f"处理文件时出错：\n{str(e)}"
        messagebox.showerror("错误", error_msg)
        return False, error_msg


def list_to_hex_str(num_list, uppercase=True, prefix=True, separator=' '):
    """将整数列表转换为十六进制字符串"""
    format_str = '0x%02X' if (prefix and uppercase) else '%02X'
    if not uppercase:
        format_str = '0x%02x' if prefix else '%02x'

    return separator.join([format_str % num for num in num_list])


def create_file_info_list(
        file_identifier,
        file_attribute,
        file_command,
        total_segments,
        segment_identifier,
        segment_length
):
    """创建文件信息列表，自动处理大小端转换"""

    def to_little_endian(value, byte_count):
        return [(value >> (8 * i)) & 0xFF for i in range(byte_count)]

    info_list = [
        to_little_endian(file_identifier, 1),
        f"文件标识:{file_identifier}:本地通信模块升级文件[BIN]",
        to_little_endian(file_attribute, 1),
        f"文件属性:{file_attribute}:起始帧、中间帧[BIN]",
        to_little_endian(file_command, 1),
        f"文件指令:{file_command}:报文方式下装[BIN]",
        to_little_endian(total_segments, 2),
        f"总段数n:{total_segments}:[BIN]",
        to_little_endian(segment_identifier, 4),
        f"第i段标识（i=0~n）:{segment_identifier}:[BIN]",
        to_little_endian(segment_length, 2),
        f"第i段数据长度Lf:{segment_length}:[BIN]"
    ]

    return info_list


def create_file_info_bytes(
        file_identifier,
        file_attribute,
        file_command,
        total_segments,
        segment_identifier,
        segment_length
):
    """生成文件信息的字节序列"""

    def to_little_endian(value, byte_count):
        return [(value >> (8 * i)) & 0xFF for i in range(byte_count)]

    parts = [
        to_little_endian(file_identifier, 1),
        to_little_endian(file_attribute, 1),
        to_little_endian(file_command, 1),
        to_little_endian(total_segments, 2),
        to_little_endian(segment_identifier, 4),
        to_little_endian(segment_length, 2)
    ]

    return [byte for part in parts for byte in part]


if __name__ == "__main__":
    # 确保资源正确释放
    root = None
    try:
        # 创建Tkinter隐藏窗口
        root = tk.Tk()
        root.withdraw()

        # 选择升级文件
        input_file = "//wsl.localhost/Ubuntu-22.04-E/home/wangy/cco_code/04-feature/cco/firmware/upgrade_cco_SHAN_XI_hv0201_sv002401_date241122_115200_E_FC_F8_isv130009_idate250809.dat"

        # 提取文件版本信息
        version_info = get_file_version(input_file)
        print(f"文件版本信息:")
        print(f"  版本号: {version_info[0]}")
        print(f"  版本日期: {version_info[1]}")
        print(f"  内部版本号: {version_info[2]}")
        print(f"  内部版本日期: {version_info[3]}")

        chunk_size = 120
        # 裁剪文件
        success, line_count = crop_file_by_size(input_file, "./cropped_file.txt", chunk_size)
        if success:
            print(f"文件裁剪完成，共 {line_count} 行")

            # 读取第3334行
            read_status, read_count, content = read_line_with_count("./cropped_file.txt", 3334)
            print(f"读取状态: {read_status}")
            print(f"行内容: {content}")
            print(f"读取次数: {read_count}")

            # 循环读取多行
            for i in range(1003):
                read_status2, read_count2, content2 = read_line_with_count("./cropped_file.txt", i)
                if read_status2 != "OK":
                    print(f"读取行 {i} 失败: {read_status2}")
                    continue

                # 转换内容为字节列表
                hex_parts = content2.split()
                content2_bytes = [int(hex_part, 16) for hex_part in hex_parts]
                print(f"行 {i} 字节列表长度: {len(content2_bytes)}")

                # 生成文件信息字节并与内容合并
                info_bytes = create_file_info_bytes(
                    file_identifier=3,
                    file_attribute=0,
                    file_command=0,
                    total_segments=line_count,
                    segment_identifier=i,
                    segment_length=chunk_size
                )

                # 合并文件信息和内容字节
                full_bytes = info_bytes + content2_bytes
                hex_result = ' '.join(f'{b:02X}' for b in full_bytes)
                # print("完整字节序列：", hex_result)

                # 生成帧并打印
                gw13762_frame = create_default_frame(0x15, 1, 1, full_bytes)
                hex_str2 = list_to_hex_str(gw13762_frame[0], uppercase=False, prefix=False, separator=' ')
                print(f"行 {i} 帧内容：", hex_str2)
        else:
            print(f"文件处理失败: {line_count}")
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
    finally:
        # 确保Tkinter窗口正确关闭，释放资源
        if root is not None:
            root.destroy()
