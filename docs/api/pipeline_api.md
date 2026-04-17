# Pipeline API

## 1. 目标

`Pipeline` 用来写图，不用来直接执行。

当前推荐只用最少接口把流程写清楚。

## 2. 常用接口

### `set_stage(name)`

给后续节点打阶段标签，主要用于导图和分组。

### `add_node(name, op, inputs=...)`

声明一个节点，并绑定输入来源。

最常见写法：

```python
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())
compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(output_name="model.om", timeout=600),
    inputs={"model_path": fetch_model.output("model_path")},
)
```

### `add_output(name, source, type=...)`

把某个节点输出暴露成 Pipeline 输出。

### `add_input(name, type=...)`

只有当某个值需要作为流程级输入流转时才用。

## 3. 推荐写法

- 按执行顺序写节点
- 优先用 `add_node(..., inputs=...)`
- 简单断言不要建成节点
- 节点属性直接放在 op 构造参数里

## 4. 兼容接口

以下接口仍可用，但不是主写法：

- `connect()`
- `add_step()`
- `input_ref()`

它们保留是为了兼容，不是为了鼓励继续扩张 DSL 面。

## 5. 当前主线示例

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

        self.add_output("model_path", fetch_model.output("model_path"), type="artifact:path")
        self.add_output("om_path", compile_model.output("om_path"), type="artifact:path")
```

结果检查放在 testcase：

```yaml
expected:
  om_path:
    exists: true
```
