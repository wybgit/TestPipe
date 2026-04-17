# 内置 Pipeline API

本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。

当前内置 Pipeline 数量：`1`

## OnnxGitAtcPipeline

- 类名：`OnnxGitAtcPipeline`
- 版本：`1.0`
- 源码：`testpipe/pipelines/atc/compile.py`

Fetch an ONNX model from git resources and compile it into OM through ATC.

### Inputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| - | - | - | - | 无 |

### Outputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | - | resolved onnx model path |
| om_path | artifact:path | yes | - | compiled om artifact |

### Nodes

#### fetchModelNode

- `op_name`: `ResourceFetch`
- `stage`: `prepare`
- `attrs`: `{"model_pattern": "*.onnx"}`

输入绑定：

- 无


#### compileModelNode

- `op_name`: `ATCCompile`
- `stage`: `compile`
- `attrs`: `{"env_script": "/home/wyb/Ascend/cann-8.5.0/set_env.sh", "framework": 5, "output_name": "model.om", "soc_version": "Ascend310P3", "timeout": 600}`

输入绑定：

- `model_path` <- `fetchModelNode.model_path`


### Output Bindings

- `model_path` <- `fetchModelNode.model_path`
- `om_path` <- `compileModelNode.om_path`
