# Pipeline API

本文档说明当前 TestPipe 的 Pipeline DSL 接口，基于真实实现 `testpipe/core/pipeline.py` 编写。

## 1. 核心类

### `Pipeline`

`Pipeline` 是所有测试流程的编排基类。

```python
class Pipeline(ABC):
    version = "1.0"

    def __init__(self) -> None:
        self.pipeline_name = self.__class__.__name__
        self.description = (self.__doc__ or "").strip()
        self.inputs: list[PortSpec] = []
        self.outputs: list[PortSpec] = []
        self.nodes: list[NodeDefinition] = []
        self.edges: list[EdgeDefinition] = []
        self.output_bindings: list[OutputDefinition] = []
        self.current_stage: str | None = None
        self.define()
```

使用要求：

- 继承 `Pipeline`。
- 实现 `define()`。
- 在 `define()` 中完成输入、节点、输出声明。

## 2. Pipeline 生命周期

### 2.1 定义阶段

开发者编写 `define()`，通过 DSL 构图。

### 2.2 编译阶段

`PipelineCompiler` 把 `Pipeline` 编译为 `PipelineSpec`。

### 2.3 执行阶段

`TestEngine` 消费 `PipelineSpec` 和 `CaseSpec` 执行。

## 3. API 明细

### 3.1 `define()`

```python
@abstractmethod
def define(self) -> None:
    """Define ports, steps, and edges."""
```

这是唯一必须实现的方法。

### 3.2 `add_input()`

```python
def add_input(
    self,
    name: str,
    type: str,
    *,
    required: bool = True,
    description: str = "",
    expose: bool = True,
    artifact_kind: str | None = None,
    default: object | None = None,
) -> PipelineInputRef:
```

作用：

- 向 Pipeline 注册一个输入端口。
- 返回 `PipelineInputRef`，可直接作为节点输入来源。

示例：

```python
soc_version = self.add_input("soc_version", "string", description="target soc version")
output_name = self.add_input("output_name", "string", required=False, description="output om file name")
```

### 3.3 `input_ref()`

```python
def input_ref(self, name: str) -> PipelineInputRef:
```

作用：

- 通过名称获取已声明的 Pipeline 输入引用。
- 当输入在别处已定义，需要重新引用时使用。

### 3.4 `add_output()`

```python
def add_output(
    self,
    name: str,
    source: PipelineInputRef | NodeOutputRef,
    *,
    type: str,
    required: bool = True,
    description: str = "",
    expose: bool = True,
    artifact_kind: str | None = None,
    default: object | None = None,
) -> None:
```

作用：

- 声明 Pipeline 输出端口。
- 把输出端口绑定到某个 Pipeline 输入或节点输出。

示例：

```python
self.add_output(
    "om_path",
    compile_model.output("om_path"),
    type="artifact:path",
    description="compiled om artifact",
)
```

### 3.5 `set_stage()`

```python
def set_stage(self, stage_name: str | None) -> None:
```

作用：

- 设置当前阶段名。
- 后续 `add_node()` 默认使用该阶段名。

示例：

```python
self.set_stage("prepare")
self.add_node("envCheckNode", EnvCheckOp())
```

### 3.6 `add_node()`

```python
def add_node(
    self,
    name: str,
    op: object,
    *,
    inputs: dict[str, PipelineInputRef | NodeOutputRef] | None = None,
    stage: str | None = None,
    **input_sources: PipelineInputRef | NodeOutputRef,
) -> NodeHandle:
```

作用：

- 声明一个节点。
- 绑定输入来源。
- 返回 `NodeHandle`，供后续节点或输出引用。

输入绑定支持两种写法：

```python
self.add_node("compileModelNode", ATCCompileOp(), inputs={"soc_version": soc_version})
```

或

```python
self.add_node("compileModelNode", ATCCompileOp(), soc_version=soc_version)
```

`stage` 优先级：

- 显式传入 `stage=...`
- 否则使用 `set_stage()` 当前值

### 3.7 `add_step()`

```python
def add_step(self, name: str, op: object, *, stage: str | None = None) -> NodeHandle:
```

这是 `add_node()` 的简写，适合没有输入绑定的节点。

### 3.8 `connect()`

```python
def connect(self, source: str, target: str) -> None:
```

作用：

- 用字符串形式补充节点连线。

示例：

```python
self.connect("fetchModelNode.model_path", "compileModelNode.model_path")
self.connect("soc_version", "compileModelNode.soc_version")
```

说明：

- `source` 没有 `.` 时按 Pipeline 输入解释。
- `source` 有 `.` 时按节点输出解释。
- `target` 必须是 `node.port` 形式。

当前更推荐直接用 `add_node(..., inputs=...)` 写串行代码，只有需要补充连接时再使用 `connect()`。

## 4. 当前推荐编排方式

### 4.1 先声明真正需要提升到 Pipeline 级别的输入

```python
soc_version = self.add_input("soc_version", "string")
```

### 4.2 再按执行顺序添加节点

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

### 4.3 最后暴露输出

```python
self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
```

## 5. 完整示例

下面是当前保留示例 `OnnxGitAtcPipeline` 的简化写法：

```python
@register_pipeline
class OnnxGitAtcPipeline(Pipeline):
    def define(self) -> None:
        soc_version = self.add_input("soc_version", "string")
        atc_options = self.add_input("atc_options", "object", required=False)
        output_name = self.add_input("output_name", "string", required=False)

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

        check_om = self.add_node(
            "checkOmExistsNode",
            PathExistsOp(),
            inputs={"target_path": compile_model.output("om_path")},
        )

        self.add_output("model_path", fetch_model.output("model_path"), type="artifact:path")
        self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
        self.add_output("path_exists", check_om.output("path_exists"), type="bool")
```

这里的关键约束是：

- `fetchModelNode` 的 `repo / ref / path / model_pattern` 只服务于当前节点，因此直接作为节点输入由 testcase 注入，不再提升成 Pipeline 输入。
- `soc_version / atc_options / output_name` 会被 `compileModelNode` 消费，且属于流程级参数，因此保留为 Pipeline 输入。

## 6. 编译结果

`PipelineCompiler` 会把 DSL 编译为 `PipelineSpec`，其中包含：

- `inputs`
- `outputs`
- `nodes`
- `edges`
- `output_bindings`

这也是执行引擎、图导出和文档生成使用的统一静态模型。

## 7. 相关接口

- `register_pipeline`
- `create_pipeline`
- `PipelineCompiler`
- `PipelineSpec`

## 8. 参考

- [Node API](node_api.md)
- [Pipeline Python 实现](../architecture/03_Pipeline_Python实现.md)
