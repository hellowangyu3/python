import unittest
from unittest.mock import MagicMock, patch
# 修正导入路径：移除不存在的 'Project.' 层级
from serial_thread import SerialThread, global_kfifo
import time


class TestSerialThread(unittest.TestCase):
    def setUp(self):
        """测试前初始化"""
        self.mock_serial = MagicMock()
        self.mock_serial.is_open.return_value = True
        self.serial_thread = SerialThread(self.mock_serial)

        # 重置全局KFIFO缓冲区：通过弹出所有元素清空（替代不存在的clear()方法）
        while True:
            try:
                global_kfifo.pop()  # 使用KFIFO已有的pop()方法移除元素
            except:  # 捕获缓冲区为空时的异常（假设空缓冲区pop会抛异常）
                break

    def test_init(self):
        """测试构造函数"""
        self.assertEqual(self.serial_thread.serial_if, self.mock_serial)
        self.assertFalse(self.serial_thread.is_running)

    @patch('serial_thread.time.sleep')  # 修正patch路径：移除 'Project.'
    @patch('serial_thread.time.strftime')  # 修正patch路径：移除 'Project.'
    @patch('serial_thread.log.write_to_plain_text_3')  # 修正patch路径：移除 'Project.'
    def test_run_normal(self, mock_log, mock_strftime, mock_sleep):
        """测试正常数据接收流程"""
        # 模拟数据
        mock_strftime.return_value = "2023-01-01 12:00:00"
        self.mock_serial.read_data.return_value = (True, b'\x01\x02')

        # 启动线程
        self.serial_thread.is_running = True
        self.serial_thread.run()

        # 验证
        self.mock_serial.read_data.assert_called()
        self.serial_thread.data_received.emit.assert_called_with(
            "[2023-01-01 12:00:00] 收到数据(hex): 0102"
        )
        self.assertEqual(global_kfifo.pop().decode(), "0102")

    @patch('Project.serial_thread.time.sleep')
    def test_run_exception(self, mock_sleep):
        """测试异常处理"""
        self.mock_serial.read_data.side_effect = Exception("Test Error")
        self.serial_thread.is_running = True
        self.serial_thread.run()

        self.serial_thread.data_received.emit.assert_called_with(
            "读取异常: Test Error"
        )

    @patch('Project.serial_thread.time.sleep')
    def test_run_serial_closed(self, mock_sleep):
        """测试串口关闭状态"""
        self.mock_serial.is_open.return_value = False
        self.serial_thread.is_running = True
        self.serial_thread.run()

        self.mock_serial.read_data.assert_not_called()

    @patch('Project.serial_thread.log.write_to_plain_text_3')
    def test_start_stop_thread(self, mock_log):
        """测试线程启动/停止"""
        # 测试启动
        self.serial_thread.start = MagicMock()
        self.serial_thread.start_thread()
        self.assertTrue(self.serial_thread.is_running)
        mock_log.assert_called_with("串口线程已启动")

        # 测试停止
        self.serial_thread.wait = MagicMock()
        self.serial_thread.stop_thread()
        self.assertFalse(self.serial_thread.is_running)
        mock_log.assert_called_with("串口线程已停止")

    def test_kfifo_overflow(self):
        """测试KFIFO缓冲区溢出"""
        # 填充缓冲区直到溢出
        test_data = b"overflow"
        for _ in range(1025):  # 超过缓冲区大小
            global_kfifo.push(test_data)

        # 验证最新数据被保留
        self.assertEqual(global_kfifo.pop(), test_data)


if __name__ == '__main__':
    unittest.main()