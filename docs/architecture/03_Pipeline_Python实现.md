# Pipeline Python 实现

本文档描述当前 TestPipe 中已经落地的 Pipeline Python DSL 实现。

## 1. 当前实现位置

- `testpipe/core/pipeline.py`
- `testpipe/core/compiler.py`
- `testpipe/pipelines/atc/compile.py`

## 2. 设计目标

当前 Pipeline DSL 解决的是“如何把测试流程写成可读、可编译、可执行、可导图的串行构图代码”。

核心要求：

- 用 Python 直接描述流程。
- 输入、节点、输出都可静态编译。
- 代码顺序尽量等于执行顺序。
- 既支持执行，也支持导出 DOT/PDF 图。

## 3. 核心模型

### 3.1 Authoring 层

- `Pipeline`
- `PipelineInputRef`
- `NodeHandle`
- `NodeOutputRef`
- `NodeDefinition`

### 3.2 Spec 层

- `PipelineSpec`
- `NodeSpec`
- `InputBindingSpec`
- `EdgeSpec`
- `OutputBindingSpec`

Pipeline 作者只直接使用 Authoring API，执行引擎只消费 Spec。

## 4. DSL 入口

当前 Pipeline 的唯一入口是实现 `define()`：

```python
class Pipeline(ABC):
    @abstractmethod
    def define(self) -> None:
        """Define ports, steps, and edges."""
```

在 `define()` 里，通常按下面顺序描述：

1. `add_input()` 定义输入。
2. `set_stage()` 标记阶段。
3. `add_node()` 按执行顺序添加节点。
4. `add_output()` 暴露最终输出。

## 5. 推荐写法

### 5.1 先定义真正需要提升到流程级的输入

如果某个值只是节点属性，优先保留在节点里，通过默认值或 testcase 在线覆盖，不要强行提升成 Pipeline 输入。

### 5.2 再按串行流程定义节点

```python
self.set_stage("prepare")
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

self.set_stage("compile")
compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(output_name="model.om", timeout=600),
    inputs={"model_path": fetch_model.output("model_path")},
)
```

### 5.3 最后定义输出

```python
self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
```

## 6. 当前示例

当前 examples 使用的 Pipeline 是 `OnnxGitAtcPipeline`：

```python
@register_pipeline
class OnnxGitAtcPipeline(Pipeline):
    """Fetch an ONNX model from git resources and compile it into OM through ATC."""

    def define(self) -> None:
        self.set_stage("prepare")
        fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

        self.set_stage("compile")
        compile_model = self.add_node(
            "compileModelNode",
            ATCCompileOp(output_name="model.om", timeout=600),
            inputs={"model_path": fetch_model.output("model_path")},
        )

        self.set_stage("assert")
        check_om_exists = self.add_node(
            "checkOmExistsNode",
            PathExistsOp(),
            inputs={"target_path": compile_model.output("om_path")},
        )

        self.add_output("model_path", fetch_model.output("model_path"), type="artifact:path")
        self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
        self.add_output("path_exists", check_om_exists.output("path_exists"), type="bool")
```

当前推荐的判断标准是：

- 节点输入只保留真正沿图流转的值，例如 `fetchModelNode.repo / branch / path` 与 `compileModelNode.model_path`。
- 节点属性用于默认值或在线覆盖，例如 `fetchModelNode.model_pattern`、`compileModelNode.soc_version / env_script / atc_options / output_name`。

## 7. 编译流程

Python DSL 不直接执行。执行前会先编译成 `PipelineSpec`。

编译后的核心结果包括：

- `inputs`
- `outputs`
- `nodes`
- `edges`
- `output_bindings`

这使得下游能力可以共享统一结构：

- `TestEngine` 执行
- 图导出
- Case 校验
- API 文档生成

## 8. 当前 DSL 的特点

当前 DSL 强调“显式构图”：

- 输入是什么
- 节点是什么
- 节点从哪里取输入
- 最终输出是什么

## 9. 相关文档

- [Pipeline API](../api/pipeline_api.md)
- [Node API](../api/node_api.md)
- [核心对象模型设计](07_核心对象模型设计.md)
