# Skill: Test Pipeline

## 目标

为 TestPipe 新增或重构一个 `Pipeline`，同时生成示例 testcase 和最小测试骨架。

## 适用场景

- 新增一条测试主链路
- 将多个已有 `TestOp` 编排成标准 Pipeline
- 输出一个可继续完善的 Pipeline 骨架和用例样例

## 先读这些文件

- `docs/api/pipeline_api.md`
- `docs/architecture/03_Pipeline_Python实现.md`
- `docs/architecture/04_TestCase_YAML规范.md`
- `testpipe/core/pipeline.py`
- `testpipe/pipelines/atc/compile.py`

## 工作流程

1. 复制 `templates/request.template.yaml`，补充节点和绑定关系。
2. 先运行当前 skill 自带的脚手架脚本:

```bash
python skills/test_pipeline/scripts/generate_scaffold.py --request /path/to/request.yaml --output-root .
```

3. 让 AI agent 在骨架基础上补齐:
   - 节点编排
   - 节点属性默认值
   - testcase 示例值
   - 需要的导入和包导出
4. 用 `PipelineCompiler`、`check-case` 或实际 testcase 运行做验证。

## OpenCode 调用建议

如果在 `OpenCode` 中使用这个 skill，建议把下面这段作为起始任务说明:

```text
先阅读 skills/test_pipeline/SKILL.md。
再读取 skills/test_pipeline/templates/request.template.yaml 和我提供的 request 文件。
如果 request 已经完整，先运行 skills/test_pipeline/scripts/generate_scaffold.py 生成骨架。
然后补齐 Pipeline、示例 testcase、测试和必要导出，不要改动无关模块。
```

## 产出要求

- 新增或更新 `testpipe/pipelines/...`
- 新增 `examples/testcases/*.yaml` 示例
- 至少一个 `tests/test_*_pipeline.py`

## 验收检查

- Pipeline 类名与文件名可读且稳定
- 节点输入绑定清晰，不混淆 Pipeline 输入与节点输入
- testcase 样例遵循当前 YAML 规范
- 新增 Pipeline 能被测试代码直接导入和编译

## 输出风格

- 优先复用已有 `OnnxGitAtcPipeline` 的编排习惯
- 每个 node 的职责保持单一
- 如果 request 中某个绑定关系不明确，先保留 TODO 注释，不要编造连接
