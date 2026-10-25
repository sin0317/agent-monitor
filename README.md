# Agent Monitor

轻量 AI IDE 会话监控器。监听 Trae / Qoder / WorkBuddy 的 hooks 事件，用 Windows 通知弹给你看，同时在控制台输出事件流。

不装一堆东西，只有两个 Python 脚本。

## 原理

```
IDE (Trae/Qoder/WorkBuddy)
    │  hooks 触发
    ▼
relay.py  ← 从 stdin 读 JSON，300ms 内转发到命名管道后立即退出（不阻塞 IDE）
    │
    ▼
\\.\pipe\agent-monitor
    │
    ▼
agent-monitor.py  ← 常驻服务，收事件 → 弹 Windows 通知 + 控制台输出
```

## 依赖

- Python 3.10+
- `winotify`（Windows 通知）

```bash
pip install winotify
```

## 快速开始

### 1. 启动监控器

```bash
python agent-monitor.py
```

后台运行（Windows）：

```powershell
Start-Process python -ArgumentList "agent-monitor.py" -WindowStyle Hidden
```

### 2. 配置 IDE hooks

在每个 IDE 的 hooks 配置里，把事件转发给 `relay.py`。命令格式：

```
"C:\Path\To\python.exe" "C:\Path\To\relay.py" <agent-name>
```

`<agent-name>` 可以是 `trae`、`qoder`、`workbuddy` 或任意自定义名。

#### Trae CN

编辑 `%USERPROFILE%\.trae-cn\hooks.json`：

```json
{
  "version": 1,
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" trae", "timeout": 3}]}],
    "UserPromptSubmit": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" trae", "timeout": 3}]}],
    "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" trae", "timeout": 3}]}],
    "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" trae", "timeout": 3}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" trae", "timeout": 3}]}]
  }
}
```

> Trae 的 Hook 运行方式需设为**本地自动运行**（沙箱模式连不上命名管道）。

#### Qoder CN

编辑 `%USERPROFILE%\.qoder-cn\settings.json`，在 `hooks` 字段中加入：

```json
{
  "hooks": {
    "SessionStart": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}],
    "UserPromptSubmit": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}],
    "PreToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}],
    "PostToolUse": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}],
    "SessionEnd": [{"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" qoder", "timeout": 3, "async": true}]}]
  }
}
```

> Qoder 改完配置需重启 IDE。

#### WorkBuddy / CodeBuddy

编辑 `%USERPROFILE%\.workbuddy\settings.json`（或 `.codebuddy\settings.json`），在对应事件下追加 relay hook，保留你已有的其他 hooks。

```json
{
  "hooks": {
    "SessionStart": [
      {"matcher": "", "hooks": [{"type": "command", "command": "\"C:\\Python313\\python.exe\" \"C:\\agent-monitor\\relay.py\" workbuddy", "timeout": 3, "async": true}]}
    ]
  }
}
```

## 会弹通知的事件

| 事件 | 通知内容 |
|---|---|
| `SessionStart` | 哪个 IDE 开了新会话 |
| `Stop` | 会话完成 |
| `SessionEnd` | 会话结束 |
| `PermissionRequest` | 请求批准权限（仍需在 IDE 里点批准） |
| `Notification` | 其他通知 |

所有事件（包括每次工具调用）都会打印在监控器的控制台。

## 开机自启

用 Windows 任务计划程序，登录时自动启动：

```powershell
schtasks /Create /TN "AgentMonitor" /TR "\"C:\Python313\python.exe\" \"C:\agent-monitor\agent-monitor.py\"" /SC ONLOGON /RL HIGHEST /F
```

把路径换成你自己的。删除自启：

```powershell
schtasks /Delete /TN "AgentMonitor" /F
```

## 限制

- 当前版本只做**监控通知**，不能在通知里直接 Allow/Deny 权限请求（需回 IDE 操作）。
- 仅 Windows（命名管道 + winotify 通知）。

## License

MIT
