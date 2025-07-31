import serial
import serial.tools.list_ports
import re


class SerialInterface:
    def __init__(self):
        self.ser = None  # 串口对象
        self.is_open = False  # 串口状态

    def parse_config(self, config_str):
        """
        解析格式如"COM3,9600,E,8,1"的配置字符串
        返回: 配置字典或None(解析失败)
        """
        # 正则匹配配置格式：端口,波特率,校验位,数据位,停止位
        pattern = r'^(\w+),(\d+),(N|O|E|S|M),(\d+),(1|1.5|2)$'
        match = re.match(pattern, config_str.strip())

        if not match:
            return None

        port, baudrate, parity, databits, stopbits = match.groups()

        # 转换校验位为serial库对应的常量
        parity_map = {
            'N': serial.PARITY_NONE,
            'O': serial.PARITY_ODD,
            'E': serial.PARITY_EVEN,
            'S': serial.PARITY_SPACE,
            'M': serial.PARITY_MARK
        }

        # 转换停止位
        stopbits_map = {
            '1': serial.STOPBITS_ONE,
            '1.5': serial.STOPBITS_ONE_POINT_FIVE,
            '2': serial.STOPBITS_TWO
        }

        return {
            'port': port,
            'baudrate': int(baudrate),
            'parity': parity_map[parity],
            'databits': int(databits),
            'stopbits': stopbits_map[stopbits]
        }

    def open_serial(self, config_str):
        """
        通过配置字符串打开串口
        返回: (成功标志, 消息)
        """
        # 先关闭已打开的串口
        if self.is_open:
            self.close_serial()

        # 解析配置
        config = self.parse_config(config_str)
        if not config:
            return False, "配置格式错误，正确格式: COMx,波特率,校验位(N/O/E),数据位,停止位"

        try:
            # 初始化串口
            self.ser = serial.Serial(
                port=config['port'],
                baudrate=config['baudrate'],
                parity=config['parity'],
                bytesize=config['databits'],
                stopbits=config['stopbits'],
                timeout=0.1  # 读超时时间
            )

            if self.ser.is_open:
                self.is_open = True
                return True, f"串口 {config['port']} 已打开"
            else:
                return False, "串口打开失败"

        except Exception as e:
            return False, f"打开失败: {str(e)}"

    def close_serial(self):
        """关闭串口"""
        if self.is_open and self.ser:
            self.ser.close()
            self.is_open = False
            return True, "串口已关闭"
        return False, "串口未打开"

    def send_data(self, data, is_hex=True):  # 修改：默认is_hex=True
        """
        发送数据
        data: 待发送数据
        is_hex: 是否以十六进制发送（True=Hex格式，False=文本格式，默认True）
        返回: (成功标志, 消息)
        """
        if not self.is_open:
            return False, "串口未打开"

        try:
            if is_hex:
                # Hex格式：转换为字节（移除空格后处理）
                cleaned_data = data.replace(' ', '')
                data = bytes.fromhex(cleaned_data)
            else:
                # 文本格式：UTF-8编码
                data = data.encode('utf-8')

            self.ser.write(data)
            return True, f"发送成功: {len(data)}字节 (格式: {'Hex' if is_hex else '文本'})"
        except Exception as e:
            return False, f"发送失败: {str(e)}"

    def read_data(self, max_bytes=1024, is_hex=True):  # 修改：默认is_hex=True
        if not self.is_open:
            print("串口未打开")
            return False, "串口未打开"

        try:
            data = self.ser.read(max_bytes)
            if not data:
                return True, ""  # 无数据但读取成功

            if is_hex:
                # 转换为十六进制字符串
                return True, ' '.join(f'{b:02X}' for b in data)
            else:
                # 尝试解码为字符串
                return True, data.decode('utf-8', errors='replace')
        except Exception as e:
            print("读取失败")
            return False, f"读取失败: {str(e)}"

    def get_available_ports(self):
        """获取可用串口号列表"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

if __name__ == '__main__':
    # 示例使用
    serial_if = SerialInterface()
    print(serial_if.get_available_ports())
    print(serial_if.open_serial("COM71,9600,E,8,1"))
    print(serial_if.send_data("Hello, World!"))
    print(serial_if.read_data())
    print(serial_if.close_serial())
