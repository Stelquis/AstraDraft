# DeepAstraDraft — CAD 图纸智能问答 Agent 生产级升级方案

> 基于 [Deep Agents 实战](https://github.com/datawhalechina/deepagents-in-action) 课程的生产级 Agent 架构，
> 将 AstraDraft 从比赛 Demo 升级为 Deep Agent 架构的工业级 CAD 问答系统。

---

## 目录

1. [现状分析](#1-现状分析)
2. [升级愿景](#2-升级愿景)
3. [环境依赖变更](#3-环境依赖变更)
4. [Phase 1：基础设施升级 — LLM + 虚拟文件系统](#4-phase-1基础设施升级--llm--虚拟文件系统)
5. [Phase 2：核心能力升级 — Skills + Memory + Middleware](#5-phase-2核心能力升级--skills--memory--middleware)
6. [Phase 3：架构重构 — 子 Agent 与中间件](#6-phase-3架构重构--子-agent-与中间件)
7. [需求分析：为什么需要前后端 + 数据库](#需求分析为什么需要前后端--数据库)
8. [Phase 4：v1.0 公用版 — 数据库与 API 增强](#8-phase-4v10-公用版--数据库与-api-增强)
9. [Phase 5：v1.0 公用版 — Web 前端界面](#9-phase-5v10-公用版--web-前端界面)
10. [附录 A：文件变更清单](#10-附录-a文件变更清单)
11. [附录 B：v2.0 企业版架构展望](#11-附录-bv20-企业版架构展望)

---

## 1. 现状分析

### 1.1 当前架构

```
main.py → agent/cli.py → Agent.load_cad() → Agent.ask()
                              │                    │
                    ┌─────────┴────────┐    ┌─────┴──────┐
                    │ cad_parser       │    │ nlp_interface│
                    │   ↕              │    │   ├─ intent  │
                    │ cad_understanding│    │   ├─ parser  │
                    │   ↕              │    │   ├─ mapper  │
                    │ ParameterIndex   │    │   └─ format  │
                    └─────────────────┘    └─────┬────────┘
                                                 │ 未命中
                                            httpx → DeepSeek LLM
```

### 1.2 关键文件及职责

| 文件 | 行数 | 职责 |
|------|------|------|
| `agent/core.py` | ~200 | Agent 总控：加载图纸 → 构建索引 → 规则查询 → LLM 回退 |
| `agent/config.py` | ~30 | Pydantic Settings 配置（ASTRADRAFT_ 环境变量前缀） |
| `agent/session.py` | ~28 | 会话管理：dataclass 内存列表，重启丢失 |
| `agent/cli.py` | ~74 | CLI 入口：argparse → REPL 循环 |
| `agent/exceptions.py` | ~14 | 分级异常：AstraDraftError → CADParseError/QueryError |
| `cad_parser/` | 7 文件 | DWG→DXF 转换 + ezdxf 解析（14 种实体 + 7 种标注 + 文本） |
| `cad_understanding/parameter_index.py` | ~763 | 核心：构建 102+ 参数索引（4 阶段提取 + 标题栏 + 签字栏 + BOM） |
| `cad_understanding/semantic_mapper.py` | ~110 | jieba 分词 + 同义词映射 + 评分匹配 |
| `nlp_interface/query_processor.py` | ~155 | 规则管道：极值→计数→数值搜索→多参→比较→单参→兜底 |
| `nlp_interface/intent_classifier.py` | ~61 | 正则意图分类（query_parameter / multi / compare / info） |
| `nlp_interface/parameter_parser.py` | ~79 | jieba 分词提取参数目标词 |
| `nlp_interface/response_formatter.py` | ~55 | 模板格式化（单参/多参/比较/无匹配） |
| `nlp_interface/prompt_templates.py` | ~35 | LLM 系统提示词 + 回答模板 |
| `tools/` | 4 文件 | 独立工具（DWG→DXF、索引构建、评估、考核答案生成） |

### 1.3 关键架构弱点

| 弱点 | 位置 | 影响 |
|------|------|------|
| **httpx 裸调 LLM** | `agent/core.py` | 无重试、无 token 统计、无追踪 |
| **全量参数注入 prompt** | `agent/core.py` | 大图纸时窗口溢出 |
| **硬编码查询管道** | `nlp_interface/query_processor.py` | 无法自适应组合查询 |
| **内存会话，重启丢失** | `agent/session.py` | 无历史持久化 |
| **单进程 CLI** | `agent/cli.py` | 无并发、无服务化 |
| **规则与 LLM 割裂** | `agent/core.py` | LLM 仅作兜底，无法协同 |

### 1.4 当前环境

| 组件 | 版本/来源 |
|------|----------|
| 基础镜像 | Ubuntu 24.04 LTS |
| Python | 3.12 |
| 包管理器 | UV (astral-sh) |
| Node.js | 22.x |
| LLM 模型 | DeepSeek v4 Flash（默认，Anthropic 兼容协议） |
| CAD 工具链 | ezdxf + LibreDWG(dwg2dxf) |
| NLP | jieba 0.42.1 |

---

## 2. 升级愿景

### 2.1 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│                     DeepAstraDraft Agent                     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ ParserAgent  │  │ IndexerAgent │  │ QueryAgent   │       │
│  │ (子Agent)    │  │ (子Agent)    │  │ (主Agent)    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                 │                │
│  ┌──────┴─────────────────┴─────────────────┴───────┐       │
│  │              中间件层 (Middleware)                │       │
│  │  TodoList │ Summarization │ Filesystem           │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────┐       │
│  │           Skills 能力包 (可插拔)                   │       │
│  │  cad-parser │ parameter-lookup │ title-block     │       │
│  │  bom-query  │ exam-eval                         │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────┐       │
│  │           虚拟文件系统 (Virtual Filesystem)        │       │
│  │  图纸索引 JSON │ 参数缓存 │ 评估结果 │ 问答历史   │       │
│  └──────────────────────┬───────────────────────────┘       │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────┐       │
│  │         长期记忆 (CompositeBackend)               │       │
│  │  StateBackend + StoreBackend                      │       │
│  └──────────────────────────────────────────────────┘       │
│                                                              │
│  外部服务: LangSmith(追踪) │ DeepSeek(LLM) │ FastAPI(HTTP)   │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 对标 Deep Agents 六大支柱

| 支柱 | 当前 | 目标 |
|------|:--:|:--:|
| 虚拟文件系统 | ❌ | ✅ 参数索引→JSON 文件，Agent 按需 ls/read/grep |
| 任务规划 | ❌ | ✅ TodoListMiddleware 自动拆解多步查询 |
| 子 Agent | ❌ | ✅ ParserAgent / IndexerAgent / QueryAgent / EvaluatorAgent |
| 异步子 Agent | ❌ | 🟡 批量评估场景 |
| Skills | ❌ | ✅ 5 个 CAD 领域 Skill 可插拔 |
| 长期记忆 | ❌ | ✅ Checkpointer + Store 持久化 |

---

## 3. 环境依赖变更

### 3.1 新增 Python 依赖

在 `requirements.txt` 中新增：

| 包名 | 用途 | Phase |
|------|------|:----:|
| `deepagents>=0.5.0` | Deep Agents 库（Agent Harness 层） | 1 |
| `langchain>=0.3.0` | LangChain（Agent Framework） | 1 |
| `langchain-deepseek>=0.1.0` | DeepSeek ChatModel（替代 httpx 裸调） | 1 |
| `langgraph>=0.2.0` | LangGraph（Agent Runtime） | 1 |
| `langgraph-checkpoint>=2.0.0` | Checkpointer 短期记忆持久化 | 1 |
| `fastapi>=0.115.0` | HTTP API 服务 | 4 |
| `uvicorn>=0.30.0` | ASGI 服务器 | 4 |
| `python-multipart>=0.0.6` | 文件上传支持 | 4 |

### 3.2 安装命令

```bash
uv pip install --python /opt/venv \
    deepagents langchain langchain-core langgraph \
    langchain-deepseek langgraph-checkpoint \
    fastapi uvicorn python-multipart
```

### 3.3 Dockerfile 更新要点

Dockerfile 第五部分依赖安装块需要追加上述依赖。Phase 5 前端需新增 Node 构建步骤。

---

## 4. Phase 1：基础设施升级 — LLM + 虚拟文件系统

> **目标**：不改变核心逻辑，把 LLM 调用和配置升级到 LangChain 标准，为后续 Deep Agent 铺路。
> **状态**：✅ 已实现

### Step 1.1：升级 LLM 集成

**改动文件**：`agent/core.py`

| 改前 | 改后 |
|------|------|
| `import httpx` + 裸调 Anthropic 协议 | `from langchain_deepseek import ChatDeepSeek` |
| 手动拼 JSON 请求体 | `self._llm.invoke(messages)` |
| 无重试、无追踪 | 自动重试 + LangSmith 可追踪 |

关键改动：
- `Agent` 新增 `_llm: Optional[ChatDeepSeek]` 属性
- 新增 `_init_llm()` 方法：从环境变量读取 key/url/model，创建 `ChatDeepSeek` 实例
- `_ask_llm()` 改为使用 `SystemMessage` / `HumanMessage` / `AIMessage` 标准接口
- 默认模型：`deepseek-v4-flash[1m]`

### Step 1.2：LangSmith 追踪

**改动文件**：`agent/core.py`

- 新增 `_init_langsmith()` 方法：检测 `LANGCHAIN_API_KEY` 环境变量，自动启用追踪
- 项目名：`deepastradraft`

### Step 1.3：虚拟文件系统

**当前问题**：参数索引全量拼入 prompt，大图纸可能超窗口。

**新增文件**：`deep_agent/filesystem_backend.py`

**类**：`CADIndexFilesystem` — 将 `ParameterIndexData` 导出为结构化文件：

| 导出文件 | 内容 |
|----------|------|
| `summary.md` | 索引摘要（总参数数、类型分布） |
| `parameters.json` | 完整参数数据（JSON） |
| `dimensions.txt` | 尺寸参数列表（按值降序） |
| `info_params.txt` | 信息参数列表（材质/标题栏/签字栏/BOM） |

**改动**：`agent/core.py` 的 `load_cad()` 中新增导出调用，输出到 `data/fs/{图纸名}/` 目录。

---

## 5. Phase 2：核心能力升级 — Skills + Memory + Middleware

> **目标**：引入 Deep Agents 核心能力——Skills 能力包、长期记忆、中间件体系。
> **状态**：✅ 已实现

### Step 2.1：Skills 能力包拆分

遵循 Agent Skills 规范（frontmatter + body），三阶段渐进式加载（名称→描述→正文）。

#### Skill 1：`skills/cad-parser/SKILL.md`

```markdown
---
name: cad-parser
description: >
  解析 DWG/DXF CAD 图纸文件，提取几何实体、尺寸标注、文本注释、
  图层信息，输出结构化的 CADDocument。
tools:
  - parse_cad_file
---

# CAD 图纸解析

## 能力
解析工业 CAD 图纸（DWG/DXF 格式），提取所有可查询的技术信息。

## 处理流程
1. DWG → LibreDWG(dwg2dxf) → DXF
2. DXF → ezdxf 解析为 CADDocument
3. 提取 14 种几何实体 + 7 种标注类型
4. 提取 TEXT/MTEXT 文本注释（GBK 编码）
5. 记录图层归属信息

## 注意事项
- DWG 依赖外部命令 dwg2dxf
- DXF 编码为 GBK
```

#### Skill 2：`skills/parameter-lookup/SKILL.md`

```markdown
---
name: parameter-lookup
description: >
  在已解析的 CAD 图纸参数索引中查询技术参数，支持模糊匹配、
  语义别名、同义词映射，返回参数名称、数值、单位和来源信息。
tools:
  - lookup_parameter
  - list_all_parameters
  - search_by_value
---

# 参数查询

## 查询方式
- 精确名称匹配 + 语义别名（"孔径"="网孔"="目"）
- jieba 分词模糊匹配（TF-IDF 权重）
- 数值范围搜索、极值查询、计数查询

## 参数类型
- 尺寸参数：长度、宽度、高度、直径、半径、角度、厚度
- 信息参数：材质、色调、成形方法、编织方式、防菌、退火
- 标题栏：图纸名称、图号、比例、版本号、标准
- 签字栏：设计、审核、工艺、标准化、批准、归档
- BOM 表：部品编号、材料、规格
```

#### Skill 3：`skills/title-block/SKILL.md`

```markdown
---
name: title-block
description: >
  从 CAD 图纸标题栏、签字栏提取元信息：图纸名称、图号、比例、
  设计者、审核者、日期等。
tools:
  - extract_title_block
  - extract_signoff
---

# 标题栏与签字栏提取

## 标题栏
图纸名称、图号、比例、分类、图幅、版本号、重要等级、标准、管理编号、材料

## 签字栏
设计、审核、工艺、标准化、批准、归档（含签名 + 日期）

## 提取策略
- 图层识别（HHLayerShuxinglan / HHLayerMingxilan）
- 空间位置聚类（x/y 坐标分组）
- 标签-值配对（同行右侧或下方）
```

#### Skill 4：`skills/bom-query/SKILL.md`

```markdown
---
name: bom-query
description: >
  查询 CAD 图纸 BOM（物料清单）表，提取部品名称、材料、
  规格、数量等生产信息。
tools:
  - query_bom
  - list_components
---

# BOM 表查询

## 提取内容
部品编号、名称、材料牌号（PS-B/PP/SPCC/SECC/SUS304）、规格（如 7T）

## 提取策略
- 图层：HHLayerMingxilan
- y 坐标行分组 + x 坐标列排序
```

#### Skill 5：`skills/exam-eval/SKILL.md`

```markdown
---
name: exam-eval
description: >
  批量评估 CAD 问答准确率，对比标准答案，生成评估报告。
tools:
  - evaluate_answers
  - generate_exam_answers
---

# 考核评估

## 输入
标准答案 CSV + CAD 图纸文件

## 输出
逐题正误表、总体准确率、分类统计（尺寸/信息/标题栏/签字栏）
```

### Step 2.2：Skills 注册与加载

**新增文件**：`deep_agent/skills_registry.py`

**类**：`SkillRegistry`
- `discover()` — Phase 1：扫描 `skills/` 目录，返回名称列表
- `load_metadata()` — Phase 2：解析 SKILL.md frontmatter（name/description/tools）
- `load_full()` — Phase 3：返回完整 Markdown 正文
- `build_system_prompt()` — 生成 Agent 系统提示词摘要

### Step 2.3：中间件体系

**新增文件**：`deep_agent/middleware.py`

| 中间件 | 类型 | 作用 |
|--------|------|------|
| `TodoListMiddleware` | 常驻 | 自动拆解多步查询（如"材质、尺寸和加工方法"→3 个 todo） |
| `FilesystemMiddleware` | 常驻 | 挂载虚拟文件系统，提供 ls/read_file/grep 工具 |
| `SummarizationMiddleware` | 常驻 | 超过 20K tokens 自动总结历史对话 |
| `collect_middleware()` | 工厂 | 收集所有可用中间件，过滤失败的 |

### Step 2.4：长期记忆

**新增文件**：`deep_agent/memory.py`

**类**：`AstraDraftMemory`

| 存储层 | 实现 | 内容 |
|--------|------|------|
| 短期 (Checkpointer) | `MemorySaver` | 对话历史持久化（后续可升 Postgres） |
| 长期 (Store) | JSON 文件 | 用户偏好、参数别名学习、查询历史、评估结果 |

---

## 6. Phase 3：架构重构 — 子 Agent 与中间件

> **目标**：将单体 Agent 拆分为协作式子 Agent，引入中间件体系。
> **状态**：✅ 已实现

### Step 6.1：子 Agent 拆分

**新增文件**：`deep_agent/sub_agents.py`

| 子 Agent | 角色 | 声明工具 |
|-----------|------|----------|
| `cad-parser` | DWG/DXF 图纸解析 | `parse_cad_file` |
| `cad-indexer` | 构建 102+ 参数索引 | `build_parameter_index`, `export_to_filesystem` |
| `cad-query` | **主 Agent**：智能问答 | `ls`, `read_file`, `grep`, `glob` |
| `cad-evaluator` | 批量评估准确率 | `evaluate_batch`, `generate_report` |

每个子 Agent 遵循字典定义规范（3 个必填字段：`name`, `description`, `system_prompt`）。

### Step 6.2：主 Agent 组装

**新增文件**：`deep_agent/agent.py`

**类**：`DeepAstraDraft` — 组装所有子系统的生产级 Agent。

**核心流程**：
1. `load_cad(file_path)` → 复用现有 Pipeline 解析图纸 → 导出虚拟文件系统 → `create_deep_agent()`
2. `ask(question)` → 优先 Deep Agent 查询 → LLM 不可用时回退到规则引擎
3. 内置 3 个自定义工具：`lookup_parameter` / `list_all_parameters` / `search_by_value`

**关键决策**：
- Deep Agent 创建失败（如无 LLM）→ 自动降级为 `nlp_interface.QueryProcessor` 规则引擎
- 每次查询记录到 `AstraDraftMemory`，源标记（rule/deep_agent）

### Step 6.3：CLI 入口升级

**改动文件**：`agent/cli.py`

新增 `--engine` 参数：

| 值 | 行为 |
|:--|------|
| `rule` | 纯规则匹配（默认，无需 LLM） |
| `llm` | 规则 + DeepSeek 兜底（旧 Agent） |
| `deep` | DeepAgent 架构（新，需 LLM key） |

---

## 需求分析：为什么需要前后端 + 数据库

在进入 v1.0 详细设计之前，回答一个核心问题：**当前 CLI 工具已经能用（93% 准确率），为什么还要加前后端和数据库？**

### 企业级 AI Agent 标准要求对标

| 维度 | 行业基准 | 当前状态 |
|------|----------|:--:|
| **多用户** | 多人同时上传图纸、查询 | 单例 Agent，全局变量 |
| **持久化** | 图纸索引结果复用，查询历史不丢 | 文件存 JSON，无事务保障 |
| **可观测** | 谁查了什么、准确率、LLM token 用量 | logging 模块，无聚合面板 |
| **权限控制** | 图纸有密级，不同人看不同参数 | v2.0 做 |
| **审计追溯** | 谁何时查了什么参数，合规检查 | 无 |
| **水平扩展** | 并发 100 人同时查图纸 | 单进程 |
| **图纸管理** | 几百张图纸、版本迭代、检索 | 靠文件系统 |

### 什么时候需要前端？

| 使用方式 | 适用场景 |
|----------|----------|
| CLI 命令行 | 个人辅助工具（你自己用） |
| FastAPI + SQLite | 小团队内部用（<10 人，几张图） |
| FastAPI + SQLite + Web 前端 | **v1.0 公用版目标**（部门级，无需登录） |
| 完整架构 | v2.0 企业版（跨部门，权限分级） |

产线上的工艺工程师不可能开终端敲命令行。他们需要的是：拖拽上传 DWG 文件、搜索框 + 聊天界面、对话历史查看。前端不是锦上添花，是可用性的基本门槛。

### 什么时候需要数据库？

当前靠 JSON 文件存索引和记忆，几张图还行，但当图纸数量超过 20 张时：
- 100 张图 × 123 参数 × 多版本 → 文件系统难以管理
- 并发读写同一个 JSON → 数据损坏风险
- 跨会话恢复依赖文件名匹配 → 脆弱

SQLite 在 v1.0 阶段即可提供：结构化查询（`SELECT * FROM params WHERE name LIKE '%孔径%'`）、事务保障、并发安全、零配置部署。

### v1.0 的设计边界

| 做 | 不做 |
|----|------|
| 多人上传图纸、各自查询 | 用户登录 / 注册 |
| 图纸列表 + 状态管理 | 权限分级（谁只能看谁的图） |
| 查询历史按图纸回溯 | 多租户数据隔离 |
| SQLite 单文件数据库 | PostgreSQL / Redis 集群 |
| 单进程 FastAPI 服务 | K8s 水平扩展 |

---

## 7. Phase 4：v1.0 公用版 — 数据库与 API 增强

> **目标**：可多人公用的 Web 服务。无需登录，任何人上传图纸即可对话。
>
> **状态**：🔄 API 框架已有，SQLite 层 + 多图纸管理待实现

### 数据库选型：为什么 v1.0 用 SQLite

| 方案 | 优势 | 劣势 | 适用 |
|------|------|------|:--:|
| JSON 文件 | 零依赖 | 并发写不安全、无查询能力 | 单图原型 |
| **SQLite** | 零部署、事务安全、SQL 查询、WAL 并发 | 不适合超大规模 | **v1.0** |
| PostgreSQL | 集群、JSONB 索引、ACID | 需要独立部署 | v2.0 |

v1.0 选 SQLite 的核心理由：和当前 JSON 文件一样零运维，但多了事务安全和结构化查询。

### 7.1 v1.0 架构总览

```
┌──────────────────────────────────────────────────────────────┐
│                    v1.0 公用 CAD Agent                        │
│                                                               │
│  浏览器 ──→ 前端 SPA (Vue 3) ──→ FastAPI ──→ DeepAstraDraft  │
│              │                    │              │            │
│              │ 上传/对话          │ REST API     │ 查询引擎   │
│              │                    │              │            │
│              └────────────────────┴──────┬───────┘            │
│                                          │                    │
│                                   ┌──────┴──────┐             │
│                                   │   SQLite    │             │
│                                   │ ┌─────────┐ │             │
│                                   │ │ 图纸索引 │ │             │
│                                   │ │ 查询历史 │ │             │
│                                   │ │ 上传记录 │ │             │
│                                   │ └─────────┘ │             │
│                                   └─────────────┘             │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 SQLite 数据库设计

**新增文件**：`deep_agent/database.py`

两张核心表：

**`drawings` 表** — 上传图纸的元数据与参数索引：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | TEXT PK | 12 位 hex ID |
| `filename` | TEXT | 原始文件名 |
| `file_path` | TEXT | 存储路径 |
| `status` | TEXT | pending → parsing → ready → error |
| `param_count` | INTEGER | 参数总数 |
| `index_json` | TEXT | 完整参数索引 JSON（从 ParameterIndexData 序列化） |

**`query_history` 表** — 所有用户的查询记录（公开可查）：

| 列 | 类型 | 说明 |
|----|------|------|
| `id` | INTEGER PK | 自增 |
| `drawing_id` | TEXT FK | 关联图纸 |
| `question` / `answer` | TEXT | 问答对 |
| `source` | TEXT | rule / llm / deep_agent |
| `session_id` | TEXT | 浏览器会话标识 |

操作函数：`add_drawing()`, `update_drawing_status()`, `get_drawing()`, `list_drawings()`, `add_query()`, `get_query_history()`, `count_queries()`

### 7.3 增强版 API

**改动文件**：`deep_agent/api.py`

核心改动：从全局单例 Agent → 按 `drawing_id` 管理多张图纸。

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/upload` | 上传 DWG/DXF → 自动解析 → 返回 drawing_id |
| `GET` | `/drawings` | 列出所有已解析图纸（名称、参数数、时间） |
| `GET` | `/drawings/{id}` | 图纸详情 |
| `POST` | `/drawings/{id}/query` | 对指定图纸提问（含 session_id 关联） |
| `GET` | `/drawings/{id}/history` | 查看该图纸的对话历史 |
| `GET` | `/health` | 健康检查（含缓存 Agent 数量） |

Agent 实例缓存策略：字典 `_agents: Dict[str, DeepAstraDraft]` + 可选 LRU（≥20 个时淘汰）。

---

## 8. Phase 5：v1.0 公用版 — Web 前端界面

> **目标**：无需命令行的 Web 界面，上传图纸即可对话。
>
> **状态**：🆕 待实现

### 8.1 技术选型

| 方案 | 优势 | 适用 |
|------|------|:--:|
| 纯 HTML + 原生 JS | 零依赖，极轻量 | 快速原型 |
| React + Ant Design | 企业级组件库，表格/表单/上传开箱即用 | 大型项目 |
| **Vue 3 + TDesign** | 腾讯出品，与国内企业习惯契合，Node.js 22 现成 | **v1.0** |

选择 Vue 3 + TDesign 的原因：
- Dockerfile 已有 Node.js 22 环境，零额外系统依赖
- TDesign 的 Upload / List / Input / Tag 组件覆盖全部需求
- Vue 3 Composition API 对单页小应用非常轻量
- 构建产物为纯静态文件，由 FastAPI 直接托管

### 8.2 页面设计

单页应用，左右分栏：

```
┌─────────────────────────────────────────────────────┐
│  DeepAstraDraft  v1.0                               │
├──────────┬──────────────────────────────────────────┤
│          │                                          │
│  图纸列表 │      📄 过滤网图纸 (123 参数)            │
│          │      ────────────────────────────        │
│ ┌──────┐ │                                          │
│ │过滤网 ││   🤖  请输入技术参数问题...               │
│ │123参 ││   ───────────────────────────            │
│ │  ✓   ││                                          │
│ ├──────┤│   ▸ 总长度 = 527.0 mm                    │
│ │侧板  ││   ▸ 材质为 PS 注塑成型品                  │
│ │ 89参 ││   ▸ 图号为 HX-001                        │
│ ├──────┤│                                          │
│ │+上传 ││   ▾ 历史记录                              │
│ └──────┘│     Q: 宽度 → 517.0 mm                   │
│          │     Q: 材质 → PS 注塑成型品              │
└──────────┴──────────────────────────────────────────┘
```

### 8.3 核心组件

**文件**：`frontend/src/views/Home.vue`

- **左侧面板**：图纸列表 + TDesign Upload 上传按钮
- **右侧面板**：选中图纸后显示对话区 + 消息列表 + 输入框
- **空状态**：未选图纸时提示"请上传一张 CAD 图纸开始对话"
- **session_id**：用 `localStorage` 保存浏览器标识，关联查询历史

### 8.4 项目初始化

```bash
cd /workspace
npm create tdesign@latest frontend -- --framework vue3 --template spa
cd frontend
npm install axios
npm run dev     # 开发服务器 :5173
npm run build   # 构建 → frontend/dist/
```

### 8.5 Dockerfile 集成

```dockerfile
COPY frontend/ /workspace/frontend/
RUN cd /workspace/frontend && npm install && npm run build && rm -rf node_modules
```

构建后 `frontend/dist/` 由 FastAPI `StaticFiles` 挂载，一个端口同时服务前后端。

---

## 9. 附录 A：文件变更清单

### 新增文件

```
deep_agent/
├── __init__.py              ✅ 包入口
├── agent.py                 ✅ DeepAstraDraft 主 Agent
├── filesystem_backend.py    ✅ 虚拟文件系统
├── middleware.py            ✅ 中间件定义
├── memory.py                ✅ 长期记忆
├── skills_registry.py       ✅ Skills 注册表
├── sub_agents.py            ✅ 4 个子 Agent 定义
├── api.py                   🔁 FastAPI 服务（待增强为 v1.0）
├── database.py              🆕 SQLite 数据库层
└── async_eval.py            🆕 异步批量评估

skills/
├── cad-parser/SKILL.md      ✅
├── parameter-lookup/SKILL.md ✅
├── title-block/SKILL.md     ✅
├── bom-query/SKILL.md       ✅
└── exam-eval/SKILL.md       ✅

frontend/                     🆕
├── package.json
├── vite.config.ts
└── src/views/Home.vue

scripts/start-api.sh          ✅
```

### 修改文件

| 文件 | 改什么 | 状态 |
|------|--------|:--:|
| `agent/core.py` | LLM httpx→ChatDeepSeek + LangSmith + 虚拟文件系统导出 | ✅ |
| `agent/config.py` | 模型默认值 `deepseek-v4-flash[1m]` | ✅ |
| `agent/cli.py` | 新增 `--engine`（rule/llm/deep）选项 | ✅ |
| `agent/session.py` | 集成 Memory 持久化方法 | ✅ |
| `requirements.txt` | 新增 10 个依赖 | ✅ |
| `deep_agent/api.py` | v1.0 增强（多图纸 + SQLite 集成） | 🔄 |
| `Dockerfile` | 新增前端构建 + API 入口 | 🔄 |

### 保留不变

`cad_parser/` `cad_understanding/` `nlp_interface/` `tools/` `main.py` `data/` `examples/`

---

## 10. 附录 B：v2.0 企业版架构展望

> v1.0 = 公用单机版（无登录，SQLite，单进程）
> v2.0 = 企业生产版（多租户，权限，高可用）

### 目标架构

```
┌──────────────────────────────────────────────────────────────┐
│                    v2.0 企业版 CAD Agent                       │
│                                                               │
│  ┌─────────────────┐  ┌───────────┐  ┌───────────────────┐  │
│  │  React / Vue 3  │  │  钉钉/企微 │  │  管理后台 (Admin)  │  │
│  │  Web 端         │  │  小程序    │  │  用户/权限/审计    │  │
│  └────────┬────────┘  └─────┬─────┘  └────────┬──────────┘  │
│           │                 │                  │              │
│  ┌────────┴─────────────────┴──────────────────┴──────────┐  │
│  │                API Gateway (Kong/Nginx)                 │  │
│  │              统一鉴权 + 限流 + 路由                      │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │                                  │
│  ┌──────────────────────────┴──────────────────────────────┐  │
│  │              FastAPI 服务集群 (×N 实例)                   │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐ │  │
│  │  │ Auth 模块 │ │Celery队列│ │WebSocket │ │CAD Engine  │ │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────┘ │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │                                  │
│  ┌──────────────────────────┴──────────────────────────────┐  │
│  │                    数据层                                  │  │
│  │  ┌────────────┐ ┌──────────┐ ┌──────────────────────┐   │  │
│  │  │ PostgreSQL │ │  Redis   │ │ MinIO/OSS 对象存储    │   │  │
│  │  │ 图纸索引   │ │ 会话缓存 │ │ DWG/DXF 文件 + 版本   │   │  │
│  │  │ 用户/权限  │ │ 任务队列 │ │ 缩略图/预览           │   │  │
│  │  │ 审计日志   │ │ 限流计数 │ │                      │   │  │
│  │  └────────────┘ └──────────┘ └──────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### v2.0 vs v1.0 差异

| 维度 | v1.0 公用版 | v2.0 企业版 |
|------|:-----------:|:-----------:|
| 数据库 | SQLite（单文件） | PostgreSQL（集群 + 读写分离） |
| 缓存 | 内存 dict | Redis 集群 |
| 文件存储 | 本地磁盘 | 对象存储（MinIO/OSS） |
| 用户体系 | **无**（公用人人可用） | JWT/OAuth2 + RBAC 权限 |
| 任务队列 | 同步 | Celery + Redis（异步解析大图纸） |
| 前端 | Vue 3 单页 | Web + 管理后台 + 移动端 |
| 部署 | 单容器 `uvicorn` | Docker Compose / K8s |
| 可观测 | logging | LangSmith + Prometheus + Grafana |
| 审计 | 查询历史表 | 完整审计链路（谁何时查了什么） |
| 图纸版本 | 覆盖式上传 | Git-like 版本管理 + diff |
| 批量评估 | 简单脚本 | 异步并发 + 报告导出 |

### v2.0 新增数据库表

```sql
-- 用户表
CREATE TABLE users (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) UNIQUE NOT NULL,
    role     VARCHAR(16) DEFAULT 'viewer'  -- admin / editor / viewer
);

-- 图纸权限表
CREATE TABLE drawing_permissions (
    drawing_id UUID REFERENCES drawings(id),
    user_id    UUID REFERENCES users(id),
    permission VARCHAR(16) DEFAULT 'read',  -- read / write / admin
    PRIMARY KEY (drawing_id, user_id)
);

-- 审计日志表
CREATE TABLE audit_log (
    id         BIGSERIAL PRIMARY KEY,
    user_id    UUID REFERENCES users(id),
    drawing_id UUID REFERENCES drawings(id),
    action     VARCHAR(32),   -- upload / query / download / delete
    detail     JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);
```

### v2.0 部署拓扑

核心服务：API（×3 副本）+ Worker（Celery ×4 并发）+ PostgreSQL + Redis + MinIO + 前端 Nginx。

---

> **文档版本**: v2.0  
> **创建日期**: 2026-06-30  
> **最后更新**: 2026-06-30  
> **基于**: AstraDraft 当前代码 + Deep Agents 实战课程 (10 章)  
> **状态**: Phase 1–3 ✅ 已实现 · Phase 4–5 🔄 设计中 · 附录 B v2.0 📋 规划中
