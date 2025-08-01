# -*- mode: python ; coding: utf-8 -*-

# 导入PyInstaller构建所需的核心类
from PyInstaller.building.build_main import Analysis, PYZ, EXE

block_cipher = None

a = Analysis(
    ['main.py'],  # 主程序入口
    pathex=['D:\\pythoncharm\\pycode\\pythonProject'],  # 项目根目录
    binaries=[],
    datas=[
        # 添加资源文件（如有）
        ('protocol\\gw13762\\13762.py', 'protocol\\gw13762'),
        ('comport\\com_poer.py', 'comport'),
        ('serial_thread.py', '.'),
        ('upgrade_thread.py', '.')
    ],
    hiddenimports=[
        'gw13762.13762',
        'comport.com_poer',
        'serial_thread',
        'upgrade_thread',
        'serial_bsp',  # 添加串口相关模块
        'config',      # 添加配置模块
        'log'          # 添加日志模块
    ],  # 手动指定隐藏依赖
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MyApp',  # 生成的EXE文件名
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # 启用压缩
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 关闭控制台窗口（GUI程序）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='app_icon.ico'  # 可选：添加图标文件
)
