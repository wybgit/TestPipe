# 开发指南 - LLM 模板与 Skills 使用

## 1. 目标

本文档说明如何使用 TestPipe 的模板和 skill 体系完成以下任务:

- 生成测试节点
- 生成测试构图
- 生成测试用例
- 检查测试用例
- 调用执行
- 分析测试结果

这里的重点不是 prompt 技巧，而是如何按框架要求提供稳定输入。

---

## 2. 使用原则

- 先选模板，再填信息
- 先调用生成 skill，再调用检查 skill
- 检查通过后再执行
- 结果分析优先读取结构化产物

## 2.1 当前 CLI 入口

当前版本已经提供以下命令:

```bash
testpipe list-templates
testpipe show-template case-template
testpipe list-skills
testpipe show-skill case-runner --json
testpipe run-skill case-generator examples/templates/generate_case_smoke.yaml --json
testpipe run-skill case-checker examples/templates/check_case_smoke.yaml --json
testpipe run-skill case-runner examples/templates/run_case_smoke.yaml --json
```

说明:

- `run-skill` 默认把结构化结果输出到标准输出
- `case-runner` 在 `execute: false` 时只返回执行计划
- `case-runner` 在 `execute: true` 时会实际调用 `TestEngine`
- 为保证 `--json` 可被脚本消费，执行阶段日志会收敛到 `execution_console_log` 字段

---

## 3. 节点生成

### 3.1 使用的模板

- `test-op-template`

### 3.2 用户需要填写的信息

- 节点名称
- 节点目标
- 输入输出
- 属性
- 外部依赖
- 副作用类型

### 3.3 推荐流程

1. 导出模板
2. 补齐节点字段
3. 调用 `test-op-generator`
4. 审查输出的 `OpSpec` 和代码草稿

### 3.4 示例

```yaml
task_type: generate_test_op
op_name: ATCCompile
op_category: compile
business_goal: 将 onnx 模型编译为 om 模型
inputs:
  - name: model_path
    type: artifact:path
    description: 待编译模型
  - name: soc_version
    type: string
    description: 目标芯片型号
outputs:
  - name: om_path
    type: artifact:path
    description: 编译产物路径
attributes:
  - name: timeout
    type: int
    default: 600
    description: 编译超时时间
side_effects:
  - host_exec
```

---

## 4. 构图生成

### 4.1 使用的模板

- `pipeline-template`

### 4.2 用户需要填写的信息

- Pipeline 名称
- 业务目标
- 输入输出
- 阶段划分
- 必选节点
- 依赖约束

### 4.3 推荐流程

1. 填写 pipeline 模板
2. 调用 `pipeline-generator`
3. 审查 `PipelineSpec`
4. 导出 DOT / Mermaid 检查结构

### 4.4 示例

```yaml
task_type: generate_pipeline
pipeline_name: ATC_E2E_Pipeline
business_goal: 完成模型转换、板端推理和精度比对
pipeline_inputs:
  - model_source
  - soc_version
  - input_data
  - golden_output
pipeline_outputs:
  - test_passed
  - accuracy_score
stages:
  - name: prepare
    goal: 环境检查和资源准备
  - name: compile
    goal: 模型转换
  - name: infer
    goal: 板端执行
  - name: check
    goal: 精度校验
required_ops:
  - EnvCheck
  - ResourceFetch
  - ATCCompile
  - Transfer
  - Inference
  - AccuracyCheck
```

---

## 5. 用例生成

### 5.1 使用的模板

- `case-template`

### 5.2 用户需要填写的信息

- 目标 Pipeline
- 测试目标
- 输入数据
- 期望输出
- 标签和优先级

### 5.3 推荐流程

1. 填写 case 模板
2. 调用 `case-generator`
3. 得到 `CaseSpec` 和 YAML 草稿
4. 调用 `case-checker`

### 5.4 示例

```yaml
task_type: generate_case
case_name: ResNet50_FP16_Test
target_pipeline: ATC_E2E_Pipeline
test_goal: 验证 resnet50 onnx 模型在 Ascend310P3 上转换和推理精度
inputs:
  model_source: models/resnet50.onnx
  soc_version: Ascend310P3
  input_data: data/input.bin
  golden_output: data/golden.bin
expected:
  test_passed: true
  accuracy_score: ">= 0.99"
tags:
  - resnet50
  - smoke
priority: P0
```

---

## 6. 用例检查

### 6.1 使用的模板

- `case-check-template`

### 6.2 检查重点

- 必填字段是否齐全
- 输入类型是否匹配
- expected 是否与 Pipeline 输出一致
- 环境条件是否满足

### 6.3 推荐流程

1. 将 `CaseSpec` 交给 `case-checker`
2. 读取 `issues`
3. 修正后再次检查
4. 检查通过再执行

---

## 7. 执行调用

### 7.1 使用的模板

- `run-template`

### 7.2 用户需要填写的信息

- case 引用
- 环境 profile
- 输出目录
- log level

### 7.3 推荐流程

1. 填写运行模板
2. 调用 `case-runner`
3. 获取执行命令或执行计划
4. 交给 `TestEngine`

### 7.4 当前运行返回结构

`case-runner` 当前会输出:

- `run_command`
- `run_plan_summary`
- `result_location`
- `summary`
- `execution_console_log`

其中:

- `execute: false` 时，只返回命令和计划
- `execute: true` 时，会额外返回运行目录、结果摘要和执行阶段日志

---

## 8. 结果分析

### 8.1 使用的模板

- `result-analysis-template`

### 8.2 输入材料

- `summary.json`
- `trace.json`
- 失败 step 的日志
- 关键 artifacts

### 8.3 推荐流程

1. 填写分析模板
2. 调用 `result-analyzer`
3. 读取根因、证据链和修复建议

### 8.4 当前分析返回结构

`result-analyzer` 当前输出:

- `analysis_report`
- `root_cause`
- `fix_suggestions`

其中 `analysis_report` 至少包含:

- `status`
- `failed_step`
- `retryability`
- `evidence.issues`
- `evidence.failed_log_lines`

### 8.4 输出重点

- 失败步骤
- 根因类型
- 关键证据
- 是否建议重试
- 修复建议

---

## 9. 推荐的最小 skill 调用链

对于大多数用户，建议使用如下链路:

1. `case-generator`
2. `case-checker`
3. `case-runner`
4. `result-analyzer`

只有在需要扩展框架能力时，再使用:

5. `test-op-generator`
6. `pipeline-generator`

---

## 10. 模板填写建议

为了让 skill 输出更稳定，建议:

- 输入输出名称使用业务语义，不要都叫 `input` / `result`
- expected 只写可判断的结果
- 清楚标明运行环境限制
- 将副作用类型显式填出
- 尽量提供真实路径、真实参数和真实目标

---

## 11. 常见错误

### 11.1 模板字段不全

会导致 skill 生成结果缺少核心契约。

### 11.2 目标 Pipeline 不存在

会导致 case 生成或检查无法完成。

### 11.3 expected 与输出不匹配

这是最常见的 case 检查失败原因之一。

### 11.4 分析只给自然语言，不引用结构化结果

会导致后续无法自动修复和聚类分析。

---

## 12. 推荐后续动作

如果你准备实现这套能力，建议按以下顺序落地:

1. 先实现 `Template Registry`
2. 再实现 `Skill Registry`
3. 先支持 `case-generator / case-checker / result-analyzer`
4. 最后再支持 `test-op-generator / pipeline-generator`
