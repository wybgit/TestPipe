# API 文档

这一组文档面向 Pipeline 作者和框架开发者，描述当前 TestPipe 中最稳定的 DSL 与静态模型接口。

## 入口

- [内置算子 API](ops_catalog.md)
- [内置 Pipeline API](pipelines_catalog.md)
- [Node API](node_api.md)
- [Pipeline API](pipeline_api.md)

## 对应源码

- `testpipe/core/pipeline.py`
- `testpipe/spec/models.py`
- `testpipe/core/compiler.py`
- `testpipe/pipelines/atc/compile.py`

## 阅读建议

1. 先看 [Pipeline API](pipeline_api.md)，理解 DSL 入口。
2. 再看 [Node API](node_api.md)，理解节点引用和绑定方式。
3. 然后看 [内置算子 API](ops_catalog.md) 和 [内置 Pipeline API](pipelines_catalog.md)，确认当前真实参数定义。
4. 最后结合 [Pipeline Python 实现](../architecture/03_Pipeline_Python实现.md) 看完整示例。

## 当前接口规则

- `Node.inputs` 只描述图上的输入绑定，来源只能是 Pipeline 输入或上游节点输出。
- `Node.attrs` 描述节点离线默认属性。
- testcase 中的 `inputs_by_node` 会在执行前按 `OpSpec` 自动拆分为节点输入和属性在线覆盖。
