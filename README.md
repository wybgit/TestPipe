# TestPipe

TestPipe 是一个面向 NPU 测试场景的轻量编排框架。当前稳定主线是：

`YAML Case -> PipelineSpec -> TestEngine -> runs/`

当前仓库刻意收敛到最小可用模型：

- `Pipeline` 只描述业务步骤
- `TestOp` 只描述单步能力
- `TestEngine` 是唯一执行入口
- 简单结果检查优先写在 `expected`

## 当前范围

当前内置主线只有一个：

- `OnnxGitAtcPipeline`

流程：

1. `fetchModelNode` 从 Git 获取模型资源
2. `compileModelNode` 调用 `atc` 生成 `.om`
3. `expected` 对最终输出做检查

这意味着当前仓库更像一个“已打通主链路的框架骨架”，不是完整测试平台。

## 安装

要求：

- Python `3.11+`

安装：

```bash
pip install -e .
```

查看内置 Pipeline：

```bash
testpipe list-pipelines
```

## 快速开始

运行示例：

```bash
testpipe run examples/testcases/onnx_git_atc.yaml
```

校验用例：

```bash
testpipe check-case examples/testcases/onnx_git_atc.yaml --json
```

导出流程图：

```bash
testpipe export-pipeline-graph examples/testcases/onnx_git_atc.yaml --json
```

## 推荐 YAML 格式

推荐把节点参数统一写进 `nodes`，把简单断言写进 `expected`。

```yaml
pipeline:
  name: OnnxGitAtcPipeline
  nodes:
    fetchModelNode:
      repo: https://github.com/wybgit/onnx-layer.git
      branch: Abs
      path: Abs_testcase_5a6b43
      model_pattern: "*.onnx"
    compileModelNode:
      env_script: /home/wyb/Ascend/cann-8.5.0/set_env.sh
      soc_version: Ascend310P3

cases:
  - case_id: onnx_git_atc_case
    description: 验证从 Git 仓获取 ONNX 并成功完成 ATC 转换
    level: P0
    expected:
      om_path:
        exists: true
```

规则：

- `pipeline.name` 必填
- `pipeline.nodes` 放通用节点参数
- `cases[*].nodes` 放单 case 覆盖参数
- `expected` 用于简单结果检查
- 旧格式仍兼容，但不建议继续新增

## 参数约定

当前实现只保留两类节点参数：

- `inputs`：图里流转的值
- `attrs`：节点行为参数或默认值

以主线为例：

- `fetchModelNode.repo / branch / path` 是输入
- `fetchModelNode.model_pattern` 是属性
- `compileModelNode.model_path` 是输入
- `compileModelNode.soc_version / env_script / atc_options / output_name / timeout / framework` 是属性

如果某个值只是控制节点行为，不要提升成 Pipeline 级输入。

## 输出结果

一次执行会生成独立 run 目录：

```text
runs/
  onnx_git_atc_case_YYYYMMDD_HHMMSS/
    summary.json
    execution.log
    pipeline_graph.dot
    pipeline_graph.pdf
    resources/
    steps/
```

默认会保留：

- `summary.json`
- `execution.log`
- `steps/<step>/result.json`
- `steps/<step>/command.sh`
- `resources/`

`--debug` 会额外输出：

- `case_spec.yaml`
- `pipeline_spec.json`
- `env_profile.json`
- `trace.json`
- `reproduce.sh`

## 环境配置

默认从仓库根目录的 `testpipe.config.yaml` 读取环境。

默认行为：

- 不传 `--env-profile` 时使用 `default_env`
- 仓库默认 `default_env=local`
- `docker`、`ssh` 等扩展环境必须先在配置中启用

示例：

```bash
testpipe run examples/testcases/onnx_git_atc.yaml --env-profile local
testpipe run examples/testcases/onnx_git_atc.yaml --config /path/to/testpipe.config.yaml --env-profile local
```

## 当前设计原则

- `PipelineSpec` 是执行真相源
- `Pipeline` 只是构图 DSL
- 所有副作用统一经过 `ActionRunner`
- 简单断言优先写在 `expected`
- 文档以“当前真实实现”为准，不以未来规划为准

## 文档

入口见 [docs/README.md](/home/wyb/AscendCode/TestPipe/docs/README.md)。

重点文档：

- [总体设计](/home/wyb/AscendCode/TestPipe/docs/architecture/00_总体设计.md)
- [Pipeline Python 实现](/home/wyb/AscendCode/TestPipe/docs/architecture/03_Pipeline_Python实现.md)
- [TestCase YAML 规范](/home/wyb/AscendCode/TestPipe/docs/architecture/04_TestCase_YAML规范.md)
- [Pipeline API](/home/wyb/AscendCode/TestPipe/docs/api/pipeline_api.md)
- [Node API](/home/wyb/AscendCode/TestPipe/docs/api/node_api.md)
- [版本迭代日志](/home/wyb/AscendCode/TestPipe/docs/changelog/README.md)
