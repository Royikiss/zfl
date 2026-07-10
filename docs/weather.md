# weather

`weather` 是一个快速在终端中查询实时天气和天气预报的小工具。

---

## 📖 用法与示例

```bash
weather [城市名称/拼音]
```

### 示例
```bash
weather beijing    # 查询北京的天气
weather shanghai   # 查询上海的天气
```

---

## ⚙️ 运行机制

1. 该函数动态加载终端颜色预设。
2. 利用 `curl wttr.in/<城市名>` 接口向 [wttr.in](https://wttr.in) 发起请求，并在终端中直接渲染带有 ASCII 艺术和彩色的天气预报图表。
