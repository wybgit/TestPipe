# Pipeline 可视化导出

## 1. 当前支持

当前导图基于：

- `PipelineSpec`
- `CaseSpec`
- 运行结果

输出：

- `.dot`
- `.pdf`，当本机存在 `dot` 命令时

## 2. 导出入口

执行时自动导出：

- `pipeline_graph.dot`
- `pipeline_graph.pdf`

也可以手动执行：

```bash
testpipe export-pipeline-graph examples/testcases/onnx_git_atc.yaml --json
```

## 3. 图里会显示什么

- Pipeline 输入
- 节点输入
- 节点属性
- 节点输出
- Pipeline 输出
- 执行后的真实命令

## 4. 当前主线表现

`OnnxGitAtcPipeline` 导图时主要展示：

1. `fetchModelNode` 的 Git 输入
2. `compileModelNode` 的 `model_path` 依赖
3. `compileModelNode` 的 ATC 相关属性
4. 最终输出 `model_path / om_path`

简单断言在 `expected` 中表达，不额外建导图节点。
