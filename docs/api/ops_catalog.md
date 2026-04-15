# 内置算子 API

本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。

当前内置算子数量：`3`

## ATCCompile

- 类名：`ATCCompileOp`
- 分组：`atc.compile`
- 版本：`1.0`
- 源码：`testpipe/ops/atc/compile.py`

Compile a model into a local OM artifact

### Inputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | - | workspace model path |

### Outputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| om_path | artifact:path | yes | - | compiled om path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| output_name | string | no | compiled_model.om | - | compiled output filename |
| soc_version | string | no | Ascend310P3 | - | target soc version |
| atc_options | object | no | - | - | extra atc options |
| env_script | string | no | /home/wyb/Ascend/cann-8.5.0/set_env.sh | - | cann env script |
| timeout | int | no | 30 | - | command timeout |
| framework | int | no | 5 | - | atc framework id |

## PathExists

- 类名：`PathExistsOp`
- 分组：`assertions`
- 版本：`1.0`
- 源码：`testpipe/ops/assertions.py`

Check whether a local file or directory exists

### Inputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| target_path | artifact:path | yes | - | path to inspect |

### Outputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| path_exists | bool | yes | - | path existence result |
| checked_path | artifact:path | yes | - | normalized checked path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | 无 |

## ResourceFetch

- 类名：`ResourceFetchOp`
- 分组：`resource.fetch`
- 版本：`1.0`
- 源码：`testpipe/ops/resource/fetch.py`

Fetch a git repository subpath into the execution workspace and resolve a model file

### Inputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| repo | string | yes | - | git repository url or local git repo path |
| branch | string | yes | - | git branch to fetch |
| path | string | yes | - | git repository file or directory path |

### Outputs

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | - | model file path matched by model_pattern |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| model_pattern | string | no | *.onnx | - | model discovery pattern under the fetched directory |
