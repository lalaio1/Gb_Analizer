# 🛠️ Gb_Analizer

A powerful tool for reverse engineering grabbers (malware) to extract webhooks and tokens.

## 🌟 Features

- **Reverse Engineer** grabbers and extract webhooks and tokens.
- Supports multiple deobfuscation methods.
- Handles both Java and Python-based grabbers.
- Outputs details in JSON format.

## 📦 Installation

### Windows

1. **Clone the repository**:
    ```sh
    git clone https://github.com/lalaio1/Gb_Analizer.git
    cd grabber-deobfuscator
    ```

2. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```

### Linux

1. **Clone the repository**:
    ```sh
    git clone https://github.com/lalaio1/Gb_Analizer.git
    cd grabber-deobfuscator
    ```

2. **Install dependencies**:
    ```sh
    pip install -r requirements.txt
    ```



> **Note**: Python 3.9 or higher is required.

## 🚀 Usage

```sh
python deobfuscator.py <filename> [options]
```

### Options

- `-d`, `--download`: Download the file from a link.
- `-j`, `--json`: Output details in JSON format.

### Example

```sh
python deobfuscator.py example_grabber.py -j
```

## 🎨 Example Output

```json
{
    "type": "python grabber",
    "webhook": "https://discord.com/api/webhooks/...",
    "pyinstaller_version": "4.5",
    "python_version": "3.9"
}
```

## 👨‍💻 Author

- Developed by TaxMachine. Please give a star on [GitHub](https://github.com/lalaio1).

## 📝 License

This project is licensed under the MIT License.
