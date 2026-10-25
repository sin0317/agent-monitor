# -*- coding: utf-8 -*-
"""
agent-monitor.py — 轻量 AI IDE 会话监控器
监听命名管道 \\.\pipe\agent-monitor，接收 Trae / Qoder / WorkBuddy 的 hooks 事件，
用 Windows 通知弹给你看，同时在控制台输出事件流。
"""
import json
import os
import sys
import time
import threading
import subprocess
from datetime import datetime

try:
    from winotify import Notification, audio
    HAS_WINOTIFY = True
except Exception:
    HAS_WINOTIFY = False

PIPE_NAME = r"\\.\pipe\agent-monitor"

# 只对这些事件弹通知（避免刷屏）
NOTIFY_EVENTS = {"SessionStart", "Stop", "SessionEnd", "PermissionRequest", "Notification"}

# 活跃会话：session_id -> {agent, last_event, started}
sessions = {}
lock = threading.Lock()


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def emoji_for(agent):
    return {"trae": "🔵", "qoder": "🟢", "workbuddy": "🟠"}.get(agent, "⚪")


def show_toast(title, body, agent=""):
    """弹 Windows 通知"""
    if not HAS_WINOTIFY:
        return
    try:
        toast = Notification(
            app_id="Agent Monitor",
            title=title,
            msg=body,
            duration="short",
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except Exception as e:
        log(f"通知失败: {e}")


def short_prompt(prompt, maxlen=60):
    prompt = (prompt or "").replace("\n", " ").strip()
    return prompt if len(prompt) <= maxlen else prompt[:maxlen] + "…"


def handle_event(ev):
    """处理单个事件"""
    event_name = ev.get("hook_event_name") or ev.get("event") or "unknown"
    agent = ev.get("agent") or ev.get("source") or ev.get("coucou_agent") or "?"
    session_id = ev.get("session_id") or "?"
    tool_name = ev.get("tool_name") or ""
    prompt = ev.get("prompt") or ""
    perm = ev.get("permission_decision") or ev.get("message") or ""

    e = emoji_for(agent)

    with lock:
        if event_name == "SessionStart":
            sessions[session_id] = {"agent": agent, "started": time.time(), "last": event_name}
        elif session_id in sessions:
            sessions[session_id]["last"] = event_name

    # 控制台输出
    extra = ""
    if tool_name:
        extra = f" tool={tool_name}"
    if prompt and event_name == "UserPromptSubmit":
        extra = f" '{short_prompt(prompt)}'"
    if perm:
        extra = f" '{short_prompt(perm, 80)}'"
    log(f"{e} [{agent}] {event_name}{extra}")

    # 通知
    if event_name in NOTIFY_EVENTS:
        if event_name == "SessionStart":
            show_toast(f"{e} {agent} 新会话开始", f"session {session_id[:8]}")
        elif event_name == "Stop":
            show_toast(f"{e} {agent} 会话完成", "agent 已停下")
        elif event_name == "SessionEnd":
            with lock:
                sessions.pop(session_id, None)
            show_toast(f"{e} {agent} 会话结束", "bye")
        elif event_name == "PermissionRequest":
            show_toast(f"{e} {agent} 请求批准权限", short_prompt(perm, 100) or "请在 IDE 中处理")
        elif event_name == "Notification":
            show_toast(f"{e} {agent}", short_prompt(perm, 100) or "通知")


def pipe_server():
    """命名管道服务器，循环接收事件"""
    import ctypes
    PIPE_ACCESS_DUPLEX = 0x00000003
    PIPE_TYPE_MESSAGE = 0x00000004
    PIPE_WAIT = 0x00000000
    PIPE_UNLIMITED_INSTANCES = 255
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    CreateNamedPipe = ctypes.windll.kernel32.CreateNamedPipeW
    ConnectNamedPipe = ctypes.windll.kernel32.ConnectNamedPipe
    ReadFile = ctypes.windll.kernel32.ReadFile
    DisconnectNamedPipe = ctypes.windll.kernel32.DisconnectNamedPipe
    CloseHandle = ctypes.windll.kernel32.CloseHandle

    log(f"监听命名管道: {PIPE_NAME}")
    while True:
        hPipe = CreateNamedPipe(
            PIPE_NAME, PIPE_ACCESS_DUPLEX,
            PIPE_TYPE_MESSAGE | PIPE_WAIT,
            PIPE_UNLIMITED_INSTANCES,
            65536, 65536, 0, None,
        )
        if hPipe == INVALID_HANDLE_VALUE:
            log("创建管道失败，5 秒后重试")
            time.sleep(5)
            continue

        if ConnectNamedPipe(hPipe, None) == 0:
            err = ctypes.get_last_error()
            if err != 536:  # ERROR_PIPE_CONNECTED
                CloseHandle(hPipe)
                continue

        # 读取数据
        buf = ctypes.create_string_buffer(65536)
        read = ctypes.c_ulong(0)
        data = b""
        while True:
            ok = ReadFile(hPipe, buf, 65536, ctypes.byref(read), None)
            if not ok or read.value == 0:
                break
            data += buf.raw[:read.value]
            if b"\n" in buf.raw[:read.value]:
                break

        DisconnectNamedPipe(hPipe)
        CloseHandle(hPipe)

        if not data:
            continue

        # 解析（可能多条，按行）
        for line in data.split(b"\n"):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line.decode("utf-8", "ignore"))
                handle_event(ev)
            except Exception as ex:
                log(f"解析失败: {ex} | {line[:120]}")


def main():
    print("=" * 60)
    print("  Agent Monitor — 轻量 AI IDE 会话监控")
    print("  Ctrl+C 退出")
    print("=" * 60)
    try:
        pipe_server()
    except KeyboardInterrupt:
        log("已退出")


if __name__ == "__main__":
    main()
