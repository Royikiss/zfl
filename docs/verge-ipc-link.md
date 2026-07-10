# verge-ipc-link

`verge-ipc-link` 用于在 Linux 环境下快速建立 Clash Verge 服务的 IPC Socket 软链接，解决部分 GUI 客户端由于默认套接字路径不一致而无法连接后端服务的问题。

---

## 📖 用法与选项

```bash
verge-ipc-link [选项]
```

### 选项说明

- **`-h, --help`**
  显示帮助信息并退出。

---

## ⚙️ 运行机制与等价操作

在特定 Linux 发行版或部分 Clash Verge 安装包中，服务生成的 IPC 套接字保存在 `/tmp/clash-verge-service-ipc-test/service.sock`。然而，GUI 客户端默认会寻找 `/tmp/verge/clash-verge-service.sock`，导致通信异常。

本命令相当于自动执行了以下具有容错处理的命令：
```bash
sudo mkdir -p /tmp/verge
sudo ln -sf /tmp/clash-verge-service-ipc-test/service.sock /tmp/verge/clash-verge-service.sock
```
运行本命令后，GUI 客户端将能够正常与底层 Clash Verge 服务建立 IPC 连接。
