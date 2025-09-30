# LangChain 驱动的上下文感知文章写作系统

本项目是 `ContextArticleWriting` 项目的重构版本，完全基于 LangChain 框架构建，旨在打造一个由 AI 驱动的、能够结合外部知识进行科学文章写作的自动化系统。

## ✨ 功能特性

-   **Agentic 工作流**: 使用 LangGraph 构建具备工具调用能力的核心 Agent 工作流，使其能自主规划并执行任务。
-   **上下文感知**: 能从 PubMed、PMC 等外部数据源获取实时、专业的上下文信息。
-   **插件化设计**: 图像生成、翻译等功能作为独立插件，易于扩展。
-   **生产级架构**: 基于 FastAPI 构建，包含日志、追踪、异常处理等完善的基础设施。
-   **配置驱动**: 所有关键参数均通过环境变量 (`.env` 文件) 进行配置，灵活且安全。

## 🚀 快速开始

### 1. 环境要求

-   Python 3.10 或更高版本
-   [uv](https://github.com/astral-sh/uv): 一个极速的 Python 包安装器。如果尚未安装，可以通过 `pip install uv` 或 `pipx install uv` 进行安装。

### 2. 安装步骤

**a. 克隆项目仓库**
```bash
git clone <你的仓库地址>
cd langchain-context-article-writing
```

**b. 创建并激活虚拟环境 (推荐)**
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

**c. 配置国内镜像源 (强烈推荐)**
为了避免网络问题并极大提升下载速度，请先运行以下命令将 `uv` 的默认包索引设置为清华大学的镜像源：
```bash
uv config set index-url https://pypi.tuna.tsinghua.edu.cn/simple
```

**d. 安装项目依赖**
现在，你可以直接运行安装命令，`uv` 会自动使用刚才配置的镜像源。
```bash
uv pip install -e .[dev]
```

### 3. 配置环境

**a. 创建 `.env` 文件**
在项目的根目录下，手动创建一个名为 `.env` 的文件。

**b. 填入你的 API 密钥**
将以下内容复制到 `.env` 文件中，并替换成你自己的密钥：
```env
# .env 文件
# OpenAI API 密钥 (必需)
OPENAI_API_KEY="sk-..."

# 如果你使用代理或兼容 OpenAI 的其他 API 服务，请配置此项
# OPENAI_API_BASE="https://your.api.base/v1"

# 即梦图像生成服务的密钥 (可选)
JIMENG_AK="your_jimeng_access_key"
JIMENG_SK="your_jimeng_secret_key"
```

### 4. 启动应用

完成以上步骤后，运行以下命令启动 FastAPI 服务。
我们使用 `python main` 来运行
```bash
uv run python main.py
```
服务启动后，你可以：
-   在浏览器中访问 `http://1227.0.0.1:8000` 查看 API 根路径。
-   在浏览器中访问 `http://127.0.0.1:8000/docs` 查看并交互式地测试 API 文档。

### 5. 运行测试

如果你想验证项目的功能是否正常，可以运行测试套件。
```bash
uv run pytest
```

## 📂 项目结构

```
.
├── .env              # 环境变量文件 (需自行创建)
├── pyproject.toml      # 项目配置文件和依赖
├── README.md         # 项目说明
├── src
│   ├── api             # FastAPI 应用、路由和中间件
│   ├── infrastructure  # 日志、追踪等基础设施
│   ├── langchain_components # LangChain 核心组件 (Agent图、工具)
│   ├── plugins         # 外部服务插件 (图像生成、翻译)
│   ├── config.py       # 应用配置
│   └── main.py         # 应用启动入口
└── tests
    └── integration     # 集成测试