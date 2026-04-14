# TestPipe

TestPipe 是一个基于 Pipeline 的测试编排框架，当前已打通最小主链路:

- `YAML Case -> PipelineSpec -> TestEngine -> runs/`
- 本机 Host 执行
- SSH/SFTP 基础执行与传输命令层
- 默认输出精简结果，`--debug` 才输出定位文件
- 模板/skill 驱动的生成、检查、执行、分析链路

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
LocalCompileAssertPipeline
LocalCompilePipeline
OnnxGitAtcPipeline
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

该样例会在 `resources/` 下得到稳定产物路径，适合作为后续设备执行链路的基础验证。

如果需要验证“产物存在 + 断言通过”的本地闭环，可以运行:

```bash
testpipe run examples/testcases/local_compile_assert.yaml
```

该样例会在编译传输后追加 `PathExists -> ValueCompare` 断言链路，并输出 `path_exists` 与 `test_passed`。

如果需要运行真实主线案例，从 Git 仓拉取 ONNX 并通过 CANN `atc` 转换成 `om`，可以运行:

```bash
testpipe run examples/testcases/onnx_git_atc.yaml --env-profile examples/env_profiles/local_cann_atc.yaml
```

该样例会走 `ResourceFetch(git_dir) -> ATCCompile -> PathExists -> ValueCompare`，其中 `ATCCompile` 会执行:

```bash
source /home/wyb/Ascend/cann-8.5.0/set_env.sh
```

随后调用 `atc` 完成 ONNX 到 OM 的真实转换，默认核心命令形态对齐为:

```bash
atc --model=./Abs_testcase_5a6b43.onnx --framework=5 --output=Abs_testcase_5a6b43 --soc_version=Ascend310P3
```

其中 `atc_options` 只用于追加额外参数，不会覆盖这 4 个保留主参数。

如果需要传入额外的 `atc` 参数，可以在 case 中追加:

```yaml
inputs:
  atc_options:
    precision_mode: allow_fp32_to_fp16
    input_format: NCHW
    dynamic_batch_size: "1,4,8"
```

这些参数会被转换为:

```bash
--precision_mode=allow_fp32_to_fp16 --input_format=NCHW --dynamic_batch_size=1,4,8
```

保留参数 `model / framework / output / soc_version` 不允许通过 `atc_options` 覆盖。

如果需要显式指定环境配置，可以传入 `EnvProfile` 文件:

```bash
testpipe run examples/testcases/smoke.yaml --env-profile examples/env_profiles/local_default.yaml
```

如果需要准备真实设备环境，可以参考 SSH/SFTP 环境模板:

```bash
cat examples/env_profiles/ssh_device.yaml
```

这个模板当前重点覆盖:

- `device.remote_root`: 统一约束远端文件路径根目录
- `device.workdir`: 统一约束远端命令执行目录
- `device.ssh_options`: 透传到 `ssh/scp`
- `device.connect_timeout`: 连接超时配置

### 5. 查看运行结果

默认模式下，会在 `runs/` 下生成独立目录，主要包含:

- `summary.json`
- `execution.log`
- `resources/` 里的用例资源和稳定产物
- `steps/<step>/` 下的执行日志、执行结果和命令脚本

典型结构:

```text
runs/
  smoke_case_YYYYMMDD_HHMMSS/
    summary.json
    execution.log
    resources/
    steps/
```

默认执行时，控制台和 `execution.log` 都会显式记录每个阶段的:

- 节点类型: 输入 / 执行 / 输出
- 输入参数
- 执行参数与实际命令
- 执行过程日志摘要
- 输出结果
- 校验内容与校验结果
- 用例总结果、总耗时、运行目录

说明:

- 日志会尽量只展示对定位问题和理解流程有帮助的核心信息
- 终端如果安装了 `rich` 会使用彩色块状日志；`execution.log` 仍保持纯文本，便于检索和归档
- 每个 step 目录下会保留 `command.sh / stdout.log / stderr.log / execution.log / result.json`

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

说明:

- `steps/<step>/stdout.log` 和 `steps/<step>/stderr.log` 会按动作追加记录，不会被最后一条命令覆盖
- 默认模式下也会保留 step 目录，便于复查每一步的命令、日志和结果

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

### 8. 模板与 Skill 快速链路

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
- `case-runner` 支持从 `env_profile` 字段加载 YAML/JSON 环境文件
- 框架只内置 deterministic skills，不在框架内部承载大模型调用
- 后续如果需要 AI 参与，可由 `OpenCode`、`Claude Code` 等外部代理填模板后调用 `run-skill`

## 当前实现范围

当前代码骨架已经具备:

- `Spec` 模型
- `Pipeline` DSL 与编译器
- `TestEngine`
- `ActionRunner`
- `TraceRecorder`
- `ArtifactStore`
- 内置 `SmokePipeline` 与 `LocalCompilePipeline`
- 内置 `LocalCompileAssertPipeline`
- 内置 `OnnxGitAtcPipeline`
- 内置模板注册表与 skill 注册表
- `run-skill` CLI 入口
- `case-generator / case-checker / case-runner / result-analyzer`
- `test-op-generator / pipeline-generator` 脚手架生成
- `EnvProfile` YAML/JSON 加载与运行时注入
- `DeviceExecutor` / `TransferExecutor` 的 local / SSH-SFTP 模式
- SSH/SFTP 命令构建、远端根目录约束、远端目录预创建
- `transfer.put / transfer.get / device.exec` trace 记录
- `ResourceFetch` 主线支持本地路径与 Git 仓目录资源
- `ATCCompile` 主线支持真实 `atc` 执行与 `extra atc options`
- 通用断言算子 `TextEquals / PathExists / ValueCompare / JsonObjectAssert`
- JSON 结果读取算子 `ReadJsonArtifact`

当前尚未完整接入:

- 真实设备网络、权限、工具链差异下的案例验证
- 更复杂的业务算子
- Device 侧 Provider 与环境能力补全
- 外部 AI 代理的间接集成约定

## 基础开发状态

当前可以认为“功能框架的基本开发内容”已经完成，范围包括:

- 统一执行主链路
- 基础 Host / local-device / SSH-SFTP 运行骨架
- 一组可直接运行的内置 Pipeline 和示例用例
- normal/debug 双模式输出
- 模板/skill 驱动的生成、检查、执行、分析入口

当前功能检查默认只保留简单 `smoke` 用例。

## 常用命令

```bash
# 运行单个用例
testpipe run examples/testcases/smoke.yaml

# 运行本地编译断言样例
testpipe run examples/testcases/local_compile_assert.yaml

# 运行并输出调试文件
testpipe run examples/testcases/smoke.yaml --debug

# 指定环境配置文件
testpipe run examples/testcases/smoke.yaml --env-profile examples/env_profiles/local_default.yaml

# 运行 Git ONNX -> OM 主线案例
testpipe run examples/testcases/onnx_git_atc.yaml --env-profile examples/env_profiles/local_cann_atc.yaml

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
testpipe run-skill case-runner examples/templates/run_case_local_compile_assert.yaml --json
testpipe run-skill case-runner examples/templates/run_case_onnx_git_atc.yaml --json

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
- [外部代理调用 Skills 指南](/home/wyb/AscendCode/TestPipe/docs/guides/user/01_外部代理调用Skills指南.md)
