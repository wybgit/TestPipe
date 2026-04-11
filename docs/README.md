# TestPipe测试框架 - 设计文档索引

## 框架命名

**TestPipe** = **Test Pipeline** (测试管道)

- **Test** - 测试领域
- **Pipe** - 管道化编排,体现测试流程的串联执行
- 简单易记,读音顺口

---

## 核心概念

- **测试算子(TestOp)** - 测试步骤的抽象,类似AI算子
- **Pipeline** - 测试流程,用Python代码定义(类似PyTorch的nn.Module)
- **TestCase** - 测试用例,包含具体测试数据,用YAML描述
- **测试引擎(TestEngine)** - 执行Pipeline的引擎

---

## 设计文档

### Phase 1 (MVP) - 核心框架

| 文档 | 特性 | 状态 | 工作量 |
|------|------|------|--------|
| [00_总体设计.md](00_总体设计.md) | 框架总体架构 | ✅ 已完成 | - |
| [01_测试算子框架.md](01_测试算子框架.md) | TestOp基类、注册机制、统一API | ✅ 已完成 | 3-4天 |
| [02_Pipeline引擎.md](02_测试图引擎.md) | Pipeline、拓扑排序、执行引擎 | ✅ 已完成 | 3-4天 |
| [03_Pipeline_Python实现.md](03_Pipeline_Python实现.md) | Pipeline Python实现(类似PyTorch) | ✅ 已完成 | 2-3天 |
| [04_TestCase_YAML规范.md](04_TestCase_YAML规范.md) | TestCase YAML规范,参数化测试 | ✅ 已完成 | 2天 |
| [05_Pipeline可视化导出.md](05_Pipeline可视化导出.md) | ONNX和DOT图导出 | ✅ 已完成 | 2天 |

### Phase 2 - 功能完善

| 文档 | 特性 | 状态 | 工作量 |
|------|------|------|--------|
| [06_文档自动生成.md](06_文档自动生成.md) | API和算子文档自动生成 | ✅ 已完成 | 2-3天 |

### 设计评审

| 文档 | 内容 | 状态 |
|------|------|------|
| [07_架构优化建议.md](07_架构优化建议.md) | 基于需求和现有设计的架构优化建议 | ✅ 已完成 |

### 用户指南

| 文档 | 内容 | 状态 |
|------|------|------|
| [用户指南_平台使用.md](用户指南_平台使用.md) | 平台使用方法、CLI命令、内置算子 | ✅ 已完成 |

### 开发指南

| 文档 | 内容 | 状态 |
|------|------|------|
| [开发指南_自定义测试算子.md](开发指南_自定义测试算子.md) | 自定义测试算子开发说明 | ✅ 已完成 |
| [开发指南_自定义API.md](开发指南_自定义API.md) | 自定义API开发说明 | ✅ 已完成 |

### 架构图

| 图表 | 内容 | 格式 | 状态 |
|------|------|------|------|
| [架构图](architecture.png) | 系统架构图 | DOT/PNG | ✅ 已完成 |
| [时序图](sequence.png) | 测试执行时序图 | DOT/PNG | ✅ 已完成 |
| [图表说明](图表说明.md) | DOT源文件和使用说明 | - | ✅ 已完成 |

---

## 术语对照

| TestPipe术语 | 说明 | 对应AI编译器概念 |
|-------------|------|------------------|
| TestOp | 测试算子 | Operator |
| Pipeline | 测试管道 | Computation Graph |
| TestCase | 测试用例 | Input Tensor |
| TestEngine | 测试引擎 | Runtime |
| Node | 测试节点 | Graph Node |
| Op_Type | 算子类型 | Op Type |

---

## 快速导航

### 我想了解TestPipe
→ 阅读 [00_总体设计.md](00_总体设计.md)  
→ 查看 [架构图](architecture.png)

### 我想使用TestPipe
→ 阅读 [用户指南_平台使用.md](用户指南_平台使用.md)

### 我想开发自定义算子
→ 阅读 [开发指南_自定义测试算子.md](开发指南_自定义测试算子.md)

### 我想扩展API
→ 阅读 [开发指南_自定义API.md](开发指南_自定义API.md)

### 我想了解Pipeline实现
→ 阅读 [03_Pipeline_Python实现.md](03_Pipeline_Python实现.md)

### 我想了解TestCase格式
→ 阅读 [04_TestCase_YAML规范.md](04_TestCase_YAML规范.md)

### 我想了解执行流程
→ 查看 [时序图](sequence.png)

---

## 核心特性

### ✅ Pipeline Python实现
- 类似PyTorch的nn.Module
- 代码即配置,IDE支持
- 灵活组合,支持if/for/函数
- 自动注册为内置Pipeline

### ✅ TestCase YAML格式
- 引用Python定义的Pipeline
- 支持参数化测试
- 多Pipeline共享输入
- 结果按TestCase维度保存

### ✅ 算子可调用
- 算子支持__call__
- 像函数一样使用
- 自动处理输入输出

### ✅ 可视化
- 导出ONNX模型(Netron查看)
- 导出DOT图(Graphviz渲染)

### ✅ 文档自动生成
- API文档自动生成
- 算子文档自动生成
- Web展示

---

**文档版本**: v3.0
- **创建日期**: 2026-04-11
- **最后更新**: 2026-04-11
- **维护团队**: TestPipe设计团队
