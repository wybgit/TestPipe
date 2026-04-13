# LLM 原生模板与 Skills 设计

## 1. 文档目标

本文档定义 TestPipe 如何天然适配大模型参与测试开发与执行，覆盖以下环节:

- 测试节点生成
- 测试构图生成
- 测试用例生成
- 测试用例检查
- 测试执行调用
- 测试结果分析

目标不是把大模型硬塞进框架，而是让大模型围绕**统一模板、统一 skill、统一 Spec** 工作，最终仍由框架的静态契约和执行引擎兜底。

---

## 2. 设计原则

- **Template First**: 所有 LLM 输入都先落成模板，不直接依赖自由文本。
- **Skill by Stage**: 每一类任务对应单一职责的 skill。
- **Spec as Output**: 所有 skill 产物最终都要映射到 `OpSpec / PipelineSpec / CaseSpec / ResultSummary`。
- **Check before Run**: 生成后的节点、构图、用例必须先经过检查 skill，再进入执行环节。
- **Structured Analysis**: 结果分析必须输出结构化结论，而不是纯自然语言总结。

---

## 3. LLM 原生工作流总览

推荐工作流如下:

1. 用户选择任务类型
2. 用户填写对应模板
3. 调用对应 skill
4. skill 输出结构化产物
5. 框架执行 schema / spec 校验
6. 必要时调用检查 skill 修正
7. 进入执行或分析阶段

整体链路可以表达为:

```text
Template Input
  -> Skill
  -> Structured Draft
  -> Spec Validation
  -> Check / Fix
  -> Run / Analyze
```

---

## 4. 模板体系

建议将模板定义为框架级资产，由 `Template Registry` 管理。

## 4.1 模板类型

至少定义以下模板:

1. `test-op-template`
2. `pipeline-template`
3. `case-template`
4. `case-check-template`
5. `run-template`
6. `result-analysis-template`

### 说明

- 节点生成关注 `TestOp`
- 构图生成关注 `PipelineSpec`
- 用例生成关注 `CaseSpec`
- 用例检查关注合法性与缺失项
- 执行模板关注运行选择和环境
- 结果分析关注输入结果和输出结论

---

## 4.2 TestOp Template

用于生成新的测试节点。

建议字段:

```yaml
task_type: generate_test_op
op_name: ""
op_category: ""
business_goal: ""
inputs:
  - name: ""
    type: ""
    description: ""
outputs:
  - name: ""
    type: ""
    description: ""
attributes:
  - name: ""
    type: ""
    default: null
    description: ""
dependencies:
  host_tools: []
  device_tools: []
side_effects:
  - host_exec
  - device_exec
validation_rules: []
examples: []
```

### 期望输出

- `OpSpec`
- 算子代码草稿
- 单元测试草稿
- 文档草稿

---

## 4.3 Pipeline Template

用于生成测试构图。

建议字段:

```yaml
task_type: generate_pipeline
pipeline_name: ""
business_goal: ""
pipeline_inputs: []
pipeline_outputs: []
stages:
  - name: ""
    goal: ""
required_ops: []
optional_ops: []
data_flow_notes: []
constraints:
  allow_parallel: false
  requires_device: true
expected_artifacts: []
```

### 期望输出

- `PipelineSpec`
- Python DSL 草稿
- DOT / Mermaid 草稿

---

## 4.4 Case Template

用于生成测试用例。

建议字段:

```yaml
task_type: generate_case
case_name: ""
target_pipeline: ""
test_goal: ""
inputs: {}
expected: {}
dataset_mode: single
tags: []
priority: P2
environment_hint: ""
```

### 期望输出

- `CaseSpec`
- YAML 用例文件
- 如需批量场景，输出 CSV/Excel 列定义建议

---

## 4.5 Case Check Template

用于检查生成好的用例是否合法。

建议字段:

```yaml
task_type: check_case
pipeline_spec_ref: ""
case_spec: {}
check_items:
  - schema
  - required_inputs
  - expected_rules
  - environment_match
strict_mode: true
```

### 期望输出

```yaml
status: pass | fail | warn
issues:
  - level: error
    field: inputs.model_path
    message: "缺少必填字段"
fix_suggestions:
  - "补充 model_path"
normalized_case: {}
```

---

## 4.6 Run Template

用于让用户以模板方式触发执行，而不是手写复杂命令。

建议字段:

```yaml
task_type: run_case
case_ref: ""
pipeline_ref: ""
env_profile: ""
output_dir: ""
log_level: INFO
rerun_failed_only: false
artifacts_policy: keep_all
```

### 期望输出

- 标准运行命令
- 执行计划摘要
- 执行结果位置

---

## 4.7 Result Analysis Template

用于分析运行结果。

建议字段:

```yaml
task_type: analyze_result
case_ref: ""
summary_ref: ""
trace_ref: ""
focus:
  - failed_step
  - root_cause
  - retryability
  - fix_suggestion
comparison_baseline: ""
```

### 期望输出

```yaml
status: passed | failed | flaky
root_cause:
  type: env | input | op_logic | infra | unknown
  message: ""
failed_step: ""
evidence:
  logs: []
  actions: []
  artifacts: []
recommendations: []
```

---

## 5. Skill 体系设计

建议定义与模板一一对应的标准 skill 集合。

## 5.1 建议 skill 列表

1. `test-op-generator`
2. `pipeline-generator`
3. `case-generator`
4. `case-checker`
5. `case-runner`
6. `result-analyzer`
7. `workflow-orchestrator`

### 当前实现状态

当前代码已经落地以下基础能力:

- `Template Registry`
- `Skill Registry`
- `run-skill` CLI 入口
- `case-checker` 静态校验
- `case-runner` 结构化执行计划与可选实际执行
- `result-analyzer` 对 `summary.json` 和 `execution.log` 的结构化分析

当前阶段的重点是先把模板填充后的消费链路打通。框架本体只内置 skills 与执行能力，不直接承载大模型调用；未来如需 AI 参与，建议由 `OpenCode`、`Claude Code` 等外部代理间接调用这些 skills。

---

## 5.2 test-op-generator

### 输入

- `test-op-template`

### 输出

- `OpSpec`
- `TestOp` 代码草稿
- 测试与文档草稿

### 适用场景

- 新增测试节点
- 扩展新测试能力

---

## 5.3 pipeline-generator

### 输入

- `pipeline-template`
- 可选 `OpSpec` 列表

### 输出

- `PipelineSpec`
- Python DSL
- 可视化草稿

### 适用场景

- 新建标准测试链路
- 为既有节点生成推荐构图

---

## 5.4 case-generator

### 输入

- `case-template`
- `PipelineSpec`

### 输出

- `CaseSpec`
- YAML 用例
- 可选数据集列说明

### 适用场景

- 生成单个测试用例
- 批量数据集设计

---

## 5.5 case-checker

### 输入

- `case-check-template`
- `CaseSpec`
- `PipelineSpec`

### 输出

- 问题列表
- 修复建议
- 规范化后的用例

### 适用场景

- LLM 生成后自动审查
- 人工编写用例前置校验

---

## 5.6 case-runner

### 输入

- `run-template`
- `CaseSpec`
- `EnvProfile`

### 输出

- 执行命令
- 执行摘要
- 结果引用路径

### 适用场景

- 让用户通过统一模板调用执行
- 为自动化代理生成稳定运行入口

---

## 5.7 result-analyzer

### 输入

- `result-analysis-template`
- `summary.json`
- `trace.json`
- step 日志与 artifacts

### 输出

- 结构化根因分析
- 证据链
- 修复建议
- 可重试判断

### 适用场景

- 测试失败自动初判
- 回归结果批量分析

---

## 5.8 workflow-orchestrator

### 输入

- 用户任务意图
- 已填写模板
- skill 调用历史

### 输出

- 下一步建议
- skill 调用顺序
- 缺失信息清单

### 适用场景

- 将多个 skill 串成完整工作流
- 支持“从需求到执行到分析”的端到端代理链路

---

## 6. Skill 接口约束

每个 skill 都应定义统一接口契约。

## 6.1 Skill Metadata

建议字段:

```yaml
name: case-generator
description: 根据 case-template 和 pipeline-spec 生成测试用例
input_template: case-template
output_type: CaseSpec
preconditions:
  - pipeline_spec_available
```

## 6.2 Skill Output Contract

skill 输出必须至少包含:

- `status`
- `structured_output`
- `issues`
- `next_actions`

建议结构:

```yaml
status: success | partial | failed
structured_output: {}
issues: []
next_actions: []
```

---

## 7. Template Registry 设计

`Template Registry` 负责:

- 注册模板名称和版本
- 导出模板
- 提供默认值
- 绑定适用 skill

建议结构:

```python
class TemplateDescriptor(BaseModel):
    template_name: str
    version: str
    target_skill: str
    description: str
    schema_ref: str
```

---

## 8. Skill Registry 设计

`Skill Registry` 负责:

- 注册 skill 元数据
- 记录输入模板类型
- 记录输出类型
- 供 CLI / UI / Agent 查询

建议结构:

```python
class SkillDescriptor(BaseModel):
    skill_name: str
    input_template: str
    output_kind: str
    description: str
    stage: str
```

---

## 9. 与核心对象模型的映射

所有 LLM 产物最终都要落到框架统一对象上:

- `test-op-generator` -> `OpSpec`
- `pipeline-generator` -> `PipelineSpec`
- `case-generator` -> `CaseSpec`
- `case-checker` -> `CaseSpec` 修正结果 + issue list
- `case-runner` -> `RunRequest` / CLI command
- `result-analyzer` -> `AnalysisReport`

这一步是整个设计的关键。  
如果 skill 输出不能映射到统一对象模型，LLM 能力就无法真正接入框架主链路。

---

## 10. 用例检查与执行接入点

推荐执行链路:

```text
case-template
  -> case-generator
  -> CaseSpec draft
  -> case-checker
  -> normalized CaseSpec
  -> case-runner
  -> TestEngine
  -> ResultSummary / trace
  -> result-analyzer
```

---

## 11. 结果分析设计

结果分析不应只是自然语言总结，而要支持结构化消费。

建议定义:

```python
class AnalysisReport(BaseModel):
    status: str
    root_cause_type: str
    root_cause_message: str
    failed_step: str | None = None
    evidence: dict[str, list[str]]
    recommendations: list[str]
    retryable: bool = False
```

### 好处

- 可供人阅读
- 可供下一轮 LLM 自动修复
- 可供平台统计与聚类

---

## 12. CLI / 平台支持建议

建议提供模板导出与 skill 绑定能力，例如:

```bash
testpipe template export test-op-template
testpipe template export case-template
testpipe skill list
testpipe skill describe case-generator
```

未来也可以支持:

```bash
testpipe skill run case-checker --input case_check.yaml
```

---

## 13. MVP 建议

MVP 阶段建议先落以下 4 个 skill:

1. `case-generator`
2. `case-checker`
3. `case-runner`
4. `result-analyzer`

### 原因

- 直接服务实际测试闭环
- 与现有执行引擎结合最紧密
- 风险低于直接做 `test-op-generator` 和 `pipeline-generator`

第二阶段再补:

- `test-op-generator`
- `pipeline-generator`
- `workflow-orchestrator`

---

## 14. 风险与控制点

### 14.1 风险

- 自由文本输入过多，skill 输出不稳定
- 节点和构图生成结果不满足框架契约
- 检查和执行链路脱节
- 分析结果不可结构化复用

### 14.2 控制点

- 强制模板输入
- 输出统一映射到 Spec
- 先检查后执行
- analysis 使用固定结构输出

---

## 15. 结论

要让框架“天然适配大模型编程实现”，关键不在于把所有流程交给大模型，而在于:

1. 先定义统一模板
2. 再定义与模板对应的 skill
3. 最后把 skill 输出严格映射到框架对象模型

这样才能让大模型真正成为框架的稳定扩展面，而不是一个不可控的旁路工具。
