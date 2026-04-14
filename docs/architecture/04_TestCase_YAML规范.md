# 特性04: TestCase YAML 规范

## 1. 当前目标

TestPipe 当前将一个用例文件统一定义为:

- 绑定一个明确的 `Pipeline`
- 在文件头部声明该 Pipeline 的通用节点输入
- 在 `cases` 中声明一个或多个具体用例
- 具体用例只填写差异化输入和用例元信息

这样做的目的:

- 单个用例和 testsuite 统一为同一种表达
- 用例填写方式直接对照 Pipeline 图上的节点名
- 通用参数与差异化参数分离，减少重复

---

## 2. 正式结构

```yaml
pipeline:
  name: PipelineName
  NodeName:
    input_a: value_a
    input_b: value_b
cases:
  - case_id: case_001
    description: 用例说明
    level: P0
    NodeName:
      input_b: override_value
```

字段说明:

- `pipeline.name`: 必填，目标 Pipeline 名称
- `pipeline.<NodeName>`: Pipeline 级通用节点输入
- `cases[*].case_id`: 必填，用例唯一标识
- `cases[*].description`: 可选，用例说明
- `cases[*].level`: 可选，用例级别
- `cases[*].<NodeName>`: 可选，用例级节点输入覆盖

---

## 3. 设计约束

### 3.1 顶层约束

- 顶层只保留 `pipeline` 和 `cases`
- 不再要求用户显式写 `globals`
- 单个 case 和多 case 文件使用同一格式

### 3.2 Pipeline 段约束

- `pipeline.name` 必填
- `pipeline` 下除 `name` 外，其余字段都按节点名解释
- 节点参数使用 `k-v` 直接赋值，不再嵌套额外包装层

### 3.3 Cases 段约束

- `case_id` 必填
- `name` 可选，不再要求必须填写
- 当前推荐的用例元信息仅包含:
  - `description`
  - `level`
- 除元信息外，其余字段都按节点名解释

### 3.4 节点赋值约束

- 节点名必须与 Pipeline 图中的节点名一致
- 参数名必须与节点输入端口名一致
- 如果某个输入端口已被上游边驱动，不应在用例中再次赋值

---

## 4. 示例

### 4.1 单文件单用例

```yaml
pipeline:
  name: OnnxGitAtcPipeline
  fetchModelNode:
    repo: https://github.com/wybgit/onnx-layer.git
    path: Abs_testcase_5a6b43
    model_pattern: "*.onnx"
  compileModelNode:
    soc_version: Ascend310P3
    env_script: /home/wyb/Ascend/cann-8.5.0/set_env.sh
  assertOmExistsNode:
    expected_value: true
cases:
  - case_id: onnx_git_atc_case
    description: 验证从 Git 仓获取 ONNX 并成功转换为 OM
    level: P0
```

### 4.2 单文件多用例

```yaml
pipeline:
  name: SmokePipeline
  echo:
    message: hello default
cases:
  - case_id: smoke_default
    description: 使用默认消息
    level: P1
  - case_id: smoke_override
    description: 覆盖消息内容
    level: P1
    echo:
      message: hello override
```

---

## 5. 兼容性说明

- 旧格式 `test_case`、`test_suite`、`testcases` 仍兼容读取
- 新增文档、示例和真实案例一律以 `pipeline + cases` 为准
- 用例检查器会继续对节点名、端口名和覆盖行为做契约校验
