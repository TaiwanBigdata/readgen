# ReadGen

一個簡單但強大的 Python 專案 README.md 自動產生工具。

## 功能特色

-   自動掃描專案結構並產生目錄說明
-   從 project.yaml 讀取專案設定
-   支援解析 .env.example 產生環境變數說明
-   自動擷取各資料夾 **init**.py 的 docstring
-   產生標準化的 Markdown 格式文件

## 安裝方式

```bash
pip install readgen
```

## 使用方法

### 基本使用

```python
from readgen import ReadmeGenerator

# 建立產生器實例
generator = ReadmeGenerator()

# 產生 README 內容
readme_content = generator.generate()

# 內容會自動寫入專案根目錄的 README.md
```

### 專案設定檔

在專案根目錄建立 `project.yaml`：

```yaml
project:
    name: '專案名稱'
    description: '專案描述'

authors:
    - name: '作者名稱'
      email: 'email@example.com'

dependencies:
    - python >= 3.7
    - PyYAML >= 6.0.1
```

## 相容性

Python 3.7 或以上版本
支援 Windows, macOS 和 Linux

## 授權條款

本專案採用 MIT License 授權。詳見 LICENSE 檔案。

## 貢獻指南

歡迎提交 Issue 和 Pull Request！
