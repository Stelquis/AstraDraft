<p align="center">
  <h1 align="center">🤖 DeepAstraDraft</h1>
  <p align="center">
    <b>生产级 CAD 图纸智能问答 Agent</b><br>
    上传 DWG/DXF → 自动解析 → 自然语言对话 → 精准回答
  </p>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/release/python-3120/"><img src="https://img.shields.io/badge/python-3.12-blue.svg" alt="Python 3.12"></a>
  <a href="https://github.com/astral-sh/uv"><img src="https://img.shields.io/badge/uv-package--manager-blueviolet.svg" alt="UV"></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-v1.0-009688.svg" alt="FastAPI"></a>
  <a href="https://vuejs.org/"><img src="https://img.shields.io/badge/Vue-3.4-42b883.svg" alt="Vue 3"></a>
  <a href="https://sqlite.org/"><img src="https://img.shields.io/badge/SQLite-v3-003b57.svg" alt="SQLite"></a>
  <a href="https://www.langchain.com/"><img src="https://img.shields.io/badge/LangChain-0.3-1c3c3c.svg" alt="LangChain"></a>
  <a href="https://langchain-ai.github.io/langgraph/"><img src="https://img.shields.io/badge/LangGraph-0.2-ff6b35.svg" alt="LangGraph"></a>
</p>

<p align="center">
  <a href="#-架构"><b>架构</b></a> ·
  <a href="#-快速开始"><b>快速开始</b></a> ·
  <a href="#-api-端点"><b>API</b></a> ·
  <a href="#-项目结构"><b>结构</b></a> ·
  <a href="#-配置"><b>配置</b></a> ·
  <a href="#-docker"><b>Docker</b></a>
</p>

---

## 📖 简介

DeepAstraDraft 是一个面向工业 CAD 图纸的智能问答 Agent。解析 DWG/DXF 图纸，构建 123 项参数语义索引，通过自然语言回答技术参数问题。支持 **三种使用形态**：

| 形态 | 方式 | 适用场景 |
|------|------|----------|
| ⌨️ **CLI** | `python main.py --file xxx.dwg` | 开发者 / 调试 |
| 🌐 **API** | `uvicorn backend.api:app` | 系统集成 |
| 🖥️ **Web** | `cd frontend && npm run dev` | 终端用户（无需登录） |

---

## 🛠️ 技术栈

| 层 | 技术 | 用途 |
|----|------|------|
| **CAD 解析** | ezdxf + LibreDWG | DWG→DXF 转换，14 种实体提取 |
| **NLP** | jieba | 中文分词、TF-IDF 关键词匹配 |
| **Agent 框架** | LangChain + LangGraph + DeepAgents | 任务规划、子Agent协作、Skills管理 |
| **后端** | FastAPI + SQLite + Pydantic | REST API、多图纸管理、持久化 |
| **前端** | Vue 3 + TDesign + Vite | 上传 + 聊天界面 |
| **LLM** | DeepSeek v4 Flash | Anthropic 兼容协议，无 Key 自动降级 |
| **可观测** | LangSmith (可选) | 全链路追踪 |
| **包管理** | UV | 10-100x 比 pip 快 |

---

## 🏗️ 架构

```
┌─────────────────────────────────────────────────────────┐
│                    DeepAstraDraft v1.0                    │
│                                                          │
│  frontend/ (Vue 3) ──→ backend/ (FastAPI + SQLite)       │
│                            │                             │
│                     ┌──────┴──────┐                      │
│                     │  agent/     │  Deep Agent 核心      │
│                     │  子Agent协作 │  中间件 · Skills      │
│                     └──────┬──────┘                      │
│                            │                             │
│              ┌─────────────┴─────────────┐               │
│              │         cad/              │  CAD 领域包    │
│              │  parser → understanding   │               │
│              │        → nlp              │               │
│              └───────────────────────────┘               │
└──────────────────────────────────────────────────────────┘
```

**数据流**：`DWG/DXF` → `cad/parser` → `cad/understanding`（123 参数索引）→ 用户提问 → `cad/nlp`（规则管道）→ `agent/`（LLM 增强）→ 回答

---

## 📊 技术指标

| 指标 | 数值 |
|------|------|
| 解析几何实体 | 3,206（14 种类型） |
| 尺寸标注 | 78（7 种类型） |
| 参数索引 | 123 |
| 领域 Skill | 5 个 |
| 子 Agent | 4 个（Parser/Indexer/Query/Evaluator） |
| 训练准确率 | **93.1%**（58 题） |
| LLM 模型 | DeepSeek v4 Flash |

---

## 💬 交互示例

```
> 总长度是多少？
📏 总长度(527.0mm) = 527.0 mm

> 最大的圆角半径是多少？
🏆 最大的圆角半径是 5.0 mm

> 5mm 的尺寸有几处？
🔢 尺寸 5mm 在图纸中共出现 4 处

> 材质是什么？
🧱 材质为 PS 注塑成型品

> 图号是什么？
📋 图号: HX-001
```

---

## 🚀 快速开始

### 环境要求

- Python 3.12+ · Node.js 22+ · LibreDWG (`dwg2dxf`)
- LLM API Key 可选（不配时自动降级为纯规则模式，准确率 93.1%）

### 安装

```bash
# Python 依赖
pip install -r requirements.txt

# 前端构建
cd frontend && npm install && npm run build && cd ..
```

### 启动

```bash
# 方式一：CLI
python main.py --file data/cad/filter_modify.dwg

# 方式二：API
./scripts/start-api.sh               # → http://localhost:8000/docs

# 方式三：Web
cd frontend && npm run dev            # → http://localhost:5173
```

---

## 🌐 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/upload` | 上传 DWG/DXF，自动解析并入库 |
| `GET` | `/drawings` | 已解析图纸列表 |
| `GET` | `/drawings/{id}` | 图纸详情（参数数、状态） |
| `POST` | `/drawings/{id}/query` | 对图纸提问 |
| `GET` | `/drawings/{id}/history` | 问答历史 |
| `GET` | `/health` | 健康检查 |
| `GET` | `/skills` | 可用 Skill 列表 |

```bash
# 上传
curl -X POST http://localhost:8000/upload -F "file=@filter_modify.dwg"
# → {"drawing_id": "abc", "status": "ready", "param_count": 123}

# 查询
curl -X POST http://localhost:8000/drawings/abc/query \
  -H "Content-Type: application/json" \
  -d '{"question": "总长度是多少"}'
```

---

## 📂 项目结构

```
DeepAstraDraft/
├── agent/                    # 🧠 Agent 核心
│   ├── core.py               #    DeepAstraDraft 主 Agent
│   ├── filesystem.py         #    虚拟文件系统
│   ├── memory.py             #    长期记忆
│   ├── skills.py             #    Skills 注册表
│   ├── sub_agents.py         #    4 个子 Agent
│   ├── session.py            #    会话管理
│   └── cli.py                #    CLI 入口
├── backend/                  # ⚙️ 后端服务
│   ├── api.py                #    FastAPI (7 端点)
│   ├── config.py             #    配置
│   ├── database.py           #    SQLite 层
│   └── middleware.py         #    中间件
├── cad/                      # 📐 CAD 领域包
│   ├── parser/               #    DWG/DXF 解析 (ezdxf + LibreDWG)
│   ├── understanding/        #    参数索引 + 语义匹配
│   └── nlp/                  #    意图分类 + 规则管道
├── frontend/                 # 🎨 Vue 3 + TDesign
│   └── src/views/Home.vue    #    上传 + 对话界面
├── skills/                   # 📋 5 个 CAD 领域 Skill
├── scripts/                  # 🔧 工具 & 启动脚本
├── main.py                   # 🚪 入口
├── requirements.txt          # 📦 Python 依赖
├── Dockerfile                # 🐳 容器构建
└── DeepAstraDraft.md         # 📄 升级方案文档
```

---

## ⚙️ 配置

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `ANTHROPIC_AUTH_TOKEN` | — | DeepSeek API Key（不配则纯规则模式） |
| `ANTHROPIC_BASE_URL` | `https://api.deepseek.com/anthropic` | API 地址 |
| `ANTHROPIC_MODEL` | `deepseek-v4-flash[1m]` | 模型名称 |
| `LANGCHAIN_API_KEY` | — | LangSmith 追踪（可选） |
| `PORT` | `8000` | API 服务端口 |

---

## 🐳 Docker

```bash
docker build -t deepastradraft .
docker run -p 8000:8000 deepastradraft ./scripts/start-api.sh
```

---

## 📄 许可证

[MIT License](LICENSE)

---

<p align="center">
  <sub>v1.0 · 基于 <a href="https://github.com/datawhalechina/deepagents-in-action">Deep Agents 实战</a> 课程</sub>
</p>
