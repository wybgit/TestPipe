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
    artifact_kind: str | None = None,
    default: object | None = None,
) -> PipelineInputRef:
```

作用：

- 向 Pipeline 注册一个输入端口。
- 返回 `PipelineInputRef`，可直接作为节点输入来源。

示例：

```python
target_device = self.add_input("target_device", "string", description="target device name")
timeout_budget = self.add_input("timeout_budget", "int", required=False, description="pipeline-level timeout budget")
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
self.add_node("fetchModelNode", ResourceFetchOp())
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
self.add_node("compileModelNode", ATCCompileOp(), inputs={"model_path": fetch_model.output("model_path")})
```

或

```python
self.add_node("checkOmExistsNode", PathExistsOp(), target_path=compile_model.output("om_path"))
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
self.connect("pipeline_input_name", "someNode.some_input")
```

说明：

- `source` 没有 `.` 时按 Pipeline 输入解释。
- `source` 有 `.` 时按节点输出解释。
- `target` 必须是 `node.port` 形式。
- `connect()` 只适用于节点输入绑定，不用于节点属性赋值。

当前更推荐直接用 `add_node(..., inputs=...)` 写串行代码，只有需要补充连接时再使用 `connect()`。

## 4. 当前推荐编排方式

### 4.1 先声明真正需要提升到 Pipeline 级别的输入

只有“确实要作为图输入流转”的参数才需要 `add_input()`。如果只是某个节点的属性默认值或在线覆盖值，直接放到节点属性里更合适。

### 4.2 再按执行顺序添加节点

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

### 4.3 最后暴露输出

```python
self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
```

### 4.4 区分输入和属性

推荐按下面的规则判断：

- `input`：来自 Pipeline 输入或上游节点输出，并且会在图结构里形成绑定关系。
- `attr`：算子默认行为或默认参数，通常在构造节点时给出离线值，也可以由 testcase 在 `inputs_by_node.<node>` 下做在线覆盖。

因此：

- 不要把节点属性误写成 Pipeline 输入。
- 不要试图用 `connect()` 或 `add_input()` 去绑定节点属性。
- `inputs_by_node` 允许同时写节点输入值和属性覆盖值，执行层会按 `OpSpec` 自动分流。

## 5. 完整示例

下面是当前保留示例 `OnnxGitAtcPipeline` 的简化写法：

```python
@register_pipeline
class OnnxGitAtcPipeline(Pipeline):
    def define(self) -> None:
        self.set_stage("prepare")
        fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

        self.set_stage("compile")
        compile_model = self.add_node(
            "compileModelNode",
            ATCCompileOp(output_name="model.om", timeout=600),
            inputs={"model_path": fetch_model.output("model_path")},
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

- `fetchModelNode` 的输入只有 `repo / branch / path`，`model_pattern` 是节点属性。
- `compileModelNode` 的输入只有 `model_path`，`soc_version / env_script / atc_options / output_name` 都是节点属性。
- 这些属性既可以在 Pipeline 里给离线默认值，也可以在 testcase 的节点参数中做在线覆盖。

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
