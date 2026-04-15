# Pipeline 可视化导出

本文档描述当前 TestPipe 已经实现的 Pipeline 图导出能力。

## 1. 当前支持范围

当前框架只支持基于 `PipelineSpec + CaseSpec` 导出：

- `.dot`
- `.pdf`，默认在本机存在 `dot` 命令时自动生成

不再维护旧设计中的 ONNX 导图能力。

## 2. 导出入口

### 2.1 执行 testcase 时自动导出

执行 `testpipe run ...` 后，每个 run 目录默认会产出：

- `pipeline_graph.dot`
- `pipeline_graph.pdf`

示例：

```text
runs/
  onnx_git_atc_case_YYYYMMDD_HHMMSS/
    pipeline_graph.dot
    pipeline_graph.pdf
    summary.json
    steps/
```

### 2.2 手动导出

也可以直接使用 CLI：

```bash
testpipe export-pipeline-graph examples/testcases/onnx_git_atc.yaml --output-dir exports --json
```

返回结果会包含：

- `dot_path`
- `pdf_path`

对应实现位于 [exporter.py](/home/wyb/AscendCode/TestPipe/testpipe/graph/exporter.py)。

## 3. 当前导图规则

图导出遵循下面的展示原则：

- 流向固定为从上到下，即 `rankdir=TB`。
- 输入、节点、输出分别使用不同配色。
- 节点主体显示：节点名、算子名、以及 IBO 信息。
- 输入参数直接显示在图里，便于复盘实际执行值。
- 只显示真正有值的可选输入；可选输入未传时不出现在图上。
- 节点内过长路径会按固定宽度自动换行，避免节点被路径撑得过宽。
- `input/output` 不做复杂包裹，尽量保持和参考图一致的简洁风格。

## 4. 输入展示策略

当前图里有两类输入来源：

### 4.1 Pipeline 输入

如果某个参数通过 `add_input()` 挂在 Pipeline 上，并且 testcase 给了值，就会显示成单独的输入节点。

例如：

- `soc_version`
- `atc_options`
- `output_name`

### 4.2 节点直输参数

如果某个参数没有提升成 Pipeline 输入，而是直接写在 testcase 的节点配置下，就会显示为该节点专属输入块。

例如 `OnnxGitAtcPipeline` 中的：

- `envCheckNode.env_script`
- `fetchModelNode.repo`
- `fetchModelNode.ref`
- `fetchModelNode.path`
- `fetchModelNode.model_pattern`

这也是当前推荐方式：只被单个节点消费的参数，不必强行提升成 Pipeline 输入。

## 5. 导图内容来源

导图不是直接读 Python 代码，而是综合下面三部分构建：

1. `PipelineSpec`
2. `CaseSpec`
3. 节点执行输出和 pipeline 最终输出

因此导出的图既能表达静态结构，也能把 testcase 中的真实输入和运行结果填进去。

## 6. OnnxGitAtcPipeline 的当前图逻辑

`OnnxGitAtcPipeline` 导图时会表现为：

1. `envCheckNode` 接受 `env_script`
2. `fetchModelNode` 接受 Git 资源参数
3. `compileModelNode` 接收：
   - 来自 `fetchModelNode` 的 `model_path`
   - 来自 Pipeline 的 `soc_version / atc_options / output_name`
   - 来自 `envCheckNode` 的 `env_script`
4. `checkOmExistsNode` 接收 `compileModelNode.om_path`
5. 输出 `model_path / om_path / path_exists`

## 7. 相关源码

- [graph/exporter.py](/home/wyb/AscendCode/TestPipe/testpipe/graph/exporter.py)
- [test_engine.py](/home/wyb/AscendCode/TestPipe/testpipe/engine/test_engine.py)
- [compile.py](/home/wyb/AscendCode/TestPipe/testpipe/pipelines/atc/compile.py)

## 8. 相关文档

- [总体设计](00_总体设计.md)
- [Pipeline Python 实现](03_Pipeline_Python实现.md)
- [框架架构图](06_框架架构图.md)
- [软件时序调用图](09_软件时序调用图.md)
