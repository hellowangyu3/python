import ctypes
from enum import IntEnum
from typing import Tuple

# 常量定义
LOCAL_ADDR_LEN = 6
LOCAL_FRAME_LEN_MIN = 15
HOST_NODE = 0  # 主节点标识（无地址域）


# 错误码枚举
class ErrorCode(IntEnum):
    FN_ACK_FFH = 0xFF  # 成功
    FN_DENY_02H = 0x02  # 长度错误
    FN_DENY_03H = 0x03  # 校验错误
    FN_DENY_05H = 0x05  # 格式错误


# 预定义数组类型
Uint8Array6 = ctypes.c_uint8 * 6
Uint8Array5 = ctypes.c_uint8 * 5
Uint8Array12 = ctypes.c_uint8 * 12  # LOCAL_ADDR_LEN * 2
Uint8Array2112 = ctypes.c_uint8 * 2112
Uint8Array4096 = ctypes.c_uint8 * 4096


# 协议结构定义
class CTRL13762(ctypes.Union):
    """控制域结构"""

    class BitField(ctypes.Structure):
        _fields_ = [
            ("mode", ctypes.c_uint8, 6),  # 通信方式
            ("prm", ctypes.c_uint8, 1),  # 启动标志
            ("dir", ctypes.c_uint8, 1)  # 传输方向
        ]

    _fields_ = [
        ("bit", BitField),
        ("ctrl", ctypes.c_uint8)  # 控制域字节
    ]


class INFO13762(ctypes.Union):
    """信息域结构"""

    class Down(ctypes.Structure):
        _fields_ = [
            ("rout_id", ctypes.c_uint8, 1),
            ("attach_id", ctypes.c_uint8, 1),
            ("module_id", ctypes.c_uint8, 1),  # 通信模块标识
            ("clash_check", ctypes.c_uint8, 1),
            ("relay_lev", ctypes.c_uint8, 4),  # 中继级别
            # ("serial_num", ctypes.c_uint8, 8),  # 帧序号
        ]

    _fields_ = [
        ("down", Down),
        ("buff", Uint8Array6),  # 6字节缓冲区
    ]


class ADDR13762(ctypes.Structure):
    """地址域结构"""
    _fields_ = [
        ("src", Uint8Array6),  # 源地址
        ("relay", Uint8Array12),  # 中继地址
        ("dst", Uint8Array6)  # 目的地址
    ]


class GW13762(ctypes.Structure):
    """GW13762协议帧结构"""
    _fields_ = [
        ("header", ctypes.c_uint8),  # 帧头
        ("length", ctypes.c_uint16),  # 长度
        ("ctrl", CTRL13762),  # 控制域
        ("info", INFO13762),  # 信息域
        ("addr", ADDR13762),  # 地址域
        ("afn", ctypes.c_uint8),  # AFN功能码
        ("fn", ctypes.c_uint8),  # FN功能码
        ("bufflen", ctypes.c_uint16),  # 数据长度
        ("buff", Uint8Array2112),  # 数据缓冲区
        ("cs", ctypes.c_uint8),  # 校验和
        ("end_char", ctypes.c_uint8)  # 帧尾
    ]


class SLocalFrame(ctypes.Structure):
    """本地帧结构"""
    _fields_ = [
        ("frame", GW13762),  # 协议帧
        ("data", Uint8Array4096),  # 原始数据
        ("datalen", ctypes.c_uint16)  # 数据长度
    ]


class SApsAffair(ctypes.Structure):
    """事务结构"""

    class PSrc(ctypes.Union):
        _fields_ = [
            ("local", SLocalFrame)  # 本地帧
        ]

    _fields_ = [
        ("p_src", PSrc)
    ]


def gw13762_dt_to_fn(dt1: int, dt2: int) -> int:
    """将DT1和DT2转换为FN码"""
    tmp_x = 0
    dt1_map = {1: 1, 2: 2, 4: 3, 8: 4, 16: 5, 32: 6, 64: 7, 128: 8}
    tmp_x = dt1_map.get(dt1, 0)
    return (tmp_x + (dt2 << 3)) if tmp_x else 0


def gw13762_fn_to_dt(fn: int) -> Tuple[int, int]:
    """将FN码转换为DT1和DT2"""
    dt2 = (fn >> 3) & 0xFF  # DT2是高5位
    dt1_val = fn & 0x07  # DT1是低3位

    # 反转dt1_map
    dt1_map = {1: 1, 2: 2, 4: 3, 8: 4, 16: 5, 32: 6, 64: 7, 128: 8}
    dt1_rev_map = {v: k for k, v in dt1_map.items()}

    return dt1_rev_map.get(dt1_val, 0), dt2


def gw13762_check(p_affair, dir: int) -> Tuple[bool, int]:
    """
    GW13762协议帧校验函数（带调试信息）
    """
    crc = 0
    tmp_buf = None
    relaylen = 0
    datalen = 0

    # 获取帧数据
    plocal_src = ctypes.pointer(p_affair.p_src.local)
    p_rx = ctypes.pointer(plocal_src.contents.frame)
    p_rxbuf = (ctypes.c_uint8 * plocal_src.contents.datalen).from_address(
        ctypes.addressof(plocal_src.contents.data)
    )

    # 调试信息：打印原始数据
    print("\n原始帧数据:")
    print([hex(p_rxbuf[i]) for i in range(plocal_src.contents.datalen)])

    # 拷贝信息域（至少需要10字节数据）
    if plocal_src.contents.datalen >= 10:
        # 信息域从第4字节开始，共6字节
        tmp_buf = (ctypes.c_uint8 * 6).from_address(
            ctypes.addressof(p_rxbuf) + 4  # p_rxbuf[4:]开始的6字节
        )
        # 复制到info.buff
        for i in range(6):
            p_rx.contents.info.buff[i] = tmp_buf[i]
    else:
        print("调试：数据长度不足10字节，无法解析信息域")
        return False, ErrorCode.FN_DENY_05H

    # 检测帧头
    if p_rxbuf[0] != 0x68:
        print(f"调试：帧头错误，预期0x68，实际0x{p_rxbuf[0]:02X}")
        return False, ErrorCode.FN_DENY_05H

    # 解析长度（大端模式）
    datalen = (p_rxbuf[2] << 8) | p_rxbuf[1]
    print(f"调试：解析得到长度: {datalen}")

    # 检测长度合法性
    if datalen < LOCAL_FRAME_LEN_MIN or plocal_src.contents.datalen < datalen:
        print(f"调试：长度错误，datalen={datalen}, 实际数据长度={plocal_src.contents.datalen}")
        return False, ErrorCode.FN_DENY_02H

    # 解析控制域并检测方向
    p_rx.contents.ctrl.ctrl = p_rxbuf[3]
    print(f"调试：控制域值=0x{p_rxbuf[3]:02X}, 解析得到方向={p_rx.contents.ctrl.bit.dir}, 预期方向={dir}")
    if p_rx.contents.ctrl.bit.dir != dir:
        print(f"调试：方向错误，预期{dir}，实际{p_rx.contents.ctrl.bit.dir}")
        return False, ErrorCode.FN_DENY_05H

    # 检测帧尾
    if p_rxbuf[datalen - 1] != 0x16:
        print(f"调试：帧尾错误，预期0x16，实际0x{p_rxbuf[datalen - 1]:02X}")
        return False, ErrorCode.FN_DENY_05H

    # 保存基本信息
    p_rx.contents.header = p_rxbuf[0]
    p_rx.contents.length = datalen
    p_rx.contents.end_char = p_rxbuf[datalen - 1]

    # 计算并校验校验和
    crc = p_rxbuf[3]  # 从控制域开始计算
    for i in range(datalen - 6):
        crc += p_rxbuf[4 + i]
    crc &= 0xFF  # 确保是8位
    print(f"调试：计算得到校验和=0x{crc:02X}, 帧中校验和=0x{p_rxbuf[datalen - 2]:02X}")
    if p_rxbuf[datalen - 2] != crc:
        return False, ErrorCode.FN_DENY_03H

    # 处理地址域和功能码
    print(f"调试：module_id={p_rx.contents.info.down.module_id}, HOST_NODE={HOST_NODE}")
    if p_rx.contents.info.down.module_id == HOST_NODE:
        # 无地址域情况 - 正确解析AFN和FN的位置
        if tmp_buf:
            # AFN位于信息域后的第一个字节
            afn_pos = 4 + 6  # 帧头(1) + 长度(2) + 控制域(1) + 信息域(6) = 10字节，AFN在第11字节
            p_rx.contents.afn = p_rxbuf[afn_pos] if afn_pos < datalen else 0

            dt1_pos = afn_pos + 1  # DT1在AFN后
            dt2_pos = afn_pos + 2  # DT2在DT1后
            dt1 = p_rxbuf[dt1_pos] if dt1_pos < datalen else 0
            dt2 = p_rxbuf[dt2_pos] if dt2_pos < datalen else 0
            p_rx.contents.fn = gw13762_dt_to_fn(dt1, dt2)

            print(f"调试：无地址域 - AFN位置={afn_pos}, DT1位置={dt1_pos}, DT2位置={dt2_pos}")
            print(f"调试：AFN=0x{p_rx.contents.afn:02X}, DT1=0x{dt1:02X}, DT2=0x{dt2:02X}, FN=0x{p_rx.contents.fn:02X}")

            # 处理数据域
            p_rx.contents.bufflen = datalen - LOCAL_FRAME_LEN_MIN
            data_start = afn_pos + 3  # 数据在DT2之后
            for i in range(p_rx.contents.bufflen):
                if data_start + i < datalen - 2:  # 减去校验和和帧尾
                    p_rx.contents.buff[i] = p_rxbuf[data_start + i]
    else:
        # 有地址域情况
        if p_rx.contents.info.down.relay_lev == 0:
            # 无中继
            if datalen < (LOCAL_FRAME_LEN_MIN + LOCAL_ADDR_LEN * 2):
                return False, ErrorCode.FN_DENY_02H

            # 复制源地址和目的地址
            for i in range(LOCAL_ADDR_LEN):
                p_rx.contents.addr.src[i] = tmp_buf[6 + i]
                p_rx.contents.addr.dst[i] = tmp_buf[6 + LOCAL_ADDR_LEN + i]

            # 解析AFN和FN
            afn_pos = 6 + LOCAL_ADDR_LEN * 2
            p_rx.contents.afn = tmp_buf[afn_pos] if afn_pos < len(tmp_buf) else 0
            dt1 = tmp_buf[afn_pos + 1] if (afn_pos + 1) < len(tmp_buf) else 0
            dt2 = tmp_buf[afn_pos + 2] if (afn_pos + 2) < len(tmp_buf) else 0
            p_rx.contents.fn = gw13762_dt_to_fn(dt1, dt2)

            # 处理数据域
            p_rx.contents.bufflen = datalen - 27
            for i in range(p_rx.contents.bufflen):
                pos = 6 + LOCAL_ADDR_LEN * 2 + 3 + i
                if pos < len(tmp_buf):
                    p_rx.contents.buff[i] = tmp_buf[pos]
        else:
            # 有中继
            relaylen = p_rx.contents.info.down.relay_lev * LOCAL_ADDR_LEN
            if datalen < (LOCAL_FRAME_LEN_MIN + LOCAL_ADDR_LEN * 2 + relaylen):
                return False, ErrorCode.FN_DENY_02H

            # 复制源地址、中继地址和目的地址
            for i in range(LOCAL_ADDR_LEN):
                p_rx.contents.addr.src[i] = tmp_buf[6 + i]

            for i in range(relaylen):
                p_rx.contents.addr.relay[i] = tmp_buf[6 + LOCAL_ADDR_LEN + i]

            for i in range(LOCAL_ADDR_LEN):
                p_rx.contents.addr.dst[i] = tmp_buf[6 + LOCAL_ADDR_LEN + relaylen + i]

            # 解析AFN和FN
            afn_pos = 6 + LOCAL_ADDR_LEN * 2 + relaylen
            p_rx.contents.afn = tmp_buf[afn_pos] if afn_pos < len(tmp_buf) else 0
            dt1 = tmp_buf[afn_pos + 1] if (afn_pos + 1) < len(tmp_buf) else 0
            dt2 = tmp_buf[afn_pos + 2] if (afn_pos + 2) < len(tmp_buf) else 0
            p_rx.contents.fn = gw13762_dt_to_fn(dt1, dt2)

            # 处理数据域
            p_rx.contents.bufflen = datalen - 27 - relaylen
            for i in range(p_rx.contents.bufflen):
                pos = 6 + LOCAL_ADDR_LEN * 2 + relaylen + 3 + i
                if pos < len(tmp_buf):
                    p_rx.contents.buff[i] = tmp_buf[pos]

    return True, ErrorCode.FN_ACK_FFH


def gw13762_build_frame(
        dir: int,
        prm: int,
        mode: int,
        afn: int,
        fn: int,
        serial_num: int,
        module_id: int = 0,
        relay_lev: int = 0,
        src_addr: list = None,
        dst_addr: list = None,
        relay_addrs: list = None,
        data: list = None
) -> Tuple[list, int]:
    """
    构建GW13762协议帧

    参数:
        dir: 传输方向 (0: 下行, 1: 上行)
        prm: 启动标志 (0: 从动站, 1: 启动站)
        mode: 通信方式 (0-63)
        afn: AFN功能码
        fn: FN功能码
        module_id: 通信模块标识 (0: 主节点, 1: 其他)
        relay_lev: 中继级别 (0-15)
        src_addr: 源地址列表 (6字节)
        dst_addr: 目的地址列表 (6字节)
        relay_addrs: 中继地址列表
        data: 数据域列表

    返回:
        (构建的帧数据, 错误码) 成功返回(帧数据列表, 0xFF)，失败返回(None, 错误码)
    """
    # 初始化默认值
    src_addr = src_addr or [0] * LOCAL_ADDR_LEN
    dst_addr = dst_addr or [0] * LOCAL_ADDR_LEN
    relay_addrs = relay_addrs or []
    data = data or []

    # 参数校验
    if len(src_addr) != LOCAL_ADDR_LEN:
        return None, ErrorCode.FN_DENY_05H
    if len(dst_addr) != LOCAL_ADDR_LEN:
        return None, ErrorCode.FN_DENY_05H
    if relay_lev < 0 or relay_lev > 15:
        return None, ErrorCode.FN_DENY_05H
    if mode < 0 or mode > 63:
        return None, ErrorCode.FN_DENY_05H

    # 计算帧长度
    frame_parts = []

    # 1. 帧头 (1字节)
    frame_parts.append(0x68)

    # 先预留长度字段位置(2字节)，后面会计算并填充
    length_pos = len(frame_parts)
    frame_parts.extend([0x00, 0x00])  # 占位

    # 2. 控制域 (1字节)
    ctrl = CTRL13762()
    ctrl.bit.dir = dir
    ctrl.bit.prm = prm
    ctrl.bit.mode = mode
    frame_parts.append(ctrl.ctrl)

    # 3. 信息域 (6字节)
    info = INFO13762()
    info.down.module_id = module_id
    info.down.relay_lev = relay_lev
    info.down.rout_id = 1 if relay_lev > 0 else 0  # 有中继则带路由
    info.down.attach_id = 0  # 无附加节点
    info.down.clash_check = 0  # 不进行冲突检测

    # 填充信息域缓冲区的其他字节
    # for i in range(6):
    #     info.buff[i] = 0x00  # 可以根据实际需求设置
    info.buff = (0x00, 0x00, 0x40, 0x00, 0x00)
    info.buff[5] = serial_num
    frame_parts.extend(info.buff)

    # 4. 地址域 (仅当不是主节点时)
    if module_id != HOST_NODE and relay_lev == 0:
        # 无中继，添加源地址和目的地址
        frame_parts.extend(src_addr)
        frame_parts.extend(dst_addr)
    elif module_id != HOST_NODE and relay_lev > 0:
        # 有中继，添加源地址、中继地址和目的地址
        frame_parts.extend(src_addr)
        frame_parts.extend(relay_addrs)
        frame_parts.extend(dst_addr)

    # 5. 功能码域
    frame_parts.append(afn)  # AFN

    # 将FN转换为DT1和DT2
    dt1, dt2 = gw13762_fn_to_dt(fn)
    frame_parts.append(dt1)  # DT1
    frame_parts.append(dt2)  # DT2

    # 6. 数据域
    frame_parts.extend(data)

    # 7. 校验和 (先预留位置)
    cs_pos = len(frame_parts)
    frame_parts.append(0x00)  # 占位

    # 8. 帧尾
    frame_parts.append(0x16)

    # 计算实际帧长度并填充
    frame_length = len(frame_parts)
    frame_parts[length_pos] = frame_length & 0xFF  # 低8位
    frame_parts[length_pos + 1] = (frame_length >> 8) & 0xFF  # 高8位

    # 计算校验和 (从控制域开始到数据域结束)
    crc = 0
    for i in range(3, len(frame_parts) - 2):  # 控制域到数据域最后一个字节
        crc += frame_parts[i]
    crc &= 0xFF  # 确保是8位
    frame_parts[cs_pos] = crc

    return frame_parts, ErrorCode.FN_ACK_FFH


def create_default_frame(afn: int, fn: int, serial_num: int, data: list) -> Tuple[list, int]:
    """
    创建默认参数的GW13762协议帧（简化调用）

    参数:
        afn: AFN功能码（必填）
        fn: FN功能码（必填）
        serial_num: 帧序号（必填，1字节）
        data: 数据域列表（必填）

    默认参数:
        dir=1 (下行), prm=0 (从动站), module_id=0 (主节点), relay_lev=0 (无中继), mode=0x03 (宽带载波)

    返回:
        (构建的帧数据列表, 错误码)
    """
    return gw13762_build_frame(
        dir=1,  # 默认：下行
        prm=0,  # 默认：从动站
        mode=0x03,  # 默认：宽带载波通信（参考示例）
        afn=afn,  # 输入：AFN功能码
        fn=fn,  # 输入：FN功能码
        serial_num=serial_num,  # 输入：帧序号
        module_id=0,  # 默认：对主节点操作
        relay_lev=0,  # 默认：无中继
        data=data  # 输入：数据域
    )


# 测试构帧函数
def wwgw13762_check():
    """测试构帧后立即进行校验，验证两者的兼容性"""
    # 构建一个查询主节点地址的帧
    frame_data, err = gw13762_build_frame(
        dir=1,  # 下行
        prm=0,  # 从动站
        mode=0x03,  # 宽带载波通信
        afn=0x03,  # 查询数据
        fn=0x04,  # 查询主节点地址
        module_id=0,  # 对主节点操作
        relay_lev=0,  # 无中继
        data=[0x51, 0x81, 0x01, 0x00, 0x00, 0x10],
        serial_num=0x07
    )

    if err == ErrorCode.FN_ACK_FFH:
        print("构帧成功:")
        print(" ".join([f"{b:02X}" for b in frame_data]))

        # 验证构建的帧是否能通过校验
        affair = SApsAffair()
        frame = affair.p_src.local
        frame.datalen = len(frame_data)

        # 填充测试数据
        for i in range(len(frame_data)):
            frame.data[i] = frame_data[i]

        # 执行校验
        success, err = gw13762_check(affair, 1)
        print(f"\n校验结果: {'成功' if success else '失败'}")
        print(f"错误码: 0x{err:02X}")

        if success:
            rx_frame = frame.frame
            print(f"解析结果: AFN=0x{rx_frame.afn:02X}, FN=0x{rx_frame.fn:02X}")
            # 新增：打印数据域（十六进制格式）
            data_field = [f"{rx_frame.buff[i]:02X}" for i in range(rx_frame.bufflen)]
            print(f"数据域: [{', '.join(data_field)}]")

    else:
        print(f"构帧失败，错误码: 0x{err:02X}")


# 测试自定义帧校验
def www_custom_frame_check():
    """测试用户提供的自定义帧的校验"""
    # 创建测试事务对象
    affair = SApsAffair()
    frame = affair.p_src.local

    # 构造测试帧
    test_data = [0x68,0x38,0x00,0xC3,0x00,0x00,0x40,0x00,0x00,0x01,0x03,0x02,0x01,0xF2,0x37,0x08,0x01,0x00,0x00,0x3C,0x14,0x00,0x4F,0x04,0x00,0x04,0x0C,0x51,0x81,0x01,0x00,0x00,0x10,0x80,0x04,0x02,0x00
        ,0x10,0x10,0x13,0x10,0x10,0x13,0x43,0x46,0x38,0x46,0x22,0x11,0x24,0x01,0x24,0x64,0x80,0x25,0x16]
    frame.datalen = len(test_data)

    # 填充测试数据
    for i in range(len(test_data)):
        frame.data[i] = test_data[i]

    # 执行校验（预期方向为0，下行）
    success, err = gw13762_check(affair, 0)
    print(f"\n校验结果: {'成功' if success else '失败'}")
    print(f"错误码: 0x{err:02X}")

    if success:
        rx_frame = frame.frame
        print(f"解析结果: AFN=0x{rx_frame.afn:02X}, FN=0x{rx_frame.fn:02X}")
        print(f"源地址: {[hex(b) for b in rx_frame.addr.src]}")
        print(f"目的地址: {[hex(b) for b in rx_frame.addr.dst]}")


# if __name__ == "__main__":
#     print("=== 测试构帧与校验的兼容性 ===")
#     wwgw13762_check()
#     print("\n=== 测试自定义帧校验 ===")
#     # www_custom_frame_check()

# 为了打印所有信息，检查一遍
def parse_and_print_frame(frame_data: list, expected_dir: int = 1):
    """解析并打印帧数据的每个成员"""
    # 创建事务对象
    affair = SApsAffair()
    frame = affair.p_src.local
    frame.datalen = len(frame_data)

    # 填充帧数据
    for i in range(len(frame_data)):
        frame.data[i] = frame_data[i]

    # 执行校验
    success, err = gw13762_check(affair, expected_dir)
    print(f"\n校验结果: {'成功' if success else '失败'}")
    print(f"错误码: 0x{err:02X}")

    if not success:
        return

    # 获取解析后的帧
    rx_frame = frame.frame

    # 打印帧的每个成员
    print("\n=== 帧结构详细信息 ===")
    print(f"帧头 (header): 0x{rx_frame.header:02X}")
    print(f"长度 (length): {rx_frame.length} (0x{rx_frame.length:04X})")

    print("\n控制域 (ctrl):")
    print(f"  控制字节: 0x{rx_frame.ctrl.ctrl:02X}")
    print(f"  传输方向 (dir): {rx_frame.ctrl.bit.dir} ({'上行' if rx_frame.ctrl.bit.dir == 1 else '下行'})")
    print(f"  启动标志 (prm): {rx_frame.ctrl.bit.prm}")
    print(f"  通信方式 (mode): 0x{rx_frame.ctrl.bit.mode:02X}")

    print("\n信息域 (info):")
    print(f"  模块标识 (module_id): {rx_frame.info.down.module_id}")
    print(f"  中继级别 (relay_lev): {rx_frame.info.down.relay_lev}")
    print(f"  路由标识 (rout_id): {rx_frame.info.down.rout_id}")
    print(f"  附加节点 (attach_id): {rx_frame.info.down.attach_id}")
    print(f"  冲突检测 (clash_check): {rx_frame.info.down.clash_check}")
    print(f"  缓冲区 (buff): {[hex(b) for b in rx_frame.info.buff]}")
    print(f"  帧序号 (serial_num): 0x{rx_frame.info.buff[0]:02X}")

    print("\n地址域 (addr):")
    print(f"  源地址 (src): {[hex(b) for b in rx_frame.addr.src]}")
    print(f"  目的地址 (dst): {[hex(b) for b in rx_frame.addr.dst]}")
    print(f"  中继地址 (relay): {[hex(b) for b in rx_frame.addr.relay if b != 0]}")  # 只显示非零值

    print("\n功能码域:")
    print(f"  AFN: 0x{rx_frame.afn:02X}")
    print(f"  FN: 0x{rx_frame.fn:02X}")
    dt1, dt2 = gw13762_fn_to_dt(rx_frame.fn)
    print(f"  DT1: 0x{dt1:02X}, DT2: 0x{dt2:02X}")

    print("\n数据域:")
    print(f"  数据长度 (bufflen): {rx_frame.bufflen}")
    print(f"  数据内容 (buff): {[hex(rx_frame.buff[i]) for i in range(rx_frame.bufflen)]}")

    print("\n校验与帧尾:")
    print(f"  校验和 (cs): 0x{rx_frame.cs:02X}")
    print(f"  帧尾 (end_char): 0x{rx_frame.end_char:02X}")


# def main():
#     frame_hex_str = "68 38 00 C3 00 00 40 00 00 01 03 02 01 F2 37 08 01 00 00 3C 14 00 4F 04 00 04 0C 51 81 01 00 00 10 80 04 02 00 10 10 13 10 10 13 43 46 38 46 22 11 24 01 24 64 80 25 16"
#
#     # 转换为整数列表
#     frame_data = [int(hex_str, 16) for hex_str in frame_hex_str.split()]
#
#     print(f"待解析帧数据长度: {len(frame_data)} 字节")
#     parse_and_print_frame(frame_data)
#
#
# if __name__ == "__main__":
#     main()
