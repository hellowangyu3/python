import threading


class KFifoAps:
    """修复死锁+数据读取错误的环形队列实现"""

    # 环形缓冲默认大小（确保是2的幂，便于环形计算）
    FIFO_QUEUE_LEN = 32768 #这里改为2^15

    def __init__(self, buffer_size=None):
        """初始化环形队列，包括线程锁"""
        # 若指定缓冲区大小，自动调整为最近的2的幂
        self.size = buffer_size if buffer_size else self.FIFO_QUEUE_LEN
        self.size = 1 << (self.size - 1).bit_length()  # 确保2的幂
        self.mask = self.size - 1  # 快速环形偏移计算（替代取模）
        self.buffer = [0] * self.size  # 环形缓冲区
        self.in_pos = 0  # 写入位置计数器（累加，非偏移）
        self.out_pos = 0  # 读取位置计数器（累加，非偏移）
        self.lock = threading.Lock()  # 线程安全锁

    # ------------------------------
    # 内部无锁辅助方法（仅供类内带锁方法调用）
    # ------------------------------
    def _get_remaining_length(self):
        """获取剩余空间（内部无锁）"""
        return (self.out_pos - self.in_pos - 1) & self.mask

    def _get_data_length(self):
        """获取当前数据长度（内部无锁）"""
        return (self.in_pos - self.out_pos) & self.mask

    # ------------------------------
    # 公开带锁方法（外部调用入口）
    # ------------------------------
    def get_remaining_length(self):
        with self.lock:
            return self._get_remaining_length()

    def get_data_length(self):
        with self.lock:
            return self._get_data_length()

    def put(self, data):
        """添加数据（支持bytes/str/整数列表）"""
        # 1. 数据类型预处理（无锁，避免持有锁时做耗时检查）
        if isinstance(data, str):
            data = list(data.encode('utf-8'))  # 字符串→bytes→整数列表
        elif isinstance(data, bytes):
            data = list(data)  # bytes→整数列表
        elif not isinstance(data, list):
            print(f"put错误：不支持类型 {type(data)}，仅允许str/bytes/整数列表")
            return 0

        # 2. 检查列表元素是否为有效字节（0-255）
        for i, byte in enumerate(data):
            if not isinstance(byte, int) or not (0 <= byte <= 255):
                print(f"put错误：第{i}个元素 {byte} 不是有效字节（需0-255）")
                return 0

        data_len = len(data)
        if data_len == 0:
            return 0

        # 3. 加锁写入数据（核心逻辑）
        with self.lock:
            add_len = min(data_len, self._get_remaining_length())  # 最大可写入长度
            if add_len <= 0:
                print("put警告：队列已满，无法添加数据")
                return 0

            in_offset = self.in_pos & self.mask  # 写入起始偏移（环形）
            # 分段1：从in_offset到缓冲区末尾
            segment1_len = min(add_len, self.size - in_offset)
            self.buffer[in_offset:in_offset + segment1_len] = data[:segment1_len]
            # 分段2：缓冲区开头到剩余长度（若有）
            segment2_len = add_len - segment1_len
            if segment2_len > 0:
                self.buffer[:segment2_len] = data[segment1_len:segment1_len + segment2_len]

            self.in_pos += add_len  # 更新写入计数器
            return add_len

    def get(self, length):
        """读取并删除数据（返回整数列表）"""
        if length <= 0:
            return []

        with self.lock:
            data_len = self._get_data_length()
            read_len = min(length, data_len)  # 实际可读取长度
            if read_len <= 0:
                # print("get警告：队列已空，无法读取数据")
                return []

            out_offset = self.out_pos & self.mask  # 读取起始偏移（环形）
            result = []
            # 分段1：从out_offset到缓冲区末尾
            segment1_len = min(read_len, self.size - out_offset)
            result.extend(self.buffer[out_offset:out_offset + segment1_len])
            # 分段2：缓冲区开头到剩余长度（若有）
            segment2_len = read_len - segment1_len
            if segment2_len > 0:
                result.extend(self.buffer[:segment2_len])

            self.out_pos += read_len  # 更新读取计数器（删除数据）
            return result

    def read(self, length):
        """读取但不删除数据（返回整数列表）"""
        if length <= 0:
            return []

        with self.lock:
            data_len = self._get_data_length()
            read_len = min(length, data_len)
            if read_len <= 0:
                # print("read警告：队列已空，无法读取数据")
                return []

            out_offset = self.out_pos & self.mask  # 读取起始偏移（环形）
            result = []
            # 分段1：从out_offset到缓冲区末尾
            segment1_len = min(read_len, self.size - out_offset)
            result.extend(self.buffer[out_offset:out_offset + segment1_len])
            # 分段2：缓冲区开头到剩余长度（若有）
            segment2_len = read_len - segment1_len
            if segment2_len > 0:
                result.extend(self.buffer[:segment2_len])

            return result  # 无需更新out_pos（不删除数据）

    def free(self, length):
        """释放指定长度的空间（等价于删除数据但不返回）"""
        if length <= 0:
            return

        with self.lock:
            data_len = self._get_data_length()
            free_len = min(length, data_len)
            self.out_pos += free_len  # 直接更新读取计数器即可

    def read_index(self, index, length):
        """从指定索引读取数据（不删除，索引从0开始）"""
        if length <= 0:
            return []

        with self.lock:
            data_len = self._get_data_length()
            # 检查索引有效性
            if index < 0 or (index + length) > data_len:
                print(f"read_index错误：索引{index}或长度{length}超出数据范围（当前数据长度{data_len}）")
                return []

            # 计算起始偏移：out_pos + index 的环形偏移
            start_offset = (self.out_pos + index) & self.mask
            result = []
            # 分段1：从start_offset到缓冲区末尾
            segment1_len = min(length, self.size - start_offset)
            result.extend(self.buffer[start_offset:start_offset + segment1_len])
            # 分段2：缓冲区开头到剩余长度（若有）
            segment2_len = length - segment1_len
            if segment2_len > 0:
                result.extend(self.buffer[:segment2_len])

            return result

    def __str__(self):
        """打印队列状态（含实际数据）"""
        with self.lock:
            data_len = self._get_data_length()
            data = []
            # 遍历所有有效数据（基于环形偏移）
            current_offset = self.out_pos & self.mask
            for _ in range(data_len):
                data.append(self.buffer[current_offset])
                current_offset = (current_offset + 1) & self.mask  # 环形递增
            return (f"KFifoAps(size={self.size}, "
                    f"used_length={data_len}, "
                    f"free_length={self._get_remaining_length()}, "
                    f"data={data})")


# ------------------------------
# 测试示例（验证修复效果）
# ------------------------------
if __name__ == "__main__":
    fifo = KFifoAps()
    print("=== 初始状态 ===")
    print(f"队列状态：{fifo}")

    # 1. 添加整数列表数据
    data1 = [0x01, 0x12, 0x03, 0x14, 0x05]
    added1 = fifo.put(data1)
    print(f"\n=== 添加数据1（{data1}）===")
    print(f"实际添加字节数：{added1}")
    print(f"当前队列长度：{fifo.get_data_length()}")
    print(f"队列状态：{fifo}")

    # 2. 读取数据（不删除）
    read_data1 = fifo.read(3)
    print(f"\n=== 读取3字节（不删除）===")
    print(f"读取到的数据：{[hex(x) for x in read_data1]}")  # 应显示 [0x1, 0x12, 0x3]
    print(f"读取后队列长度：{fifo.get_data_length()}")  # 应保持5

    # 3. 获取数据（删除）
    get_data1 = fifo.get(3)
    print(f"\n=== 获取3字节（删除）===")
    print(f"获取到的数据：{[hex(x) for x in get_data1]}")  # 应显示 [0x1, 0x12, 0x3]
    print(f"获取后队列长度：{fifo.get_data_length()}")  # 应剩余2（5-3）

    # 4. 添加字符串数据
    data2 = "whudwhduw"
    added2 = fifo.put(data2)
    print(f"\n=== 添加数据2（字符串：{data2}）===")
    print(f"字符串编码后长度：{len(data2.encode('utf-8'))}")
    print(f"实际添加字节数：{added2}")
    print(f"添加后队列长度：{fifo.get_data_length()}")  # 应显示 2+9=11

    # 5. 释放2字节空间
    fifo.free(2)
    print(f"\n=== 释放2字节空间 ===")
    print(f"释放后队列长度：{fifo.get_data_length()}")  # 应显示 11-2=9
    print(f"队列状态：{fifo}")

    # 6. 从指定索引读取数据
    read_index_data = fifo.read_index(2, 4)
    print(f"\n=== 从索引2读取4字节（不删除）===")
    print(f"读取到的数据：{[hex(x) for x in read_index_data]}")  # 基于实际数据计算
    print(f"读取后队列长度：{fifo.get_data_length()}")  # 保持9