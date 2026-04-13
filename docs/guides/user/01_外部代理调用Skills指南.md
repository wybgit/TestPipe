# 外部代理调用 Skills 指南

## 1. 目标

本文档说明如何让 `OpenCode`、`Claude Code` 等外部代理间接调用 TestPipe 内置 skills。

框架边界如下:

- TestPipe 只承载内置 skills、模板、校验、执行和结果分析
- 外部代理负责理解需求、补全模板、决定调用顺序
- 外部代理不直接修改框架内部 skill 实现

---

## 2. 推荐调用模式

推荐采用以下稳定链路:

1. 代理读取模板
2. 代理补全 YAML 模板字段
3. 代理调用 `testpipe run-skill ... --json`
4. 代理消费 JSON 结果
5. 必要时继续调用下一类 skill

典型链路:

```text
User Intent
  -> Agent fills template
  -> testpipe run-skill case-generator
  -> testpipe run-skill case-checker
  -> testpipe run-skill case-runner
  -> testpipe run-skill result-analyzer
```

---

## 3. 推荐约束

- 一次只调用一个 skill
- 输入一律落成 YAML 或 JSON 文件
- 输出一律使用 `--json`
- 生成结果先检查再执行
- 执行时显式指定 `env_profile`

---

## 4. 推荐命令

### 4.1 生成用例

```bash
testpipe run-skill case-generator examples/templates/generate_case_smoke.yaml --json
```

### 4.2 检查用例

```bash
testpipe run-skill case-checker examples/templates/check_case_smoke.yaml --json
```

### 4.3 生成执行计划

```bash
testpipe run-skill case-runner examples/templates/run_case_smoke.yaml --json
```

### 4.4 实际执行

将模板中的 `execute` 改为 `true` 后执行:

```bash
testpipe run-skill case-runner examples/templates/run_case_smoke.yaml --json
```

mock device 场景可直接使用:

```bash
testpipe run-skill case-runner examples/templates/run_case_mock_device.yaml --json
testpipe run-skill case-runner examples/templates/run_case_mock_device_roundtrip.yaml --json
```

### 4.5 分析结果

```bash
testpipe run-skill result-analyzer result_analysis.yaml --json
```

---

## 5. 代理侧最小提示约定

可给外部代理如下约束:

```text
你只能通过填写 TestPipe 模板并调用 testpipe run-skill --json 来操作框架。
不要直接假设 skill 输出结构，必须读取 JSON 结果。
生成后的 case 必须先调用 case-checker，再决定是否执行。
执行时必须显式提供 env_profile。
```

---

## 6. 推荐目录组织

```text
workspace/
  agent_inputs/
    generate_case.yaml
    run_case.yaml
    result_analysis.yaml
  agent_outputs/
    generated_case.json
    run_plan.json
    analysis.json
```

---

## 7. 当前限制

- TestPipe 当前不直接承载大模型调用
- skill 之间的自动编排由外部代理负责
- `EnvProfile` 已支持从 YAML/JSON 加载，但 Device/Transport 的真实执行能力仍在逐步补全
- 当前已支持 mock device 环境下的 `transfer.put -> device.exec -> transfer.get` 闭环验证
