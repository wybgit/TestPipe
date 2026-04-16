# Skill: Test Case Generation

## 目标

基于现有 Pipeline 和节点契约，生成符合当前 TestPipe YAML 规范的测试用例。

## 适用场景

- 为已有 Pipeline 补充 smoke / regression / edge case 用例
- 统一整理历史 testcase 到当前规范
- 在真实运行前先做结构化 case 设计

## 先读这些文件

- `docs/architecture/04_TestCase_YAML规范.md`
- `README.md` 中关于 testcase 的约定
- 目标 Pipeline 的 Python 实现和已有 testcase 示例

## 工作流程

1. 复制 `templates/request.template.yaml` 并补充约束。
2. 阅读目标 Pipeline 中每个节点仍需手工赋值的输入。
3. 生成 YAML:
   - `pipeline.name`
   - `pipeline` 段默认节点参数
   - `cases` 段差异化覆盖
4. 如果需要验证，可用现有命令检查:

```bash
testpipe check-case /path/to/testcase.yaml
```

## 产出要求

- 输出结构化 YAML，而不是自然语言清单
- `case_id` 唯一且可读
- case 差异只保留真正变化的节点参数
- 尽量让默认值收敛在 `pipeline` 段

## 验收检查

- 不要为已经由上游边提供的端口重复赋值
- 节点名应与 Pipeline 中的 node name 严格一致
- `expected` 字段只写当前框架真实能消费或检查的内容
