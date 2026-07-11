# countText

`countText` is a utility tool to quickly count words, characters, and Chinese characters in mixed Chinese-English text files.

---

## 📖 Usage & Options

```bash
countText <mode> <file_path>
```

### Option Descriptions

- **`-zh` or `-ch`**
  Count the number of Chinese characters in the text file (matching Chinese Unicode ranges only).
- **`-cn`**
  Count the number of English words/characters in the text file (based on whitespace and punctuation word separation).
- **`-h`**
  Show the help menu.

---

## 💡 Examples

```bash
countText -zh document.txt   # Count Chinese characters in document.txt
countText -cn document.txt   # Count English words in document.txt
```

---

## ⚙️ How it Works

- Verifies that the file exists and is readable (returns exit code `1` if not readable).
- Utilizes efficient character matching algorithms (such as Chinese character range matching) to calculate and output formatted statistics.
