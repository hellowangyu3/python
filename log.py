import time
import inspect
# 移除未使用的循环导入：from test import Protocol13762
LOG_OPT_CMD = 1
LOG_DEBUG_CMD = 2
LOG_PROTOCOL_CMD = 3
LOG_RESULT_CMD = 4
# 常量定义
LOG_FILE_PATH = './log.txt'
DEBUG_FILE_PATH = './debug.txt'
# 协议交互日志
Protocol13762_LOG_FILE_PATH = './protocol13762.txt'

RESULT_LOG_FILE_PATH = './result.txt'

# 新增：全局存储 plainTextEdit_3 控件引用
_plain_text_edit_3 = None
_label_7_text_edit = None

# 定义日志写入函数（每次调用生成当前时间戳）
def log_wp(log):
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    # 获取当前时间并格式化为字符串（例如：2024-05-20 15:30:45）
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    # 拼接日志内容：[时间戳] 日志信息
    log_content = f"[{current_time}][{caller_func}:{caller_line}]{log}\n"
    log_file.write(log_content)
    log_file.flush()  # 立即写入磁盘
    print(log_content.strip())  # 打印时移除末尾换行符
    log_file.close()


def log_info(cmd, info):
    # 用 if-elif-else 替代 match-case，兼容 Python 3.10 以下版本
    if cmd == LOG_OPT_CMD:
        log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    elif cmd == LOG_DEBUG_CMD:
        log_file = open(DEBUG_FILE_PATH, 'a', encoding='utf-8')
    elif cmd == LOG_PROTOCOL_CMD:
        log_file = open(Protocol13762_LOG_FILE_PATH, 'a', encoding='utf-8')
    elif cmd == LOG_RESULT_CMD:
        log_file = open(RESULT_LOG_FILE_PATH, 'a', encoding='utf-8')
    else:
        log_wp(f"无效日志命令: {cmd}")
        return

    # 获取当前时间并格式化为字符串（例如：2024-05-20 15:30:45）
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 拼接日志内容：[时间戳] 日志信息
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    # 拼接日志内容：[时间戳] 日志信息
    log_content = f"[{current_time}][{caller_func}:{caller_line}]{info}\n"
    log_file.write(log_content)
    log_file.flush()  # 立即写入磁盘
    print(log_content.strip())  # 打印时移除末尾换行符
    log_file.close()

def set_plain_text_edit_3(widget):
    """设置 plainTextEdit_3 文本框控件引用（由主窗口调用）"""
    global _plain_text_edit_3
    _plain_text_edit_3 = widget
def set_label_7_text_edit(widget):
    """设置 label_7 文本框控件引用（由主窗口调用）"""
    global _label_7_text_edit
    _label_7_text_edit = widget

def set_version_text_edit(text):
    """设置 label_7 文本框内容"""
    if _label_7_text_edit is not None:
        _label_7_text_edit.setText("当前版本：" + text +"待升级版本")
    else:
        log_info(LOG_DEBUG_CMD,f"label_7 控件未设置，无法写入日志: {text}")


def write_to_plain_text_3(text):
    """往 plainTextEdit_3 文本框中追加内容"""
    stack = inspect.stack()
    caller_func = stack[1].function
    caller_line = stack[1].lineno
    if _plain_text_edit_3 is not None:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        _plain_text_edit_3.appendPlainText(f"[{current_time}] {text}")
        log_content = f"[{current_time}][{caller_func}:{caller_line}]{text}\n"
        log_wp(log_content)
        print(log_content.strip())  # 打印时移除末尾换行符
        # 滚动到底部，确保最新内容可见
        _plain_text_edit_3.verticalScrollBar().setValue(
            _plain_text_edit_3.verticalScrollBar().maximum()
        )
    else:
        print(f"plainTextEdit_3 控件未设置，无法写入日志: {text}")