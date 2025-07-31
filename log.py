import time


# 打开日志文件并写入（使用 'a+' 模式追加日志，避免覆盖）


# 定义日志写入函数（每次调用生成当前时间戳）
def log_wp(log):
    log_file = open('.venv/log.txt', 'a', encoding='utf-8')
    # 获取当前时间并格式化为字符串（例如：2024-05-20 15:30:45）
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # 拼接日志内容：[时间戳] 日志信息
    log_content = f"[{current_time}] {log}\n"
    log_file.write(log_content)
    log_file.flush()  # 立即写入磁盘
    print(log_content.strip())  # 打印时移除末尾换行符
    log_file.close()


# 新增：全局存储 plainTextEdit_3 控件引用
_plain_text_edit_3 = None

def set_plain_text_edit_3(widget):
    """设置 plainTextEdit_3 文本框控件引用（由主窗口调用）"""
    global _plain_text_edit_3
    _plain_text_edit_3 = widget

def write_to_plain_text_3(text):
    """往 plainTextEdit_3 文本框中追加内容"""
    if _plain_text_edit_3 is not None:
        # 使用 appendPlainText 方法追加文本（自动换行）
        current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        _plain_text_edit_3.appendPlainText(f"[{current_time}] {text}")
        # 滚动到底部，确保最新内容可见
        _plain_text_edit_3.verticalScrollBar().setValue(
            _plain_text_edit_3.verticalScrollBar().maximum()
        )