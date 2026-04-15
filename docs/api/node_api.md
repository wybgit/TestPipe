# Node API

本文档说明 TestPipe 中“节点”相关的 Authoring API 和静态 Spec 模型。

## 1. 概念边界

当前框架里和节点相关的对象分两层：

- Authoring 层：开发者在 `Pipeline.define()` 中使用的节点引用对象。
- Spec 层：编译后写入 `PipelineSpec` 的节点与连线描述。

源码位置：

- `testpipe/core/pipeline.py`
- `testpipe/spec/models.py`

## 2. Authoring API

### 2.1 `NodeHandle`

`NodeHandle` 是 `add_node()` 的返回值，用于在后续节点或输出中引用当前节点的某个输出端口。

```python
@dataclass(slots=True)
class NodeHandle:
    name: str

    def output(self, port_name: str) -> NodeOutputRef:
        return NodeOutputRef(node_name=self.name, output_name=port_name)
```

#### 方法

##### `output(port_name: str) -> NodeOutputRef`

返回一个节点输出引用，用来绑定下游输入或 Pipeline 输出。

示例：

```python
compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(),
    inputs={"model_path": fetch_model.output("model_path")},
)
```

### 2.2 `NodeOutputRef`

`NodeOutputRef` 表示“某个节点的某个输出端口”。

```python
@dataclass(slots=True)
class NodeOutputRef:
    node_name: str
    output_name: str
```

使用场景：

- 作为 `add_node(..., inputs=...)` 的输入来源。
- 作为 `add_output(name, source=...)` 的输出来源。

### 2.3 `NodeDefinition`

`NodeDefinition` 是 DSL 在内存中的中间结构，表示开发者声明的一个节点。

```python
@dataclass(slots=True)
class NodeDefinition:
    name: str
    op: object
    stage: str | None = None
    inputs: dict[str, PipelineInputRef | NodeOutputRef] = field(default_factory=dict)
```

字段说明：

- `name`：节点名，在同一个 Pipeline 内应保持唯一。
- `op`：算子实例，例如 `ResourceFetchOp()`。
- `stage`：节点所属阶段，用于分组和可视化。
- `inputs`：输入端口到来源引用的映射。

## 3. 节点输入来源

节点输入只支持两类来源：

- `PipelineInputRef`
- `NodeOutputRef`

也就是说，代码描述上是“从 Pipeline 输入取值”或“从上游节点输出取值”。

示例：

```python
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())

compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(),
    inputs={"model_path": fetch_model.output("model_path")},
)
```

说明：

- 如果某个参数只属于单个节点，例如 `fetchModelNode.repo`，推荐直接在 testcase 里写到该节点下，不需要强行提升成 Pipeline 输入。
- 只有需要在图层面流转、复用或统一校验的参数，才建议通过 `add_input()` 提升为 Pipeline 输入。
- 算子属性不走图输入绑定。属性通常在算子构造时提供离线默认值，也可以在 testcase 的 `inputs_by_node.<node>` 下按同名字段做在线覆盖。

## 4. 节点 Spec 模型

### 4.1 `NodeSpec`

`NodeSpec` 是编译后进入 `PipelineSpec` 的节点定义。

```python
@dataclass(slots=True)
class NodeSpec:
    name: str
    op_name: str
    op_version: str | None = None
    stage: str | None = None
    attrs: dict[str, Any] = field(default_factory=dict)
    input_bindings: list["InputBindingSpec"] = field(default_factory=list)
```

字段说明：

- `name`：节点实例名。
- `op_name`：注册表中的算子名。
- `op_version`：算子版本。
- `stage`：阶段名。
- `attrs`：节点构造时传入的算子属性。
- `input_bindings`：输入绑定列表。

### 4.2 `InputBindingSpec`

`InputBindingSpec` 描述节点某个输入端口如何取值。

```python
@dataclass(slots=True)
class InputBindingSpec:
    target_port: str
    source_type: str
    source_name: str
    source_port: str | None = None
```

典型取值：

- `source_type="pipeline_input"`：来源于 Pipeline 输入。
- `source_type="node_output"`：来源于某个上游节点输出。

### 4.3 `EdgeSpec`

`EdgeSpec` 只描述节点到节点之间的显式边。

```python
@dataclass(slots=True)
class EdgeSpec:
    source_node: str
    source_port: str
    target_node: str
    target_port: str
```

说明：

- Pipeline 输入到节点的绑定不会进入 `EdgeSpec`。
- `EdgeSpec` 主要服务于执行规划、可视化与导出。

## 5. 推荐写法

### 5.1 串行描述节点

优先使用“上一个节点输出作为下一个节点输入”的形式，让 Pipeline 代码天然反映构图顺序。

```python
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())
compile_model = self.add_node("compileModelNode", ATCCompileOp(), inputs={"model_path": fetch_model.output("model_path")})
check_om = self.add_node("checkOmExistsNode", PathExistsOp(), inputs={"target_path": compile_model.output("om_path")})
```

### 5.2 用节点名表达业务动作

建议节点名直接体现动作，例如：

- `fetchModelNode`
- `compileModelNode`
- `checkOmExistsNode`

避免使用无语义的 `node1`、`step_a`。

## 6. 常见问题

### 节点本身能直接暴露输出吗

不能。必须通过 `NodeHandle.output("port_name")` 生成 `NodeOutputRef` 后再绑定。

### 节点可以跨阶段引用吗

可以。`stage` 只影响分组和展示，不影响引用能力。

### 节点输入能直接写常量吗

当前 DSL 入口不直接支持在 `add_node()` 中把常量作为输入来源写入图绑定。常量通常通过：

- Pipeline 输入传入
- 或 Case 的 `inputs_by_node` 在执行时补充

### 节点属性放在哪里

节点属性放在算子构造参数里，例如：

```python
ATCCompileOp(output_name="model.om", timeout=600)
```

这类值会编译进 `NodeSpec.attrs` 作为离线默认值。若 testcase 里存在同名 `inputs_by_node.<node>.<attr>`，执行时会覆盖该默认值，作为在线属性生效。

## 7. 参考

- [Pipeline API](pipeline_api.md)
- [Pipeline Python 实现](../architecture/03_Pipeline_Python实现.md)
