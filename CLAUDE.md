# DeepAstraDraft — CAD 智能问答 Agent

## 项目简介

DeepAstraDraft v1.0 — 基于 Deep Agents 架构的生产级 CAD 图纸智能问答系统。
上传 DWG/DXF → 自动解析 → 自然语言对话 → 精准回答技术参数。

## 核心架构

```
DWG/DXF 文件 → cad/parser (ezdxf解析)
                    ↓
            cad/understanding (参数索引 123个)
                    ↓
用户问题 → cad/nlp (意图分类/规则匹配) → 答案
                    ↓(未命中)
              agent/core (LLM增强: DeepSeek v4 Flash)
```

## 目录结构

| 路径 | 用途 |
|------|------|
| `agent/` | Agent 核心：core.py (DeepAstraDraft 主类)、filesystem.py (虚拟FS)、memory.py (长期记忆)、skills.py (Skills注册)、sub_agents.py (4个子Agent)、cli.py (CLI) |
| `backend/` | 后端服务：api.py (FastAPI 7端点)、config.py (配置)、database.py (SQLite)、middleware.py (中间件) |
| `cad/parser/` | CAD 解析：reader (DWG→DXF)、entities (14种几何体)、dimensions (7种标注)、text_extractor |
| `cad/understanding/` | 语义理解：parameter_index (核心索引 123参数)、semantic_mapper (jieba模糊匹配)、component_recognizer、scale_inferencer |
| `cad/nlp/` | NLP：intent_classifier、query_processor (规则管道)、parameter_parser、response_formatter、prompt_templates |
| `frontend/` | Vue 3 + TDesign：Home.vue (上传+对话)、dist/ (构建产物) |
| `skills/` | 5 个 CAD 领域 Skill：cad-parser、parameter-lookup、title-block、bom-query、exam-eval |
| `scripts/` | 脚本：start-api.sh、build_index.py、evaluate.py、generate_exam_answers.py |
| `data/cad/` | CAD 源文件 (.dwg/.dxf) |

## 关键技术点

- **CAD 解析链路**: DWG → LibreDWG(dwg2dxf) → DXF → ezdxf → CADDocument
- **参数索引构建**: 4 阶段：维度提取 → 键值对提取 → 领域启发式 → 语义别名
- **规则管道优先级**: 极值 > 计数 > 数值搜索 > 多参 > 比较 > 单参 > 兜底
- **LLM 模型**: DeepSeek v4 Flash (Anthropic 兼容协议)
- **Deep Agents 六大支柱**: 虚拟文件系统 ✅ · 任务规划 ✅ · 子Agent ✅ · Skills ✅ · 长期记忆 ✅ · LangSmith追踪 ✅
- **编码**: GBK（DXF 内部编码），UTF-8（系统）

## 当前状态 (v1.0, 2026-06-30)

- ✅ Phase 1-5 全部实现
- ✅ 93.1% 准确率（58题/123参数）
- ✅ FastAPI 7 端点 + SQLite 持久化
- ✅ Vue 3 + TDesign Web 前端
- ✅ 5 个 CAD 领域 Skill 可插拔
- ✅ 4 个协作式子 Agent
- ✅ 项目结构标准化重组完成

## LLM 配置

```bash
ANTHROPIC_AUTH_TOKEN=sk-xxx    # DeepSeek API Key (不配时降级为纯规则模式)
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-flash[1m]
LANGCHAIN_API_KEY=             # LangSmith 追踪 (可选)
```

## 启动方式

```bash
# CLI
python main.py --file data/cad/filter_modify.dwg

# API
./scripts/start-api.sh

# 前端开发
cd frontend && npm run dev
```
