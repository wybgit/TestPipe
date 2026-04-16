# TestPipe Agent Skills

`skills/` 目录用于给 `OpenCode`、`Claude Code` 这类 AI 代码开发工具提供可直接参考的 agent skill 资产。

当前仓库已经不再保留框架内部的 `testpipe/skills` 运行时目录，`skills/` 就是唯一保留的 skill 资产入口。

当前内置 4 个 agent skill:

1. `test_node`: 新增或重构测试 Node / TestOp
2. `test_pipeline`: 新增或重构测试 Pipeline
3. `test_case_generation`: 生成或整理测试用例
4. `test_result_analysis`: 分析测试结果并给出定位建议

其中需要修改框架代码的 skill 已附带模板和辅助脚本:

- `skills/test_node/scripts/generate_scaffold.py`
- `skills/test_pipeline/scripts/generate_scaffold.py`

目录组织原则:

- 每个 skill 自包含 `SKILL.md`
- 每个 skill 自包含 `templates/`
- 需要生成代码的 skill 自包含 `scripts/`
- `examples/` 只放该 skill 自己的 request 示例

推荐工作方式:

1. 让 AI agent 先读取对应 skill 目录下的 `SKILL.md`
2. 用 `templates/request.template.yaml` 生成本次任务的 request 文件
3. 对于代码生成类任务，直接运行同目录下的辅助脚本输出骨架
4. 再让 AI agent 在骨架基础上补全实现、测试和文档

范围说明:

- 本目录只提供给 AI 代码工具参考的 skill 资产
- 当前 `testpipe` CLI 不再提供内置 skill 调度指令
- 外部 agent 可以按需要调用已有 `testpipe` 常规命令完成校验，例如 `check-case`、`run`、`python -m unittest`

技能目录总表见 [catalog.yaml](catalog.yaml)。
