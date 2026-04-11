# TestPipe

TestPipe 是一个基于 Pipeline 的测试编排框架，当前已打通最小主链路:

- `YAML Case -> PipelineSpec -> TestEngine -> runs/`
- 本机 Host 执行
- 默认输出精简结果，`--debug` 才输出定位文件
- LLM 模板/skill 驱动的生成、检查、执行、分析链路

## 快速上手

### 1. 环境要求

- Python `3.11+`

### 2. 安装

在仓库根目录执行:

```bash
pip install -e .
```

### 3. 查看内置 Pipeline

```bash
testpipe list-pipelines
```

当前最小示例会返回:

```text
LocalCompilePipeline
SmokePipeline
```

### 4. 运行示例用例

```bash
testpipe run examples/testcases/smoke.yaml
```

预期输出类似:

```json
{
  "case_id": "smoke_case",
  "pipeline": "SmokePipeline",
  "status": "passed",
  "outputs": {
    "echoed_message": "hello testpipe"
  }
}
```

也可以运行本地资源拉取、编译、传输的完整样例:

```bash
testpipe run examples/testcases/local_compile.yaml
```

该样例会在 `artifacts/` 下得到稳定产物路径，适合作为后续设备执行链路的基础验证。

### 5. 查看运行结果

默认模式下，会在 `runs/` 下生成独立目录，主要包含:

- `summary.json`
- `execution.log`
- `artifacts/` 里的业务产物

典型结构:

```text
runs/
  smoke_case_YYYYMMDD_HHMMSS/
    summary.json
    execution.log
    artifacts/
```

默认执行时，控制台和 `execution.log` 都会显式记录每个阶段的:

- 开始执行
- 输入摘要
- 完成状态
- 用户可见输出摘要
- 耗时

说明:

- 内部控制输出不会默认展示，例如环境检查返回的内部信号
- 只有对用户有意义的业务输出才会进入阶段摘要

### 6. Debug 模式

如果需要排查问题，可以开启 `--debug`:

```bash
testpipe run examples/testcases/smoke.yaml --debug
```

这时会额外输出:

- `case_spec.yaml`
- `pipeline_spec.json`
- `env_profile.json`
- `trace.json`
- `reproduce.sh`
- `steps/<step>/step.json`
- `steps/<step>/stdout.log`
- `steps/<step>/stderr.log`

典型结构:

```text
runs/
  smoke_case_YYYYMMDD_HHMMSS/
    summary.json
    case_spec.yaml
    pipeline_spec.json
    env_profile.json
    trace.json
    reproduce.sh
    steps/
```

### 7. 示例用例内容

示例文件在 [smoke.yaml](/home/wyb/AscendCode/TestPipe/examples/testcases/smoke.yaml):

```yaml
test_case:
  case_id: smoke_case
  name: SmokePipeline_Basic
  pipeline: SmokePipeline
  inputs:
    message: "hello testpipe"
  expected:
    echoed_message: "hello testpipe"
```

### 8. LLM 模板与 Skill 快速链路

当前已经支持用模板文件驱动常见流程:

1. 生成用例

```bash
testpipe run-skill case-generator examples/templates/generate_case_smoke.yaml --json
```

2. 检查用例

```bash
testpipe run-skill case-checker examples/templates/check_case_smoke.yaml --json
```

3. 生成执行计划或直接执行

```bash
testpipe run-skill case-runner examples/templates/run_case_smoke.yaml --json
```

4. 生成算子或 Pipeline 脚手架

```bash
testpipe run-skill test-op-generator examples/templates/generate_test_op_scaffold.yaml --json
testpipe run-skill pipeline-generator examples/templates/generate_pipeline_scaffold.yaml --json
```

说明:

- 不带 `scaffold.enabled: true` 时，generator 只返回结构化草稿
- 开启 scaffold 后，会按模板中的 `root_dir` 写入生成文件
- `case-runner` 使用 `execute: false` 时只返回计划，`execute: true` 时会实际执行
- `case-runner --json` 的执行阶段日志会出现在 `execution_console_log` 字段中，便于脚本消费

## 当前实现范围

当前代码骨架已经具备:

- `Spec` 模型
- `Pipeline` DSL 与编译器
- `TestEngine`
- `ActionRunner`
- `TraceRecorder`
- `ArtifactStore`
- 内置 `SmokePipeline` 与 `LocalCompilePipeline`
- 内置 LLM 模板注册表与 skill 注册表
- `run-skill` CLI 入口
- `case-generator / case-checker / case-runner / result-analyzer`
- `test-op-generator / pipeline-generator` 脚手架生成

当前尚未完整接入:

- Device 执行
- SSH / SFTP / NFS
- 更复杂的业务算子
- 真实大模型调用与多 skill workflow orchestration

## 常用命令

```bash
# 运行单个用例
testpipe run examples/testcases/smoke.yaml

# 运行并输出调试文件
testpipe run examples/testcases/smoke.yaml --debug

# 执行前先检查用例和 Pipeline 契约是否匹配
testpipe check-case examples/testcases/smoke.yaml

# 列出已注册 Pipeline
testpipe list-pipelines

# 列出内置模板与 skill
testpipe list-templates
testpipe list-skills

# 查看模板骨架与 skill 契约
testpipe show-template case-template
testpipe show-skill case-runner --json

# 用模板输入直接执行 skill
testpipe run-skill case-generator examples/templates/generate_case_smoke.yaml --json
testpipe run-skill case-checker examples/templates/check_case_smoke.yaml --json
testpipe run-skill case-runner examples/templates/run_case_smoke.yaml --json

# 直接生成脚手架文件
testpipe run-skill test-op-generator examples/templates/generate_test_op_scaffold.yaml --json
testpipe run-skill pipeline-generator examples/templates/generate_pipeline_scaffold.yaml --json

# 运行测试
python3 -m unittest discover -s tests -v
```

## 文档入口

完整设计文档见 [docs/README.md](/home/wyb/AscendCode/TestPipe/docs/README.md)。

重点推荐:

- [软件需求说明书](/home/wyb/AscendCode/TestPipe/docs/requirements/02_软件需求说明书.md)
- [核心对象模型设计](/home/wyb/AscendCode/TestPipe/docs/architecture/07_核心对象模型设计.md)
- [执行与追踪机制设计](/home/wyb/AscendCode/TestPipe/docs/architecture/08_执行与追踪机制设计.md)
- [LLM 原生模板与 Skills 设计](/home/wyb/AscendCode/TestPipe/docs/architecture/09_LLM原生模板与Skills设计.md)
