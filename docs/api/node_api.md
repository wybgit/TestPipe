# Node API

## 1. 当前需要理解的对象

- `NodeHandle`
- `NodeOutputRef`
- `NodeSpec`
- `InputBindingSpec`

## 2. `NodeHandle`

`add_node()` 的返回值，用来引用当前节点的输出。

```python
fetch_model = self.add_node("fetchModelNode", ResourceFetchOp())
compile_model = self.add_node(
    "compileModelNode",
    ATCCompileOp(),
    inputs={"model_path": fetch_model.output("model_path")},
)
```

## 3. 输入来源

节点输入只支持两类来源：

- Pipeline 输入
- 上游节点输出

如果某个值只是当前节点的行为参数，不要把它建成图输入，直接放到节点属性里。

## 4. `NodeSpec`

编译后节点会落到 `NodeSpec`，主要包含：

- `name`
- `op_name`
- `stage`
- `attrs`
- `input_bindings`

## 5. 推荐规则

- 节点名直接表达业务动作
- 输入只保留真正流动的值
- 属性只保留行为参数

## 6. 关于断言节点

简单断言通常不需要单独建节点。

例如“输出路径存在”更推荐写成：

```yaml
expected:
  om_path:
    exists: true
```

只有当校验逻辑需要复用、参与图结构或依赖专门执行环境时，才单独建断言节点。
