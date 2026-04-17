# API 文档

这里只看当前稳定接口。

## 入口

- [Pipeline API](pipeline_api.md)
- [Node API](node_api.md)
- [内置算子 API](ops_catalog.md)
- [内置 Pipeline API](pipelines_catalog.md)

## 阅读建议

1. 先看 `Pipeline API`
2. 再看 `Node API`
3. 最后看两个 catalog 确认真实参数表

## 当前接口边界

- `Pipeline` 负责构图
- `NodeHandle.output()` 负责引用上游输出
- `TestOp.spec` 定义输入、输出、属性契约
- testcase 中的节点参数会在执行前按 `OpSpec` 自动拆分为输入和属性覆盖
