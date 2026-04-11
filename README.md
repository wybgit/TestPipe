# TestPipe

TestPipe 是一个基于 Pipeline 的测试编排框架，当前已打通最小主链路:

- `YAML Case -> PipelineSpec -> TestEngine -> runs/`
- 本机 Host 执行
- step 级日志、`trace.json`、`summary.json`、`reproduce.sh`

## 快速上手

### 1. 环境要求

- Python `3.11+`

### 2. 安装

在仓库根目录执行:

```bash
pip install -e .
```

### 3. 查看内置 Pipeline

```bash
testpipe list-pipelines
```

当前最小示例会返回:

```text
SmokePipeline
```

### 4. 运行示例用例

```bash
testpipe run examples/testcases/smoke.yaml
```

预期输出类似:

```json
{
  "case_id": "smoke_case",
  "pipeline": "SmokePipeline",
  "status": "passed",
  "outputs": {
    "echoed_message": "hello testpipe"
  }
}
```

### 5. 查看运行结果

执行完成后，会在 `runs/` 下生成独立目录，包含:

- `case_spec.yaml`
- `pipeline_spec.json`
- `summary.json`
- `trace.json`
- `reproduce.sh`
- `steps/<step>/step.json`

典型结构:

```text
runs/
  smoke_case_YYYYMMDD_HHMMSS/
    case_spec.yaml
    pipeline_spec.json
    env_profile.json
    summary.json
    trace.json
    reproduce.sh
    steps/
```

### 6. 示例用例内容

示例文件在 [smoke.yaml](/home/wyb/AscendCode/TestPipe/examples/testcases/smoke.yaml):

```yaml
test_case:
  case_id: smoke_case
  name: SmokePipeline_Basic
  pipeline: SmokePipeline
  inputs:
    message: "hello testpipe"
  expected:
    echoed_message: "hello testpipe"
```

## 当前实现范围

当前代码骨架已经具备:

- `Spec` 模型
- `Pipeline` DSL 与编译器
- `TestEngine`
- `ActionRunner`
- `TraceRecorder`
- `ArtifactStore`
- 内置 smoke pipeline 和基础测试

当前尚未完整接入:

- Device 执行
- SSH / SFTP / NFS
- 复杂业务算子
- LLM Template Registry / Skill Registry 代码实现

## 常用命令

```bash
# 运行单个用例
testpipe run examples/testcases/smoke.yaml

# 列出已注册 Pipeline
testpipe list-pipelines

# 运行测试
python3 -m unittest discover -s tests -v
```

## 文档入口

完整设计文档见 [docs/README.md](/home/wyb/AscendCode/TestPipe/docs/README.md)。

重点推荐:

- [软件需求说明书](/home/wyb/AscendCode/TestPipe/docs/requirements/02_软件需求说明书.md)
- [核心对象模型设计](/home/wyb/AscendCode/TestPipe/docs/architecture/07_核心对象模型设计.md)
- [执行与追踪机制设计](/home/wyb/AscendCode/TestPipe/docs/architecture/08_执行与追踪机制设计.md)
- [LLM 原生模板与 Skills 设计](/home/wyb/AscendCode/TestPipe/docs/architecture/09_LLM原生模板与Skills设计.md)
