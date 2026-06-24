# AstraDraft — CAD 智能问答 Agent

## 项目简介

海信 × 阿里云 AI 智能体大赛参赛项目。解析 DXF/DWG 工业 CAD 图纸，构建语义参数索引，用自然语言回答技术参数问题。

## 核心架构

```
输入(DWG/DXF) → cad_parser → 几何实体+标注+文本
                          ↓
                  cad_understanding → 参数索引(102+参数)
                          ↓
用户问题 → nlp_interface → 规则匹配(优先) → 答案
                              ↓(未命中)
                          LLM回退(DeepSeek)
```

## 目录结构

| 路径 | 用途 |
|------|------|
| `agent/` | Agent 调度层：core.py（主循环）、cli.py（CLI入口）、config.py（配置） |
| `cad_parser/` | CAD 解析：reader（DWG→DXF）、entities（14种几何体）、dimensions（7种标注）、text_extractor（TEXT/MTEXT） |
| `cad_understanding/` | 语义理解：parameter_index（核心索引）、semantic_mapper（jieba模糊匹配） |
| `nlp_interface/` | NLP：intent_classifier、query_processor（规则管道）、prompt_templates |
| `tools/` | 工具：generate_exam_answers.py（考核答案生成）、evaluate.py（评估）|
| `data/cad/` | CAD 源文件（.dwg / .dxf） |
| `data/exam_temp/` | 考核答案输出（submission.csv） |
| `files/` | 文档：Design.md（架构设计）、STATUS.md（状态追踪）、竞赛指南.md |
| `examples/` | 训练问答集（58题） |

## 关键技术点

- **CAD 解析链路**: DWG → LibreDWG(dwg2dxf) → DXF → ezdxf → CADDocument
- **参数索引构建**: 4 阶段：维度提取 → 键值对提取 → 领域启发式 → 语义别名
- **规则管道优先级**: 极值 > 计数 > 数值搜索 > 多参 > 比较 > 单参 > 兜底
- **LLM 回退**: DeepSeek v4 Pro（Anthropic 兼容协议），注入全量文字上下文
- **编码**: GBK（DXF 内部编码），UTF-8（系统）

## 当前状态（2026-06-24）

- ✅ 原训练集 93.1% 准确率（58题/102参数）
- ✅ 考核答案已生成（侧板 20题 + 印刷版 21题，共41题）
- ✅ 答案输出：`data/exam_temp/submission.csv`
- ✅ 所有改动已 commit & push
- ⬜ 待提交技术方案报告（≤10页PDF）
- ⬜ 考核答案上传窗口：**6/25 00:00 ~ 6/26 23:59**

## LLM 配置

```bash
# 环境变量（已配置在容器中）
ANTHROPIC_AUTH_TOKEN=sk-xxx    # DeepSeek API Key
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
ANTHROPIC_MODEL=deepseek-v4-pro[1m]
```

## 考核答案生成

```bash
python3 tools/generate_exam_answers.py
```

输出：`submission.csv`（答案）、`answers.json`（完整JSON）

## 近期关键改动

1. `parameter_index.py` — 新增标题栏提取、签字栏提取、技术要求提取、BOM表提取
2. `agent/core.py` — 增强 LLM 回退，扩展复杂问题检测，注入全量文字上下文
3. `nlp_interface/prompt_templates.py` — 升级系统提示词覆盖考核题型
4. `Dockerfile` — 新增 XeLaTeX 编译环境（支持中文 PDF 技术报告）

## 签字栏结构（已知）

侧板（右下角 x≈960-1010）：
- y≈31：再归档+设计 → AA / 17-05-23
- y≈21：审核 → BB / 17-05-23
- y≈19：工艺 → CC / 17-06-15
- y≈14：标准化 → DD / 17-06-15
- y≈4：批准 → EE / 17-06-16
- HHLayerFR1：17-06-16（归档日期）
- HHLayerFR2：19-12-12（审核相关日期）

印刷版（右下角 x≈385-435）：
- y≈34：再归档 → AA / 18-12-17
- y≈29：设计 → BB / 19-03-20
- y≈25：审核 → 24-12-19（仅日期，无签名）
- y≈14：工艺 → CC / 19-03-20
- y≈9：标准化+归档 → DD / 19-10-21
- 批准栏为空
