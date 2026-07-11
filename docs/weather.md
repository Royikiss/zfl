# weather

`weather` is a quick utility to query real-time weather and weather forecasts directly from the terminal.

---

## 📖 Usage & Examples

```bash
weather [city_name/pinyin]
```

### Examples
```bash
weather beijing    # Query Beijing weather
weather shanghai   # Query Shanghai weather
```

---

## ⚙️ How it Works

1. The function dynamically loads terminal color presets.
2. It sends an HTTP request to [wttr.in](https://wttr.in) using `curl wttr.in/<city_name>`, rendering colorized weather forecasts with ASCII art directly in the terminal.
