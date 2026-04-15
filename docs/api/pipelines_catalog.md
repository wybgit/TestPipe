# 内置 Pipeline API

本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。

当前内置 Pipeline 数量：`1`

## OnnxGitAtcPipeline

- 类名：`OnnxGitAtcPipeline`
- 版本：`1.0`
- 源码：`testpipe/pipelines/atc/compile.py`

Fetch an ONNX model from git resources and compile it into OM through ATC.

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| soc_version | string | yes | yes | - | target soc version |
| atc_options | object | no | yes | - | extra atc options |
| output_name | string | no | yes | - | output om file name |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | yes | - | resolved onnx model path |
| om_path | artifact:path | yes | yes | - | compiled om artifact |
| path_exists | bool | yes | yes | - | compiled om existence |

### Nodes

#### envCheckNode

- `op_name`: `EnvCheck`
- `stage`: `prepare`
- `attrs`: `-`

输入绑定：

- 无


#### fetchModelNode

- `op_name`: `ResourceFetch`
- `stage`: `prepare`
- `attrs`: `-`

输入绑定：

- 无


#### compileModelNode

- `op_name`: `ATCCompile`
- `stage`: `compile`
- `attrs`: `{"framework": 5, "output_name": "model.om", "timeout": 600}`

输入绑定：

- `model_path` <- `fetchModelNode.model_path`
- `soc_version` <- `pipeline.soc_version`
- `atc_options` <- `pipeline.atc_options`
- `output_name` <- `pipeline.output_name`
- `env_script` <- `envCheckNode.env_script`


#### checkOmExistsNode

- `op_name`: `PathExists`
- `stage`: `assert`
- `attrs`: `-`

输入绑定：

- `target_path` <- `compileModelNode.om_path`


### Output Bindings

- `model_path` <- `fetchModelNode.model_path`
- `om_path` <- `compileModelNode.om_path`
- `path_exists` <- `checkOmExistsNode.path_exists`
