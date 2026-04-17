# TestPipe 文档

这套文档只描述当前仓库已经落地的实现，不展开未来平台规划。

## 先看什么

建议按这个顺序阅读：

1. [总体设计](architecture/00_总体设计.md)
2. [Pipeline Python 实现](architecture/03_Pipeline_Python实现.md)
3. [TestCase YAML 规范](architecture/04_TestCase_YAML规范.md)
4. [Pipeline API](api/pipeline_api.md)
5. [Node API](api/node_api.md)

## 当前结论

- 当前稳定主线只有 `OnnxGitAtcPipeline`
- Pipeline 默认只保留业务步骤
- 简单结果检查优先写在 `expected`
- 推荐 testcase 主格式是 `pipeline.nodes + cases[*].nodes`
- `PipelineSpec` 是执行、导图和校验的统一输入

## 文档分组

### 架构

- [总体设计](architecture/00_总体设计.md)
- [测试算子框架](architecture/01_测试算子框架.md)
- [测试图引擎](architecture/02_测试图引擎.md)
- [Pipeline Python 实现](architecture/03_Pipeline_Python实现.md)
- [TestCase YAML 规范](architecture/04_TestCase_YAML规范.md)
- [Pipeline 可视化导出](architecture/05_Pipeline可视化导出.md)
- [核心对象模型设计](architecture/07_核心对象模型设计.md)
- [执行与追踪机制设计](architecture/08_执行与追踪机制设计.md)

### API

- [API 总览](api/README.md)
- [Pipeline API](api/pipeline_api.md)
- [Node API](api/node_api.md)
- [内置算子 API](api/ops_catalog.md)
- [内置 Pipeline API](api/pipelines_catalog.md)

### 需求

- [原始需求](requirements/00_原始需求.md)
- [测试场景](requirements/01_测试场景.md)
- [软件需求说明书](requirements/02_软件需求说明书.md)

### 记录

- [版本迭代日志](changelog/README.md)

## 本地预览

```bash
npx docsify-cli serve docs
```
