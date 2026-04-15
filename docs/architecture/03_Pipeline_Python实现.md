# Pipeline Python 实现

本文档描述当前 TestPipe 中已经落地的 Pipeline Python DSL 实现，而不是早期的 `forward()` 风格原型。

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

### 5.1 先定义流程级输入

```python
soc_version = self.add_input("soc_version", "string", description="target soc version")
```

### 5.2 再按串行流程定义节点

```python
self.set_stage("prepare")
env_check = self.add_node("envCheckNode", EnvCheckOp())
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

self.set_stage("compile")
compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(output_name="model.om", timeout=600),
    inputs={
        "model_path": fetch_model.output("model_path"),
        "soc_version": soc_version,
        "env_script": env_check.output("env_script"),
    },
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
        soc_version = self.add_input("soc_version", "string", description="target soc version")
        atc_options = self.add_input("atc_options", "object", required=False, description="extra atc options")
        output_name = self.add_input("output_name", "string", required=False, description="output om file name")

        self.set_stage("prepare")
        env_check = self.add_node("envCheckNode", EnvCheckOp())
        fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

        self.set_stage("compile")
        compile_model = self.add_node(
            "compileModelNode",
            ATCCompileOp(output_name="model.om", timeout=600),
            inputs={
                "model_path": fetch_model.output("model_path"),
                "soc_version": soc_version,
                "atc_options": atc_options,
                "output_name": output_name,
                "env_script": env_check.output("env_script"),
            },
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

- 只被单个节点消费、且更适合贴近资源定义的参数，直接放在节点输入里，例如 `fetchModelNode.repo / ref / path / model_pattern`。
- 需要作为流程公共入口暴露的参数，再定义成 Pipeline 输入，例如 `soc_version / atc_options / output_name`。

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

## 8. 为什么不再使用旧设计

旧文档里的 `forward()` / `op_type` / 自动注册 `_ops` 方案已经不再适用，原因是：

- 不利于静态导出结构。
- 图关系不够明确。
- 与当前按文件夹组织 Op/Pipeline 的实现不一致。
- 会引入与运行时逻辑耦合过深的问题。

当前 DSL 更强调“显式构图”：

- 输入是什么
- 节点是什么
- 节点从哪里取输入
- 最终输出是什么

## 9. 相关文档

- [Pipeline API](../api/pipeline_api.md)
- [Node API](../api/node_api.md)
- [核心对象模型设计](07_核心对象模型设计.md)
