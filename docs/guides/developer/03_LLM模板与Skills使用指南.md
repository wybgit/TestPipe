# 开发指南 - LLM 模板与 Skills 使用

## 1. 目标

本文档说明如何使用 TestPipe 的模板和 skill 体系完成以下任务:

- 生成测试节点
- 生成测试构图
- 生成测试用例
- 检查测试用例
- 调用执行
- 分析测试结果

重点不是 prompt 技巧，而是让外部代理始终围绕稳定的结构化输入工作。

---

## 2. 使用原则

- 先导出模板，再填信息
- 先生成，再检查，再执行
- 用例文件格式始终与框架实际 `pipeline + cases` 结构保持一致
- 执行环境通过 `testpipe.config.yaml` 中的命名环境选择
- `run-skill --json` 输出是外部代理消费的唯一可靠接口

## 2.1 当前 CLI 入口

```bash
testpipe list-templates
testpipe show-template case-template
testpipe list-skills
testpipe show-skill case-runner --json
testpipe run-skill case-generator /path/to/generate_case.yaml --json
testpipe run-skill case-checker /path/to/check_case.yaml --json
testpipe run-skill case-runner /path/to/run_case.yaml --json
testpipe run examples/testcases/onnx_git_atc.yaml
```

说明:

- `run-skill` 默认把结构化结果输出到标准输出
- `case-runner` 在 `execute: false` 时只返回执行计划
- `case-runner` 在 `execute: true` 时会实际调用 `TestEngine`
- 执行阶段日志会收敛到 `execution_console_log` 字段，便于脚本消费
- 框架当前只内置 deterministic skills，不在框架内部直接承载大模型调用

---

## 3. 节点生成

### 3.1 使用的模板

- `test-op-template`

### 3.2 推荐流程

1. `testpipe show-template test-op-template > op.yaml`
2. 补齐节点输入、输出、属性和依赖
3. 调用 `test-op-generator`
4. 审查输出的 `OpSpec`、代码草稿和单测草稿

---

## 4. 构图生成

### 4.1 使用的模板

- `pipeline-template`

### 4.2 推荐流程

1. `testpipe show-template pipeline-template > pipeline.yaml`
2. 填写 Pipeline 名称、阶段划分、必选节点和输入输出
3. 调用 `pipeline-generator`
4. 审查 `PipelineSpec` 和 Mermaid 草稿

---

## 5. 用例生成

### 5.1 使用的模板

- `case-template`

### 5.2 当前推荐用例结构

`case-template` 输出的 YAML 草稿应直接对齐框架正式用例格式:

```yaml
pipeline:
  name: OnnxGitAtcPipeline
  fetchModelNode:
    repo: https://github.com/wybgit/onnx-layer.git
    path: Abs_testcase_5a6b43
    model_pattern: "*.onnx"
  compileModelNode:
    soc_version: Ascend310P3
    env_script: /home/wyb/Ascend/cann-8.5.0/set_env.sh
  assertOmExistsNode:
    expected_value: true
cases:
  - case_id: onnx_git_atc_case
    description: 验证从 Git 仓获取 ONNX 并完成 ATC 转换
    level: P0
```

### 5.3 推荐流程

1. `testpipe show-template case-template > case.yaml`
2. 在 `pipeline` 下填写目标 Pipeline 名称和通用节点输入
3. 在 `cases` 下填写 `case_id` 和差异化节点输入
4. 调用 `case-generator`
5. 调用 `case-checker`

关键约束:

- `pipeline.name` 必填
- `pipeline` 下其余字段直接写节点名
- `cases[*]` 下其余字段也直接写节点名
- 通用值放在 `pipeline`，差异值放在具体 `case`

---

## 6. 用例检查

### 6.1 使用的模板

- `case-check-template`

### 6.2 检查重点

- 节点名是否真实存在于 Pipeline 图中
- 节点输入端口名是否正确
- 是否错误覆盖了被上游边驱动的端口
- 必填输入是否齐全

---

## 7. 执行与结果分析

### 7.1 执行模板

`run-template` 重点字段:

- `case_ref`
- `framework_config`
- `env_profile`
- `output_dir`
- `execute`

### 7.2 推荐流程

1. `testpipe show-template run-template > run.yaml`
2. 填写用例文件路径和环境选择
3. 先用 `execute: false` 生成计划
4. 确认无误后切到 `execute: true`

### 7.3 结果分析

`result-analysis-template` 用于读取 `summary.json` 或失败 step 结果并输出结构化分析。

---

## 8. 结论

当前模板与 skill 的定位已经清晰:

- TestPipe 负责模板、校验、执行、分析
- 外部代理负责补全模板和组织调用顺序
- 正式用例格式统一为 `pipeline + cases`
