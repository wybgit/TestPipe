# TestPipe

TestPipe 是一个基于 Pipeline 的测试编排框架，当前已打通最小主链路:

- `YAML Case -> PipelineSpec -> TestEngine -> runs/`
- 默认使用当前宿主机环境执行
- SSH/SFTP 基础执行与传输命令层
- 环境能力统一收敛到框架配置文件 `testpipe.config.yaml`
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
MockDeviceJsonPipeline
MockDevicePipeline
MockDeviceRoundTripPipeline
MockDeviceUppercasePipeline
SmokePipeline
```

### 4. 运行示例用例

当前 `examples/testcases/` 目录只保留一个主线案例，从 Git 仓拉取 ONNX 并通过 CANN `atc` 转换成 `om`:

```bash
testpipe run examples/testcases/onnx_git_atc.yaml
```

默认会直接使用仓库根目录 `testpipe.config.yaml` 中的默认环境，也就是当前宿主机本地环境。

该样例会走 `ResourceFetch(git_dir) -> ATCCompile -> PathExists -> ValueCompare`，其中 `ATCCompile` 会执行:

```bash
source /home/wyb/Ascend/cann-8.5.0/set_env.sh
```

随后调用 `atc` 完成 ONNX 到 OM 的真实转换，默认核心命令形态对齐为:

```bash
atc --model=./Abs_testcase_5a6b43.onnx --framework=5 --output=Abs_testcase_5a6b43 --soc_version=Ascend310P3
```

其中 `atc_options` 只用于追加额外参数，不会覆盖这 4 个保留主参数。

如果需要传入额外的 `atc` 参数，可以在 `compileModelNode` 中追加:

```yaml
pipeline:
  name: OnnxGitAtcPipeline
  compileModelNode:
    atc_options:
      precision_mode: allow_fp32_to_fp16
      input_format: NCHW
      dynamic_batch_size: "1,4,8"
cases:
  - case_id: onnx_git_atc_case
    name: OnnxGitAtcPipeline_Basic
```

这些参数会被转换为:

```bash
--precision_mode=allow_fp32_to_fp16 --input_format=NCHW --dynamic_batch_size=1,4,8
```

保留参数 `model / framework / output / soc_version` 不允许通过 `atc_options` 覆盖。

环境配置现在建议统一写入框架配置文件 `testpipe.config.yaml`。默认行为:

- 不传 `--env-profile` 时，使用配置文件中的 `default_env`
- 仓库默认 `default_env=local`，即当前宿主机环境
- `ssh / docker / conda` 等扩展环境必须先在配置文件中声明并 `enabled: true`

例如默认 local:

```bash
testpipe run examples/testcases/onnx_git_atc.yaml --env-profile local
```

如果需要显式指定其他配置文件，可以传入:

```bash
testpipe run examples/testcases/onnx_git_atc.yaml --config /path/to/testpipe.config.yaml --env-profile local
```

仓库默认提供的 [testpipe.config.yaml](/home/wyb/AscendCode/TestPipe/testpipe.config.yaml) 当前只保留最小环境集合:

- `local`
- `docker`，默认禁用
- `ssh`，默认禁用

其中扩展环境配置重点覆盖:

- `device.remote_root`: 统一约束远端文件路径根目录
- `device.workdir`: 统一约束远端命令执行目录
- `device.ssh_options`: 透传到 `ssh/scp`
- `device.connect_timeout`: 连接超时配置
- `host.mode`: `local / conda / docker`
- `host.conda_env`: conda 模式目标环境名
- `host.docker_image`: docker 模式目标镜像

### 5. 查看运行结果

默认模式下，会在 `runs/` 下生成独立目录，主要包含:

- `summary.json`
- `execution.log`
- `resources/` 里的用例资源和稳定产物
- `steps/<step>/` 下的执行日志、执行结果和命令脚本
- `device_fs/` 下的 mock device 工作空间产物（仅设备 mock 场景）

典型结构:

```text
runs/
  onnx_git_atc_case_YYYYMMDD_HHMMSS/
    summary.json
    execution.log
    resources/
    steps/
```

默认执行时，控制台和 `execution.log` 都会显式记录每个阶段的:

- 节点类型: `INPUT / EXEC / OUTPUT`
- `INPUT` 节点显示输入信息
- `EXEC` 节点显示 `I / B / O`
- `OUTPUT` 节点显示 `O / CHECK`
- 控制台末尾显示单独的 `SUMMARY` 面板

说明:

- 日志会尽量只展示对定位问题和理解流程有帮助的核心信息
- 终端如果安装了 `rich` 会使用彩色块状日志；`execution.log` 仍保持纯文本，便于检索和归档
- 每个 step 目录下会保留 `command.sh / stdout.log / stderr.log / execution.log / result.json`

### 6. Debug 模式

如果需要排查问题，可以开启 `--debug`:

```bash
testpipe run examples/testcases/onnx_git_atc.yaml --debug
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

示例文件在 [onnx_git_atc.yaml](/home/wyb/AscendCode/TestPipe/examples/testcases/onnx_git_atc.yaml):

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
    description: 验证从Git仓获取ONNX并成功完成ATC转换
    level: P0
```

统一格式下，顶层只保留两部分:

- `pipeline`: 声明目标 pipeline 名称和通用节点参数
- `cases`: 只声明 case 信息和差异化节点参数覆盖

每个节点配置都直接写成 `节点名: {输入参数k-v}`。通用参数写在 `pipeline` 段，对单个 case 的差异化覆盖写在 `cases[*]` 里。同名节点参数会按 case 覆盖 pipeline 默认值。

说明:

- `pipeline.name` 必填，表示当前文件绑定的目标 Pipeline
- `pipeline` 下除 `name` 外，其余字段直接写节点名
- `cases` 里 `case_id` 必填，且在当前 YAML 文件内必须唯一
- `cases[*]` 支持用例级字段: `description`、`level`
- `cases[*]` 下除这些用例字段外，其余字段都直接写节点名
- `fetchModelNode.path` 可以是 Git 仓内目录，也可以是单个文件路径
- `fetchModelNode.path` 为目录时下载该目录内容，为文件时只下载该文件
- 断言值应该写到断言节点输入中，例如 `assertOmExistsNode.expected_value`
- 节点输入会直接注入对应节点，不再要求先声明成 Pipeline 顶层输入
- 如果某个端口已经由上游边连接驱动，就不应该再在用例里手动赋值
- 当前示例节点命名统一推荐使用 `*Node` 后缀，Pipeline 命名统一使用 `*Pipeline` 后缀
- 旧格式 `test_case` / `test_suite` 仍然兼容读取，但不再推荐继续新增

### 8. 模板与 Skill 快速链路

当前已经支持用结构化 payload 文件驱动常见流程。可以先用 `testpipe show-template <name>` 查看模板骨架，再把内容保存成自己的 YAML 文件后执行:

1. 生成用例

```bash
testpipe show-template case-template
testpipe run-skill case-generator /path/to/case-generator-input.yaml --json
```

2. 检查用例

```bash
testpipe show-template case-check-template
testpipe run-skill case-checker /path/to/case-check-input.yaml --json
```

3. 生成执行计划或直接执行

```bash
testpipe show-template run-template
testpipe run-skill case-runner /path/to/run-input.yaml --json
```

4. 生成算子或 Pipeline 脚手架

```bash
testpipe show-template test-op-template
testpipe run-skill test-op-generator /path/to/test-op-input.yaml --json
testpipe show-template pipeline-template
testpipe run-skill pipeline-generator /path/to/pipeline-input.yaml --json
```

说明:

- 不带 `scaffold.enabled: true` 时，generator 只返回结构化草稿
- 开启 scaffold 后，会按模板中的 `root_dir` 写入生成文件
- `case-runner` 使用 `execute: false` 时只返回计划，`execute: true` 时会实际执行
- `case-runner --json` 的执行阶段日志会出现在 `execution_console_log` 字段中，便于脚本消费
- `case-runner` 支持从 `framework_config` 加载框架配置，并通过 `env_profile` 选择命名环境
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
- 内置 `MockDeviceJsonPipeline`
- 内置 `MockDevicePipeline`
- 内置 `MockDeviceRoundTripPipeline`
- 内置 `MockDeviceUppercasePipeline`
- 内置 `OnnxGitAtcPipeline`
- 内置模板注册表与 skill 注册表
- `run-skill` CLI 入口
- `case-generator / case-checker / case-runner / result-analyzer`
- `test-op-generator / pipeline-generator` 脚手架生成
- 默认框架配置加载与命名环境解析
- 兼容 legacy `EnvProfile` YAML/JSON 直载方式
- `DeviceExecutor` / `TransferExecutor` 的 mock 模式
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
- 基础 Host / mock-device / SSH-SFTP 运行骨架
- 一组可直接运行的内置 Pipeline 和示例用例
- 示例目录当前只保留 `onnx_git_atc.yaml`
- normal/debug 双模式输出
- 模板/skill 驱动的生成、检查、执行、分析入口

后续开发将优先围绕真实案例推进，不再继续单独扩张抽象层。

## 常用命令

```bash
# 运行并输出调试文件
testpipe run examples/testcases/onnx_git_atc.yaml --debug

# 指定框架配置和命名环境
testpipe run examples/testcases/onnx_git_atc.yaml --config testpipe.config.yaml --env-profile local

# 运行 Git ONNX -> OM 主线案例，默认使用当前宿主机 local 环境
testpipe run examples/testcases/onnx_git_atc.yaml

# 执行前先检查用例和 Pipeline 契约是否匹配
testpipe check-case examples/testcases/onnx_git_atc.yaml

# 列出已注册 Pipeline
testpipe list-pipelines

# 列出内置模板与 skill
testpipe list-templates
testpipe list-skills

# 查看模板骨架与 skill 契约
testpipe show-template case-template
testpipe show-skill case-runner --json

# 用自定义 payload 文件直接执行 skill
testpipe run-skill case-generator /path/to/case-generator-input.yaml --json
testpipe run-skill case-checker /path/to/case-check-input.yaml --json
testpipe run-skill case-runner /path/to/run-input.yaml --json

# 直接生成脚手架文件
testpipe run-skill test-op-generator /path/to/test-op-input.yaml --json
testpipe run-skill pipeline-generator /path/to/pipeline-input.yaml --json

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
