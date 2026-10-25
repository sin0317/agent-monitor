# -*- coding: utf-8 -*-
"""
relay.py — hooks 转发脚本
被 Trae / Qoder / WorkBuddy 的 hooks 调用，从 stdin 读 JSON 事件，
转发到 agent-monitor 的命名管道，然后立即退出（不阻塞 IDE）。

用法: echo '{"hook_event_name":"SessionStart",...}' | py relay.py trae
"""
import json
import sys
import time
import ctypes

PIPE_NAME = r"\\.\pipe\agent-monitor"
TIMEOUT = 0.3  # 最多等 300ms，连不上就放弃

GENERIC_READ_WRITE = 0xC0000000
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def forward(payload_str, agent):
    """把 payload 转发到命名管道"""
    # 补上 agent 字段
    try:
        ev = json.loads(payload_str)
        if "agent" not in ev:
            ev["agent"] = agent
        payload_str = json.dumps(ev, ensure_ascii=False)
    except Exception:
        pass  # 解析失败就原样转发

    CreateFile = ctypes.windll.kernel32.CreateFileW
    WriteFile = ctypes.windll.kernel32.WriteFile
    CloseHandle = ctypes.windll.kernel32.CloseHandle

    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        h = CreateFile(PIPE_NAME, GENERIC_READ_WRITE, 0, None, OPEN_EXISTING, 0, None)
        if h != INVALID_HANDLE_VALUE:
            data = (payload_str + "\n").encode("utf-8")
            written = ctypes.c_ulong(0)
            WriteFile(h, data, len(data), ctypes.byref(written), None)
            CloseHandle(h)
            return True
        # 管道忙，稍等重试
        time.sleep(0.02)
    return False


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    payload = sys.stdin.read()
    if not payload.strip():
        return
    forward(payload, agent)


if __name__ == "__main__":
    main()
