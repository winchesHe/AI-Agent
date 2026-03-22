# Hello-Agent 守护进程配置

本目录提供 macOS 和 Linux 下将 Hello-Agent 注册为守护进程（后台常驻服务）的示例配置文件。

---

## macOS（launchd）

1. 复制并编辑 plist 文件，将 `WorkingDirectory` 修改为实际项目路径：

   ```bash
   cp hello-agent.plist ~/Library/LaunchAgents/com.hello-agent.daemon.plist
   # 编辑文件，替换 /path/to/Hello-Agent/src 为实际路径
   ```

2. 加载服务：

   ```bash
   launchctl load ~/Library/LaunchAgents/com.hello-agent.daemon.plist
   ```

3. 查看运行状态：

   ```bash
   launchctl list | grep hello-agent
   ```

4. 停止并卸载服务：

   ```bash
   launchctl unload ~/Library/LaunchAgents/com.hello-agent.daemon.plist
   ```

5. 日志位置：
   - 标准输出：`/tmp/hello-agent-stdout.log`
   - 标准错误：`/tmp/hello-agent-stderr.log`

---

## Linux（systemd 用户级单元）

1. 复制并编辑 service 文件，将 `WorkingDirectory` 和 `ExecStart` 中的路径修改为实际值：

   ```bash
   mkdir -p ~/.config/systemd/user
   cp hello-agent.service ~/.config/systemd/user/
   # 编辑文件，替换 /path/to/Hello-Agent/src 为实际路径
   ```

2. 重新加载并启动服务：

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now hello-agent.service
   ```

3. 查看运行状态：

   ```bash
   systemctl --user status hello-agent.service
   ```

4. 查看日志：

   ```bash
   journalctl --user -u hello-agent.service -f
   ```

5. 停止服务：

   ```bash
   systemctl --user stop hello-agent.service
   ```
