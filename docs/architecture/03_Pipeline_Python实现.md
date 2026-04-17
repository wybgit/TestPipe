# Pipeline Python 实现

## 1. 当前目标

当前 DSL 只解决一个问题：用最直接的 Python 代码把测试流程写清楚。

推荐标准：

- 代码顺序接近执行顺序
- 绑定关系显式
- 不把 testcase 数据硬编码进 Pipeline

## 2. 最小写法

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

## 3. 推荐写法

### 3.1 按执行顺序写节点

优先写成线性步骤，不要先追求“通用图语法”。

### 3.2 只把真正流动的值定义成输入

例如：

- `model_path` 是输入
- `soc_version` 是属性

### 3.3 简单断言不要塞进 Pipeline

像“文件存在”这类检查，优先写在 testcase 的 `expected`。

## 4. 当前 API

常用的只有：

- `set_stage()`
- `add_node()`
- `add_output()`
- `add_input()`，仅在确实需要流程级输入时使用

`connect()` 和 `add_step()` 保留兼容，但不是主写法。
