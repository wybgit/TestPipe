# TestPipe 文档索引

## 1. 目录结构

```text
docs/
  requirements/     需求与范围
  architecture/     架构与设计细节
  guides/           用户与开发指南
  review/           设计评审与优化建议
  presentation/     PPT 与展示素材
```

---

## 2. 推荐阅读顺序

### 需求侧

1. [原始需求](/home/wyb/AscendCode/TestPipe/docs/requirements/00_原始需求.md)
2. [测试场景](/home/wyb/AscendCode/TestPipe/docs/requirements/01_测试场景.md)
3. [软件需求说明书](/home/wyb/AscendCode/TestPipe/docs/requirements/02_软件需求说明书.md)

### 架构侧

1. [总体设计](/home/wyb/AscendCode/TestPipe/docs/architecture/00_总体设计.md)
2. [测试算子框架](/home/wyb/AscendCode/TestPipe/docs/architecture/01_测试算子框架.md)
3. [测试图引擎](/home/wyb/AscendCode/TestPipe/docs/architecture/02_测试图引擎.md)
4. [Pipeline Python 实现](/home/wyb/AscendCode/TestPipe/docs/architecture/03_Pipeline_Python实现.md)
5. [TestCase YAML 规范](/home/wyb/AscendCode/TestPipe/docs/architecture/04_TestCase_YAML规范.md)
6. [Pipeline 可视化导出](/home/wyb/AscendCode/TestPipe/docs/architecture/05_Pipeline可视化导出.md)
7. [文档自动生成](/home/wyb/AscendCode/TestPipe/docs/architecture/06_文档自动生成.md)
8. [核心对象模型设计](/home/wyb/AscendCode/TestPipe/docs/architecture/07_核心对象模型设计.md)
9. [执行与追踪机制设计](/home/wyb/AscendCode/TestPipe/docs/architecture/08_执行与追踪机制设计.md)

### 指南侧

- [用户指南](/home/wyb/AscendCode/TestPipe/docs/guides/user/用户指南_平台使用.md)
- [开发总览](/home/wyb/AscendCode/TestPipe/docs/guides/developer/00_开发总览.md)
- [自定义测试算子](/home/wyb/AscendCode/TestPipe/docs/guides/developer/01_自定义测试算子.md)
- [自定义 API 与 Action 扩展](/home/wyb/AscendCode/TestPipe/docs/guides/developer/02_自定义API与Action扩展.md)

### 评审与展示

- [架构优化建议](/home/wyb/AscendCode/TestPipe/docs/review/07_架构优化建议.md)
- [PPT 展示版](/home/wyb/AscendCode/TestPipe/docs/presentation/PPT展示_系统架构与接口时序.md)

---

## 3. 当前文档分层说明

### requirements

放需求、边界、测试场景和重构后的软件需求说明，回答“为什么做”和“必须做到什么”。

### architecture

放架构方案、执行模型、导出方式和文档机制，回答“系统应该怎么设计”。

### guides

放用户和开发者视角的操作说明，回答“怎么用”和“怎么扩展”。

### review

放评审意见、风险和优化方向，回答“现有设计哪里需要收敛”。

### presentation

放用于汇报和展示的 PPT 素材、Mermaid、DOT 和图文件。

---

## 4. 维护规则

- 需求变更先改 `requirements`
- 架构方案变更再改 `architecture`
- 对外使用方式和扩展方式变更同步改 `guides`
- 评审结论统一沉淀在 `review`

不要在不同目录中维护相互冲突的两套主模型。

---

## 5. 当前重点结论

- 统一采用“Python DSL 编写 + PipelineSpec 执行”的主路径
- `TestEngine` 是唯一执行入口
- `TestOp` 必须有强类型契约
- 所有外部副作用统一走 Action / Provider 层
- 运行结果必须沉淀到 case 级工作空间
