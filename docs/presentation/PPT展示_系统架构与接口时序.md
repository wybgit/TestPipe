# TestPipe PPT展示版

## 系统架构图

可直接使用矢量图:

![PPT系统架构图](assets/ppt_架构图.svg)

### 讲解重点

- 入口统一: `TestCase YAML + CLI`
- 编排核心: `PipelineRegistry + TestEngine`
- 执行主链路: `Pipeline -> TestOp -> OpAPI`
- 结果沉淀: 日志、结果目录、可视化导出

## 接口调用时序图

下面使用 Mermaid 精简版，适合直接贴到支持 Mermaid 的 PPT/Markdown 工具中展示。

```mermaid
sequenceDiagram
    autonumber
    participant U as CLI / 调用方
    participant R as PipelineRegistry
    participant E as TestEngine
    participant P as Pipeline
    participant T as TestOp
    participant A as OpAPI
    participant B as 底层能力

    U->>R: 根据 TestCase 查找 Pipeline
    R-->>E: 返回 Pipeline 实例
    U->>E: 提交输入并启动执行
    E->>P: 构建上下文并驱动 Pipeline
    P->>T: 按依赖顺序执行测试步骤
    T->>A: 调用统一操作接口
    A->>B: 执行命令 / 传输 / SSH / 文件操作
    B-->>A: 返回执行结果
    A-->>T: 返回标准化响应
    T-->>P: 产出中间结果
    P-->>E: 汇总 Pipeline 输出
    E-->>U: 返回测试结果与日志位置
```

### 讲解重点

- 前半段聚焦装配: 查找 Pipeline、创建实例、提交输入
- 中间段聚焦执行: `TestEngine` 驱动 `Pipeline`
- 核心链路聚焦接口调用: `TestOp -> OpAPI -> 底层能力`
- 结果统一回收: 执行结果回到 `TestEngine` 对外输出

### 相关素材

- Mermaid 源文件: `assets/ppt_接口调用时序图.mmd`
- DOT 源文件: `assets/ppt_接口调用时序图.dot`
