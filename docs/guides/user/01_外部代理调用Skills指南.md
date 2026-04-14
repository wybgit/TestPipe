# 外部代理调用 Skills 指南

## 1. 目标

本文档说明如何让 `OpenCode`、`Claude Code` 等外部代理间接调用 TestPipe 内置 skills。

框架边界如下:

- TestPipe 只承载内置 skills、模板、校验、执行和结果分析
- 外部代理负责理解需求、补全模板、决定调用顺序
- 框架内不直接承载大模型推理调用

---

## 2. 推荐调用模式

推荐采用以下稳定链路:

1. 用 `testpipe show-template <name>` 导出模板骨架
2. 外部代理补全 YAML 文件
3. 调用 `testpipe run-skill ... --json`
4. 消费 JSON 结构化结果
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
- 输入统一落成 YAML 或 JSON 文件
- 输出统一使用 `--json`
- 生成结果先检查再执行
- 执行环境通过 `testpipe.config.yaml` 和 `env_profile` 选择

---

## 4. 推荐命令

### 4.1 导出模板骨架

```bash
testpipe show-template case-template > agent_inputs/generate_case.yaml
testpipe show-template case-check-template > agent_inputs/check_case.yaml
testpipe show-template run-template > agent_inputs/run_case.yaml
```

### 4.2 生成用例

```bash
testpipe run-skill case-generator agent_inputs/generate_case.yaml --json
```

### 4.3 检查用例

```bash
testpipe run-skill case-checker agent_inputs/check_case.yaml --json
```

### 4.4 生成执行计划或实际执行

```bash
testpipe run-skill case-runner agent_inputs/run_case.yaml --json
```

当 `run_case.yaml` 中 `execute: true` 时会实际执行。

### 4.5 分析结果

```bash
testpipe run-skill result-analyzer agent_inputs/result_analysis.yaml --json
```

---

## 5. 代理侧最小提示约定

可给外部代理如下约束:

```text
你只能通过填写 TestPipe 模板并调用 testpipe run-skill --json 来操作框架。
不要直接假设 skill 输出结构，必须读取 JSON 结果。
生成后的 case 必须先调用 case-checker，再决定是否执行。
执行环境通过 testpipe.config.yaml 中的命名环境选择，不直接内嵌环境配置片段。
```

---

## 6. 推荐目录组织

```text
workspace/
  agent_inputs/
    generate_case.yaml
    check_case.yaml
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
- 真实设备侧能力仍需结合实际案例继续完善
