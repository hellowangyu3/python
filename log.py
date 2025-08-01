import time

# 移除未使用的循环导入：from test import Protocol13762
LOG_OPT_CMD = 1
LOG_DEBUG_CMD = 2
LOG_PROTOCOL_CMD = 3

# 常量定义
LOG_FILE_PATH = './log.txt'
DEBUG_FILE_PATH = './debug.txt'
# 协议交互日志
Protocol13762_LOG_FILE_PATH = './protocol13762.txt'

# 新增：全局存储 plainTextEdit_3 控件引用
_plain_text_edit_3 = None


# 定义日志写入函数（每次调用生成当前时间戳）
def log_wp(log):
    log_file = open(LOG_FILE_PATH, 'a', encoding='utf-8')
    # 获取当前时间并格式化为字符串（例如：2024-05-20 15:30:45）
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 拼接日志内容：[时间戳] 日志信息
    log_content = f"[{current_time}] {log}\n"
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
    else:
        log_wp(f"无效日志命令: {cmd}")
        return

    # 获取当前时间并格式化为字符串（例如：2024-05-20 15:30:45）
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 拼接日志内容：[时间戳] 日志信息
    log_content = f"[{current_time}] {cmd} {info}\n"
    log_file.write(log_content)
    log_file.flush()  # 立即写入磁盘
    print(log_content.strip())  # 打印时移除末尾换行符
    log_file.close()

def set_plain_text_edit_3(widget):
    """设置 plainTextEdit_3 文本框控件引用（由主窗口调用）"""
    global _plain_text_edit_3
    _plain_text_edit_3 = widget

def write_to_plain_text_3(text):
    """往 plainTextEdit_3 文本框中追加内容"""
    if _plain_text_edit_3 is not None:
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        _plain_text_edit_3.appendPlainText(f"[{current_time}] {text}")
        # 滚动到底部，确保最新内容可见
        _plain_text_edit_3.verticalScrollBar().setValue(
            _plain_text_edit_3.verticalScrollBar().maximum()
        )