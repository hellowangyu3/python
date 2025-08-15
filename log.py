import time
import inspect
import threading
from kfifo import KFifoAps  # 导入环形队列类

# 日志命令常量
LOG_OPT_CMD = 1
LOG_DEBUG_CMD = 2
LOG_PROTOCOL_CMD = 3
LOG_RESULT_CMD = 4

# 日志文件路径
LOG_FILE_PATH = './log.txt'
DEBUG_FILE_PATH = './debug.txt'
Protocol13762_LOG_FILE_PATH = './protocol13762.txt'
RESULT_LOG_FILE_PATH = './result.txt'

# 全局控件引用
_plain_text_edit_3 = None
_label_7_text_edit = None
_progress_bar = None  # 新增：进度条控件引用

# 初始化各日志类型对应的环形队列
log_fifo = KFifoAps()          # 对应LOG_OPT_CMD
debug_fifo = KFifoAps()        # 对应LOG_DEBUG_CMD
protocol_fifo = KFifoAps()     # 对应LOG_PROTOCOL_CMD
result_fifo = KFifoAps()       # 对应LOG_RESULT_CMD

class LogThread(threading.Thread):
    """日志写入线程，循环读取队列并写入文件"""
    def __init__(self):
        super().__init__(daemon=True)
        self.file_handles = {}
        self._init_files()

    def _init_files(self):
        """打开所有日志文件，保持句柄以便持续写入"""
        file_mapping = {
            LOG_OPT_CMD: LOG_FILE_PATH,
            LOG_DEBUG_CMD: DEBUG_FILE_PATH,
            LOG_PROTOCOL_CMD: Protocol13762_LOG_FILE_PATH,
            LOG_RESULT_CMD: RESULT_LOG_FILE_PATH
        }
        for cmd, path in file_mapping.items():
            self.file_handles[cmd] = open(path, 'a', encoding='utf-8')

    def run(self):
        """线程主循环：持续读取队列并写入文件"""
        print("日志线程启动，开始监听队列...")
        while True:
            self._process_fifo(log_fifo, LOG_OPT_CMD)
            self._process_fifo(debug_fifo, LOG_DEBUG_CMD)
            self._process_fifo(protocol_fifo, LOG_PROTOCOL_CMD)
            self._process_fifo(result_fifo, LOG_RESULT_CMD)
            time.sleep(0.01)

    def _process_fifo(self, fifo, cmd):
        """处理单个队列的日志数据并写入对应文件"""
        if fifo.get_data_length() == 0:
            return
        # 读取队列中所有数据（字节列表）
        byte_data = fifo.get(fifo.get_data_length())
        # 将字节列表转换为字符串（UTF-8解码）
        try:
            log_content = bytes(byte_data).decode('utf-8')
            self.file_handles[cmd].write(log_content)
            self.file_handles[cmd].flush()
        except UnicodeDecodeError as e:
            print(f"日志解码失败: {e}")

    def __del__(self):
        """线程结束时关闭所有文件句柄"""
        for handle in self.file_handles.values():
            handle.close()
        print("日志线程结束，文件句柄已关闭")

def _str_to_byte_list(s):
    """将字符串编码为UTF-8字节列表（确保每个元素是0-255的整数）"""
    return list(s.encode('utf-8'))  # encode后转为bytes，再转为整数列表

def log_wp(log):
    """写入操作日志"""
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    log_content = f"[{current_time}][{caller_func}:{caller_line}]{log}\n"
    # 关键修正：用UTF-8编码字符串为字节列表
    byte_data = _str_to_byte_list(log_content)
    log_fifo.put(byte_data)
    print(log_content.strip())

def log_info(cmd, info):
    """按命令类型写入不同日志"""
    fifo_map = {
        LOG_OPT_CMD: log_fifo,
        LOG_DEBUG_CMD: debug_fifo,
        LOG_PROTOCOL_CMD: protocol_fifo,
        LOG_RESULT_CMD: result_fifo
    }
    target_fifo = fifo_map.get(cmd)
    if not target_fifo:
        log_wp(f"无效日志命令: {cmd}")
        return

    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    log_content = f"[{current_time}][{caller_func}:{caller_line}]{info}\n"
    # 关键修正：用UTF-8编码字符串为字节列表
    byte_data = _str_to_byte_list(log_content)
    target_fifo.put(byte_data)
    # print(log_content.strip())

def set_plain_text_edit_3(widget):
    """设置 plainTextEdit_3 文本框控件引用"""
    global _plain_text_edit_3
    _plain_text_edit_3 = widget

def set_label_7_text_edit(widget):
    """设置 label_7 文本框控件引用"""
    global _label_7_text_edit
    _label_7_text_edit = widget

def set_version_text_edit(text):
    """设置 label_7 文本框内容"""
    if _label_7_text_edit is not None:
        _label_7_text_edit.setText(f"当前版本：{text} 待升级版本")
    else:
        log_info(LOG_DEBUG_CMD, f"label_7 控件未设置，无法写入版本信息: {text}")

def write_to_plain_text_3(text):
    """往 plainTextEdit_3 文本框中追加内容"""
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    display_text = f"[{current_time}] {text}"
    if _plain_text_edit_3 is not None:
        _plain_text_edit_3.appendPlainText(display_text)
        _plain_text_edit_3.verticalScrollBar().setValue(
            _plain_text_edit_3.verticalScrollBar().maximum()
        )
    # 写入日志队列
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    log_content = f"[{current_time}][{caller_func}:{caller_line}]{text}\n"
    # 关键修正：用UTF-8编码字符串为字节列表
    byte_data = _str_to_byte_list(log_content)
    log_fifo.put(byte_data)
    print(display_text)

# 启动日志线程
def start_log_thread():
    log_thread = LogThread()
    log_thread.start()
    return log_thread

def set_progress_bar(widget):
    """设置进度条控件引用"""
    global _progress_bar
    _progress_bar = widget


# 新增：简化的进度条更新函数（仅需当前值和最大值）
def update_progress_bar(current_value, max_value):
    """
    更新进度条（自动处理最大值设置和进度值限制）
    :param current_value: 当前进度值（必须为非负整数）
    :param max_value: 进度条最大值（必须为正整数）
    :return: bool - 操作是否成功
    """
    # 1. 检查进度条控件是否初始化
    if not _progress_bar:
        print("错误：进度条控件未初始化")
        return False

    # 2. 验证current_value类型和格式
    if not isinstance(current_value, int):
        print(f"错误：当前值必须为整数，实际为{type(current_value).__name__}")
        return False
    if current_value < 0:
        print(f"错误：当前值不能为负数，实际为{current_value}")
        return False

    # 3. 验证max_value类型和格式
    if not isinstance(max_value, int):
        print(f"错误：最大值必须为整数，实际为{type(max_value).__name__}")
        return False
    if max_value <= 0:
        print(f"错误：最大值必须为正数，实际为{max_value}")
        return False

    # 4. 检查当前值是否超过最大值（提前预警但不阻断）
    if current_value > max_value:
        print(f"警告：当前值({current_value})超过最大值({max_value})，将自动截断")

    # 5. 更新最大值（仅当不同时更新，减少不必要的UI操作）
    if _progress_bar.maximum() != max_value:
        _progress_bar.setMaximum(max_value)

    # 6. 限制当前值在有效范围内并更新
    clamped_value = max(0, min(current_value, max_value))
    _progress_bar.setValue(clamped_value)

    return True
    

# 主程序入口示例
if __name__ == "__main__":
    log_thread = start_log_thread()
    print("主程序启动，日志线程已运行")

    # 测试日志功能（包含中文）
    try:
        log_wp("测试操作日志（包含中文）")
        log_info(LOG_DEBUG_CMD, "测试调试日志（包含中文）")
        log_info(LOG_PROTOCOL_CMD, "测试协议交互日志（包含中文）")
        log_info(LOG_RESULT_CMD, "测试结果日志（包含中文）")
        write_to_plain_text_3("测试UI文本框日志（包含中文）")
        set_version_text_edit("v1.0.0")
    finally:
        time.sleep(1)