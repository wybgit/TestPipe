# Skill: Test Node

## 目标

为 TestPipe 新增或重构一个 `TestOp` / 测试节点实现，并同步生成最小测试与开发说明。

## 适用场景

- 需要新增一个可复用测试步骤
- 需要把零散脚本收敛成标准 `TestOp`
- 需要补齐 `OpSpec`、单测骨架和接入说明

## 先读这些文件

- `docs/guides/developer/01_自定义测试算子.md`
- `testpipe/core/test_op.py`
- `testpipe/core/registry.py`
- 目标领域下现有 `testpipe/ops/` 实现

## 工作流程

1. 复制 `templates/request.template.yaml`，按本次任务填写 request。
2. 先运行当前 skill 自带的脚手架脚本:

```bash
python skills/test_node/scripts/generate_scaffold.py --request /path/to/request.yaml --output-root .
```

3. 在生成骨架基础上补齐:
   - `execute()` 真实逻辑
   - 失败路径和边界条件
   - 必要的 trace / artifact / provider 调用
4. 如新增目录包，确认导入路径和 `bootstrap()` 可见性。
5. 运行单测和文档刷新命令。

## OpenCode 调用建议

如果在 `OpenCode` 中使用这个 skill，建议把下面这段作为起始任务说明:

```text
先阅读 skills/test_node/SKILL.md。
再读取 skills/test_node/templates/request.template.yaml 和我提供的 request 文件。
如果 request 已经完整，先运行 skills/test_node/scripts/generate_scaffold.py 生成骨架。
然后只在生成骨架基础上补全实现、测试和文档，不要编造新的框架接口。
```

## 产出要求

- 新增或更新 `testpipe/ops/...`
- 至少一个 `tests/test_*_op.py`
- 如需要，补充开发说明或示例
- 保持 `OpSpec`、实现、文档一致

## 验收检查

- 类名以 `Op` 结尾，可被 `register_op` 注册
- `spec.inputs / outputs / attrs` 完整且描述清晰
- `execute()` 不绕过框架能力直接堆裸命令
- 单测覆盖成功路径和至少一个失败或契约检查场景
- 如接口暴露变化，运行 `python scripts/generate_api_docs.py`

## 输出风格

- 优先复用现有 `testpipe/ops` 风格
- 默认保持单一职责，不把多阶段逻辑塞进一个算子
- 如果脚手架中的 TODO 无法安全补全，明确写出缺口和假设
