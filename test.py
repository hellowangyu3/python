import log
LOG_WP = log.LOG_WP


class Protocol13762:
    """13762协议基础类（处理通用帧结构）"""
    def __init__(self):
        self.afn = None  # 应用功能码
        self.fn = None   # 功能码
        self.data = None # 业务数据域
        self.header = b''  # 帧头
        self.control = b'' # 控制域
        self.checksum = 0  # 校验和

    def parse_common_frame(self, frame_bytes):
        """解析通用帧结构（提取AFN/FN和数据域）"""
        # 假设帧格式：[帧头(2B)][控制域(1B)][AFN(1B)][FN(1B)][数据域(nB)][校验和(1B)][帧尾(1B)]
        self.header = frame_bytes[:2]
        self.control = frame_bytes[2:3]
        self.afn = frame_bytes[3]  # 提取AFN
        self.fn = frame_bytes[4]   # 提取FN
        self.data = frame_bytes[5:-2]  # 数据域（排除校验和与帧尾）
        self.checksum = frame_bytes[-2]  # 校验和

        # 校验和验证（异或校验示例）
        calculated_checksum = self.calculate_checksum(frame_bytes[:-2])
        if calculated_checksum != self.checksum:
            raise ValueError(f"校验和错误（接收:{self.checksum:02X}, 计算:{calculated_checksum:02X}）")

    def build_common_frame(self, afn, fn, data, control=b'\x43'):
        """构建通用帧结构（组装帧头、控制域、AFN/FN、数据、校验和）"""
        self.afn = afn
        self.fn = fn
        self.data = data
        self.control = control

        # 组装帧主体（帧头固定为0x681A示例）
        frame_body = b'\x68\x1A' + control + bytes([afn, fn]) + data
        # 计算校验和并添加帧尾（0x16为结束符）
        self.checksum = self.calculate_checksum(frame_body)
        full_frame = frame_body + bytes([self.checksum]) + b'\x16'
        return full_frame

    @staticmethod
    def calculate_checksum(data):
        """计算异或校验和"""
        checksum = 0
        for byte in data:
            checksum ^= byte
        return checksum


class AFNFNDispatcher:  # 修改：类名遵循 CapWords 约定（移除下划线）
    """AFN/FN调度器（路由到对应业务处理器）"""
    def __init__(self):
        self.handlers = {}  # 存储(afn, fn): handler映射

    def register_handler(self, afn, fn, handler):
        """注册AFN/FN对应的业务处理器"""
        self.handlers[(afn, fn)] = handler

    def dispatch(self, afn, fn, data):
        """根据AFN/FN调用对应处理器"""
        handler = self.handlers.get((afn, fn))
        if not handler:
            raise ValueError(f"未支持的AFN={afn:02X}, FN={fn:02X}")
        return handler(data)


# -------------------------- 业务处理器示例 --------------------------
def handle_file_transfer(data):
    """处理AFN=0x15, FN=0x01的文件传输帧"""
    # 解析文件传输专用数据（示例：文件标识+总段数+当前段数据）
    file_id = data[0]
    total_segments = int.from_bytes(data[1:3], 'big')
    current_segment = int.from_bytes(data[3:5], 'big')
    file_data = data[5:]
    return {
        "type": "文件传输",
        "file_id": file_id,
        "total_segments": total_segments,
        "current_segment": current_segment,
        "data_length": len(file_data),
        "data_sample": file_data.hex().upper()[:20] + "..."
    }


def handle_measurement_data(data):
    """处理AFN=0x01, FN=0x02的测量数据帧"""
    # 解析测量数据（示例：电压+电流）
    voltage = int.from_bytes(data[:2], 'big') / 10.0  # 单位：V
    current = int.from_bytes(data[2:4], 'big') / 100.0  # 单位：A
    return {
        "type": "测量数据",
        "voltage": voltage,
        "current": current
    }


# -------------------------- 使用示例 --------------------------
if __name__ == "__main__":
    # 1. 初始化协议解析器和调度器
    protocol = Protocol13762()
    dispatcher = AFNFNDispatcher()  # 修改：同步更新类名引用

    # 2. 注册业务处理器（AFN/FN -> 处理函数）
    dispatcher.register_handler(0x15, 0x01, handle_file_transfer)  # 文件传输
    dispatcher.register_handler(0x01, 0x02, handle_measurement_data)  # 测量数据

    # -------------------------- 解析示例 --------------------------
    print("===== 解析接收到的帧 =====")
    # 示例帧：AFN=0x15, FN=0x01（文件传输）
    received_frame = bytes.fromhex(
        "68 1A 43 15 01 08 00 06 2C 00 00 FF E2 C5 A8 E4 16"  # E4为校验和，16为帧尾
    )
    try:
        # 解析通用帧结构
        protocol.parse_common_frame(received_frame)
        print(f"解析成功：AFN={protocol.afn:02X}, FN={protocol.fn:02X}")
        # 调度到业务处理器
        result = dispatcher.dispatch(protocol.afn, protocol.fn, protocol.data)
        print("业务数据解析结果：", result)
    except Exception as e:
        print(f"解析失败：{e}")

    # -------------------------- 构帧示例 --------------------------
    print("\n===== 构建发送帧 =====")
    # 构建AFN=0x01, FN=0x02的测量数据帧（电压220.5V，电流1.25A）
    measurement_data = b'\x08\xB5' + b'\x00\x7D'  # 0x08B5=2229 → 222.9V；0x007D=125 → 1.25A
    send_frame = protocol.build_common_frame(
        afn=0x01, fn=0x02, data=measurement_data
    )
    print(f"构建的帧（16进制）：{send_frame.hex().upper()}")
