# TestCase YAML 规范

## 1. 推荐格式

推荐只使用一种主格式：

```yaml
pipeline:
  name: PipelineName
  nodes:
    nodeA:
      key: value

cases:
  - case_id: case_001
    description: 用例说明
    level: P0
    nodes:
      nodeA:
        key: override
    expected:
      output_key:
        exists: true
```

## 2. 字段说明

- `pipeline.name`：目标 Pipeline
- `pipeline.nodes`：通用节点参数
- `cases[*].nodes`：单 case 覆盖参数
- `expected`：简单结果检查

## 3. 参数规则

节点参数可以同时包含：

- 节点输入
- 节点属性覆盖

执行前会按 `OpSpec` 自动拆分。

## 4. 推荐约束

- 一个 YAML 绑定一个 Pipeline
- 一个文件可以包含多个 case
- 简单断言写在 `expected`
- 不要为已被上游边驱动的输入再手动赋值

## 5. 兼容性

旧格式仍兼容：

- 直接把节点名写在 `pipeline` 下
- 直接把节点名写在 `cases[*]` 下
- `test_case` / `test_suite` 历史格式

但这些都不再推荐继续新增。
