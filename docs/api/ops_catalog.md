# 内置算子 API

本文档由 `scripts/generate_api_docs.py` 基于当前注册表自动生成。

当前内置算子数量：`5`

## ATCCompile

- 类名：`ATCCompileOp`
- 分组：`atc.compile`
- 版本：`1.0`
- 源码：`testpipe/ops/atc/compile.py`

Compile a model into a local OM artifact

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | yes | - | workspace model path |
| soc_version | string | no | yes | - | target soc version |
| atc_options | object | no | yes | - | extra atc options |
| env_script | string | no | yes | - | cann env script |
| output_name | string | no | yes | - | output om filename or prefix |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| om_path | artifact:path | yes | yes | - | compiled om path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| output_name | string | no | compiled_model.om | - | compiled output filename |
| timeout | int | no | 30 | - | command timeout |
| framework | int | no | 5 | - | atc framework id |

## EnvCheck

- 类名：`EnvCheckOp`
- 分组：`builtin`
- 版本：`1.0`
- 源码：`testpipe/ops/builtin.py`

Validate that the configured CANN environment script exists

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| env_script | string | no | yes | - | cann environment script path |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| env_ready | bool | yes | no | - | environment readiness flag |
| env_script | string | yes | no | - | validated cann environment script path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | 无 |

## PathExists

- 类名：`PathExistsOp`
- 分组：`assertions`
- 版本：`1.0`
- 源码：`testpipe/ops/assertions.py`

Check whether a local file or directory exists

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| target_path | artifact:path | yes | yes | - | path to inspect |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| path_exists | bool | yes | yes | - | path existence result |
| checked_path | artifact:path | yes | no | - | normalized checked path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | 无 |

## ResourceFetch

- 类名：`ResourceFetchOp`
- 分组：`resource.fetch`
- 版本：`1.0`
- 源码：`testpipe/ops/resource/fetch.py`

Fetch a local or git-backed resource into the execution workspace

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| resource_path | artifact:path | no | yes | - | source resource path |
| resource_ref | object | no | yes | - | structured resource reference |
| repo | string | no | yes | - | git repository url or local git repo path |
| path | string | no | yes | - | git repository file or directory path |
| ref | string | no | yes | - | git ref, branch, tag, or commit |
| model_pattern | string | no | yes | - | model discovery pattern under a directory |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| model_path | artifact:path | yes | yes | - | workspace-local model path |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | 无 |

## ValueCompare

- 类名：`ValueCompareOp`
- 分组：`assertions`
- 版本：`1.0`
- 源码：`testpipe/ops/assertions.py`

Compare an actual value against an expected value using a configured operator

### Inputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| actual_value | any | yes | yes | - | actual value to compare |
| expected_value | any | no | yes | - | expected comparison value |
| operator | string | no | yes | - | comparison operator |

### Outputs

| Name | Type | Required | Expose | Default | Description |
| --- | --- | --- | --- | --- | --- |
| test_passed | bool | yes | yes | - | comparison result |
| comparison_detail | string | yes | no | - | comparison detail |

### Attrs

| Name | Type | Required | Default | Enum | Description |
| --- | --- | --- | --- | --- | --- |
| operator | string | no | eq | ["eq", "ne", "gt", "ge", "lt", "le"] | comparison operator |
| expected_value | any | yes | - | - | expected comparison value |
