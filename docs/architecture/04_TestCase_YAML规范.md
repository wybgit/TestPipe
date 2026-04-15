# 特性04: TestCase YAML 规范

## 1. 当前目标

TestPipe 当前将一个用例文件统一定义为:

- 绑定一个明确的 `Pipeline`
- 在文件头部声明该 Pipeline 的通用节点参数
- 在 `cases` 中声明一个或多个具体用例
- 具体用例只填写差异化节点参数和用例元信息

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
- `pipeline.<NodeName>`: 该节点的通用参数，可同时包含节点输入和属性离线值
- `cases[*].case_id`: 必填，用例唯一标识
- `cases[*].description`: 可选，用例说明
- `cases[*].level`: 可选，用例级别
- `cases[*].<NodeName>`: 可选，用例级节点参数覆盖

---

## 3. 设计约束

### 3.1 顶层约束

- 顶层只保留 `pipeline` 和 `cases`
- 顶层通用参数直接写在 `pipeline` 段
- 单个 case 和多 case 文件使用同一格式

### 3.2 Pipeline 段约束

- `pipeline.name` 必填
- `pipeline` 下除 `name` 外，其余字段都按节点名解释
- 节点参数使用 `k-v` 直接赋值

### 3.3 Cases 段约束

- `case_id` 必填
- `case_id` 是当前 YAML 文件内用例的唯一标识
- 当前推荐的用例元信息仅包含:
  - `description`
  - `level`
- 除元信息外，其余字段都按节点名解释

### 3.4 节点赋值约束

- 节点名必须与 Pipeline 图中的节点名一致
- 参数名必须与该节点 `OpSpec.inputs` 或 `OpSpec.attrs` 中定义的名字一致
- 如果某个字段属于 `inputs`，它表示节点输入
- 如果某个字段属于 `attrs`，它表示在线属性覆盖
- 如果某个输入端口已被上游边驱动，不应在用例中再次赋值
- 已编译进 `NodeSpec.attrs` 的默认属性，可在用例中按同名字段覆盖

---

## 4. 示例

### 4.1 单文件单用例

```yaml
pipeline:
  name: OnnxGitAtcPipeline
  fetchModelNode:
    repo: https://github.com/wybgit/onnx-layer.git
    branch: Abs
    path: Abs_testcase_5a6b43
    model_pattern: "*.onnx"
  compileModelNode:
    env_script: /home/wyb/Ascend/cann-8.5.0/set_env.sh
    soc_version: Ascend310P3
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

## 5. 当前推荐格式

- 文档、示例和真实案例统一使用 `pipeline + cases`
- 用例检查器会对节点名、端口名和覆盖行为做契约校验
## 6. 当前语义落地

归一化后：

- `CaseSpec.inputs` 只保存真正的 Pipeline 输入
- `CaseSpec.inputs_by_node` 保存节点参数
- 节点参数会在执行时按 `OpSpec` 自动拆分为：
  - 节点输入
  - 节点属性在线覆盖
