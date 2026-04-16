# 开发指南 - Agent Skills 使用指南

## 1. 目标

`skills/` 目录面向 `OpenCode`、`Claude Code` 这类 AI 代码开发工具，提供一组可直接读取、可直接执行的 agent skill 资产。

当前目标很明确:

- 让每个 skill 自包含自己的说明、模板、示例和脚本
- 让外部 AI 工具不依赖 `testpipe` 内置 skill 调度
- 让 Node、Pipeline、testcase 生成链路可直接落地

## 2. 当前边界

- `testpipe` CLI 已不再保留内置 `skill/template` 调度命令
- `skills/` 是当前仓库唯一保留的 skill 资产目录
- 外部 agent 仍然要靠 TestPipe 原生命令完成校验，例如:
  - `python3 -m unittest discover -s tests -v`
  - `testpipe check-case ...`
  - `testpipe run ...`

## 3. 目录结构

```text
skills/
  README.md
  catalog.yaml
  test_node/
    SKILL.md
    templates/
    examples/
    scripts/
  test_pipeline/
    SKILL.md
    templates/
    examples/
    scripts/
  test_case_generation/
    SKILL.md
    templates/
    examples/
  test_result_analysis/
    SKILL.md
    templates/
    examples/
```

每个 skill 的约束:

- `SKILL.md` 是入口说明
- `templates/request.template.yaml` 是任务模板
- `examples/request.example.yaml` 是示例输入
- `scripts/` 只放该 skill 自己需要的脚手架脚本

## 4. 如何对接到 OpenCode

当前仓库里没有专门的 `opencode` 配置文件，因此推荐用最直接也最稳定的接法: 把 skill 文件路径作为 OpenCode 的任务上下文，让 OpenCode 先读 `SKILL.md`，再按同目录模板和脚本工作。

推荐步骤:

1. 在 OpenCode 中打开当前仓库根目录。
2. 明确告诉 OpenCode 先读取某个 skill 的 `SKILL.md`。
3. 同时提供该 skill 下的 request 模板或你已经填好的 request 文件。
4. 如果该 skill 带脚本，要求 OpenCode 先执行脚本，再补实现。
5. 最后要求 OpenCode 用 TestPipe 原生命令做验证。

推荐提示词骨架:

```text
先阅读 skills/<skill_name>/SKILL.md。
再阅读 skills/<skill_name>/templates/request.template.yaml 和我提供的 request 文件。
如果当前 skill 带 scripts/，先运行对应脚手架脚本生成骨架。
然后只在生成骨架基础上补全实现、测试和文档。
最后运行相关验证命令，不要编造仓库中不存在的接口。
```

如果你希望 OpenCode 直接执行命令，建议在提示中把命令写死，不要只写“生成骨架”这种抽象要求。

## 5. 每个 Skill 如何使用

### 5.1 `test_node`

用途:

- 生成目标测试 Node / `TestOp`
- 生成对应测试骨架
- 生成基础说明文档

主要文件:

- `skills/test_node/SKILL.md`
- `skills/test_node/templates/request.template.yaml`
- `skills/test_node/examples/request.example.yaml`
- `skills/test_node/scripts/generate_scaffold.py`

生成目标 Node 的步骤:

1. 复制 `skills/test_node/templates/request.template.yaml`。
2. 填写 `op_name`、`module_group`、`inputs`、`outputs`、`attrs`、`behavior_summary`。
3. 运行:

```bash
python skills/test_node/scripts/generate_scaffold.py --request /path/to/request.yaml --output-root .
```

4. 让 OpenCode 基于生成结果补全 `execute()`、失败处理、测试和文档。
5. 验证:

```bash
python3 -m unittest discover -s tests -v
python scripts/generate_api_docs.py
```

产物:

- `testpipe/ops/...`
- `tests/test_*_op.py`
- `docs/guides/generated/*_op.md`

推荐给 OpenCode 的指令:

```text
先阅读 skills/test_node/SKILL.md。
再读取我的 request 文件。
先运行 python skills/test_node/scripts/generate_scaffold.py --request <request> --output-root .
然后补全目标 TestOp、测试和文档，并运行 python3 -m unittest discover -s tests -v。
```

### 5.2 `test_pipeline`

用途:

- 生成目标 Pipeline
- 生成示例 testcase
- 生成 Pipeline 编译测试骨架

主要文件:

- `skills/test_pipeline/SKILL.md`
- `skills/test_pipeline/templates/request.template.yaml`
- `skills/test_pipeline/examples/request.example.yaml`
- `skills/test_pipeline/scripts/generate_scaffold.py`

生成目标 Pipeline 的步骤:

1. 复制 `skills/test_pipeline/templates/request.template.yaml`。
2. 填写 `pipeline_name`、`nodes`、`pipeline_inputs`、`pipeline_outputs`、`case_defaults`。
3. 运行:

```bash
python skills/test_pipeline/scripts/generate_scaffold.py --request /path/to/request.yaml --output-root .
```

4. 让 OpenCode 补全节点绑定、导入、示例值和测试。
5. 验证:

```bash
python3 -m unittest discover -s tests -v
testpipe check-case examples/testcases/<generated>.yaml
```

产物:

- `testpipe/pipelines/...`
- `examples/testcases/*.yaml`
- `tests/test_*_pipeline.py`
- `docs/guides/generated/*_pipeline.md`

推荐给 OpenCode 的指令:

```text
先阅读 skills/test_pipeline/SKILL.md。
再读取我的 request 文件。
先运行 python skills/test_pipeline/scripts/generate_scaffold.py --request <request> --output-root .
然后补全目标 Pipeline、示例 testcase 和测试，并运行 check-case 与 unittest。
```

### 5.3 `test_case_generation`

用途:

- 为现有 Pipeline 生成目标测试用例
- 统一整理 testcase YAML

主要文件:

- `skills/test_case_generation/SKILL.md`
- `skills/test_case_generation/templates/request.template.yaml`
- `skills/test_case_generation/examples/request.example.yaml`

生成目标测试用例的步骤:

1. 准备目标 Pipeline 源文件路径。
2. 复制 `skills/test_case_generation/templates/request.template.yaml`。
3. 填写 `pipeline_name`、`pipeline_source`、`shared_defaults`、`case_variants`。
4. 让 OpenCode 直接输出 YAML testcase。
5. 验证:

```bash
testpipe check-case /path/to/testcase.yaml --json
```

产物:

- 一个符合当前 TestPipe 规范的 testcase YAML

推荐给 OpenCode 的指令:

```text
先阅读 skills/test_case_generation/SKILL.md。
再读取目标 Pipeline 源文件和我的 request 文件。
只输出符合 TestPipe 当前规范的 testcase YAML，不要输出伪代码。
生成后再运行 testpipe check-case 做校验。
```

### 5.4 `test_result_analysis`

用途:

- 分析运行失败
- 输出结构化定位报告

主要文件:

- `skills/test_result_analysis/SKILL.md`
- `skills/test_result_analysis/templates/request.template.yaml`
- `skills/test_result_analysis/examples/request.example.yaml`

使用步骤:

1. 提供 `run_dir`、`summary.json`、必要时提供 `execution.log`。
2. 复制 `skills/test_result_analysis/templates/request.template.yaml`。
3. 填写 `focus` 和 `known_context`。
4. 让 OpenCode 输出结构化结论、证据、根因和下一步建议。

推荐给 OpenCode 的指令:

```text
先阅读 skills/test_result_analysis/SKILL.md。
再读取我的 request 文件和对应 run 目录。
输出结构化分析报告，必须区分已确认事实和推断，并指出下一步建议。
```

## 6. 三条典型生成链路

### 6.1 生成目标 Node

1. 填 `skills/test_node/templates/request.template.yaml`
2. 运行 `skills/test_node/scripts/generate_scaffold.py`
3. 让 OpenCode 补 `execute()` 与测试
4. 跑 `unittest`

### 6.2 生成目标 Pipeline

1. 填 `skills/test_pipeline/templates/request.template.yaml`
2. 运行 `skills/test_pipeline/scripts/generate_scaffold.py`
3. 让 OpenCode 补完整的 Pipeline 和示例 case
4. 跑 `unittest` 和 `check-case`

### 6.3 生成目标测试用例

1. 准备目标 Pipeline 源文件
2. 填 `skills/test_case_generation/templates/request.template.yaml`
3. 让 OpenCode 输出 YAML
4. 跑 `testpipe check-case`

## 7. 使用约束

- 优先让 OpenCode 先读 `SKILL.md`
- 代码生成类任务先跑脚手架，再补实现
- request 信息不足时先补上下文，不要让 AI 猜接口
- 验证命令必须显式写进任务说明里
- 如果要生成 Node、Pipeline、testcase，尽量一次只做一类任务
