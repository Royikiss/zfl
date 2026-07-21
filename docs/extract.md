# extract (万能解压与一键压缩工具)

`extract` 是 ZFL 内置的高性能命令行解压与压缩一体化工具。设计遵循极简交互哲学：**不传格式参数默认自适应解压；传入格式参数直接一键压缩**。

---

## 📖 使用方法与示例

### 1. 默认解压模式 (无需任何选项)
直接传入压缩包文件名，自动识别格式并解压，内置“防解压炸弹”（Archive Bomb Defense）保护：
```bash
extract project.tar.gz               # 自动解压 tar.gz
x release.zip docs.7z                # 快捷别名，同时解压 zip 与 7z
```

### 2. 一键压缩模式 (直接指定目标格式参数)
无需指定 `-c`，只要传入格式选项（如 `--zip`, `--tar.gz`, `--7z`），直接触发打包压缩：
```bash
extract --zip my_folder/             # 自动压缩为 my_folder.zip
extract --tar.gz file1 dir2/        # 默认以首项命名压缩为 file1.tar.gz
extract --7z -o backup assets/      # 使用 -o 指定输出文件名为 backup.7z
```

---

## ⚙️ 格式参数对照表

| 选项参数 | 输出文件后缀 | 说明 |
| :--- | :--- | :--- |
| `--zip` | `.zip` | 通用 zip 压缩格式 |
| `--tar.gz` / `--tgz` | `.tar.gz` / `.tgz` | tar 打包 + gzip 压缩 |
| `--tar.bz2` / `--tbz2` | `.tar.bz2` / `.tbz2` | tar 打包 + bzip2 压缩 |
| `--tar.xz` / `--txz` | `.tar.xz` / `.txz` | tar 打包 + xz 极高压缩率 |
| `--tar.zst` / `--tzst` | `.tar.zst` / `.tzst` | tar 打包 + zstd 极速高压缩率 |
| `--7z` | `.7z` | 7-Zip 高压缩率归档 |
| `--rar` | `.rar` | RAR 归档格式 |
| `--tar` | `.tar` | 未压缩的 tar 打包归档 |

---

## 💡 Zsh Tab 自动补全

在终端输入 `extract --` 或 `x --` 并按 **Tab** 键，系统自动提示格式补全菜单与说明：

```bash
--zip      -- 一键压缩为 .zip 格式
--tar.gz   -- 一键打包压缩为 .tar.gz
--7z       -- 一键压缩为 7-Zip (.7z)
--tar.xz   -- 一键打包压缩为 .tar.xz (高压缩率)
-o         -- 指定输出文件名
```
