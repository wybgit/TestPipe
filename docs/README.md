# TestPipe 文档首页

TestPipe 当前采用统一的 Python DSL + `PipelineSpec` 执行模型。

文档站点面向 Docsify 组织，建议从下面几个入口开始阅读。

## 快速入口

- [内置算子 API](api/ops_catalog.md)
- [内置 Pipeline API](api/pipelines_catalog.md)
- [Node API](api/node_api.md)
- [Pipeline API](api/pipeline_api.md)
- [Agent Skills 使用指南](guides/developer/03_Agent_Skills使用指南.md)
- [Pipeline Python 实现](architecture/03_Pipeline_Python实现.md)
- [Pipeline 可视化导出](architecture/05_Pipeline可视化导出.md)
- [框架架构图](architecture/06_框架架构图.md)
- [软件时序调用图](architecture/09_软件时序调用图.md)
- [TestCase YAML 规范](architecture/04_TestCase_YAML规范.md)

## 当前框架结论

- `testpipe/core/pipeline.py` 是 Pipeline DSL 的唯一实现。
- Pipeline 通过 `define()` 构图，核心 API 是 `add_input`、`add_node`、`add_output`。
- Node 输入来源统一分为 Pipeline 输入或上游节点输出。
- 算子属性与节点输入明确分离：`inputs` 表示图上流转的值，`attrs` 表示算子默认值，可在 testcase 中按节点做在线覆盖。
- `CaseSpec.inputs` 只承载 Pipeline 输入，`CaseSpec.inputs_by_node` 用于节点输入补充和属性在线覆盖。
- 当前示例保留的主流程是 `OnnxGitAtcPipeline`。
- Pipeline 执行和显式导出都支持生成 `.dot` 与 `.pdf` 图。

## 文档目录

### API

- [API 总览](api/README.md)
- [内置算子 API](api/ops_catalog.md)
- [内置 Pipeline API](api/pipelines_catalog.md)
- [Node API](api/node_api.md)
- [Pipeline API](api/pipeline_api.md)

### 架构

- [总体设计](architecture/00_总体设计.md)
- [测试算子框架](architecture/01_测试算子框架.md)
- [测试图引擎](architecture/02_测试图引擎.md)
- [Pipeline Python 实现](architecture/03_Pipeline_Python实现.md)
- [TestCase YAML 规范](architecture/04_TestCase_YAML规范.md)
- [Pipeline 可视化导出](architecture/05_Pipeline可视化导出.md)
- [框架架构图](architecture/06_框架架构图.md)
- [核心对象模型设计](architecture/07_核心对象模型设计.md)
- [执行与追踪机制设计](architecture/08_执行与追踪机制设计.md)
- [软件时序调用图](architecture/09_软件时序调用图.md)

### 开发指南

- [开发总览](guides/developer/00_开发总览.md)
- [自定义测试算子](guides/developer/01_自定义测试算子.md)
- [自定义 API 与 Action 扩展](guides/developer/02_自定义API与Action扩展.md)
- [Agent Skills 使用指南](guides/developer/03_Agent_Skills使用指南.md)

### 需求说明

- [原始需求](requirements/00_原始需求.md)
- [测试场景](requirements/01_测试场景.md)
- [软件需求说明书](requirements/02_软件需求说明书.md)

## Docsify 本地预览

```bash
npx docsify-cli serve docs
```

打开 `http://localhost:3000` 即可预览文档站点。
