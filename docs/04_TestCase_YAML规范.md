# 特性04: TestCase YAML规范

**阶段**: Phase 1 (MVP)  
**优先级**: P0 (最高)  
**预计工作量**: 2天  
**依赖**: 特性03 (Pipeline JSON规范)

---

## 1. 需求描述

### 1.1 业务需求

TestCase YAML用于定义测试用例,支持:
- **多Pipeline测试** - 一个TestCase可以测试多个Pipeline
- **参数化测试** - 支持参数矩阵,自动生成多个测试实例
- **共享输入** - 多个Pipeline共用一份测试输入数据
- **结果保存** - 以TestCase维度保存测试结果

### 1.2 设计理念

- TestCase是测试的最小单元
- 一个TestCase可以包含多个Pipeline的执行
- 支持参数矩阵,方便批量测试不同配置

---

## 2. TestCase YAML规范

### 2.1 基础结构

```yaml
test_case:
  name: string                    # 测试用例名称
  description: string             # 测试用例描述
  
  # 单Pipeline模式
  pipeline: string                # Pipeline名称
  
  # 或多Pipeline模式
  pipelines:                      # Pipeline列表
    - name: string
      enabled: bool               # 是否启用(可选)
  
  # 测试输入(所有Pipeline共享)
  inputs:
    param1: value1
    param2: value2
  
  # 期望输出(可选)
  expected:
    output1: value1
    output2: condition            # 支持条件表达式
  
  # 元数据
  tags: [tag1, tag2]              # 标签
  priority: P0                    # 优先级
  timeout: 3600                   # 超时(秒)
```

---

## 3. 使用示例

### 3.1 单Pipeline测试

```yaml
# ResNet50 FP16精度测试
test_case:
  name: ResNet50_FP16_Accuracy_Test
  description: 测试ResNet50模型FP16精度转换和推理
  
  pipeline: ATC_E2E_Pipeline
  
  inputs:
    model_source: "models/resnet50.onnx"
    soc_version: "Ascend310P3"
    input_data:
      file: "data/resnet50_input.bin"
      shape: [1, 3, 224, 224]
      dtype: float32
    golden_output:
      file: "data/resnet50_golden.bin"
      shape: [1, 1000]
      dtype: float32
  
  expected:
    test_passed: true
    accuracy_score: ">= 0.99"
  
  tags: [resnet, fp16, accuracy, smoke]
  priority: P0
  timeout: 1800
```

### 3.2 多Pipeline测试

```yaml
# ResNet50多SOC测试
test_case:
  name: ResNet50_Multi_SOC_Test
  description: 在多个SOC上测试ResNet50模型
  
  # 多个Pipeline
  pipelines:
    - name: ATC_E2E_Pipeline
    - name: Performance_Test_Pipeline
    - name: Memory_Test_Pipeline
  
  # 共享输入
  inputs:
    model_source: "models/resnet50.onnx"
    soc_version: "Ascend310P3"
    input_data:
      file: "data/resnet50_input.bin"
      shape: [1, 3, 224, 224]
      dtype: float32
  
  expected:
    test_passed: true
    accuracy_score: ">= 0.99"
    latency_ms: "<= 10"
    memory_mb: "<= 500"
  
  tags: [resnet, multi-soc]
  priority: P1
```

### 3.3 参数化测试

```yaml
# ResNet50参数化测试
test_case:
  name: ResNet50_Parameterized_Test
  description: 测试ResNet50在不同配置下的表现
  
  pipeline: ATC_E2E_Pipeline
  
  # 参数矩阵
  parameters:
    soc_version:
      - "Ascend310P3"
      - "Ascend910B"
    precision:
      - "FP16"
      - "FP32"
    batch_size:
      - 1
      - 4
      - 8
  
  # 基础输入(会被参数覆盖)
  inputs:
    model_source: "models/resnet50.onnx"
    input_data:
      file: "data/resnet50_input.bin"
      shape: [1, 3, 224, 224]
      dtype: float32
  
  expected:
    test_passed: true
  
  tags: [resnet, parameterized]
  priority: P2
```

**说明**: 参数化测试会自动生成 2×2×3 = 12 个测试实例

---

## 4. 参数化测试规则

### 4.1 参数展开

```yaml
parameters:
  soc_version: ["Ascend310P3", "Ascend910B"]
  precision: ["FP16", "FP32"]
```

自动生成4个测试实例:
1. soc_version=Ascend310P3, precision=FP16
2. soc_version=Ascend310P3, precision=FP32
3. soc_version=Ascend910B, precision=FP16
4. soc_version=Ascend910B, precision=FP32

### 4.2 参数组合

```yaml
# 方式1: 笛卡尔积(默认)
parameters:
  soc_version: ["A", "B"]
  precision: ["FP16", "FP32"]
# 生成: A+FP16, A+FP32, B+FP16, B+FP32

# 方式2: 配对组合
parameter_pairs:
  - {soc_version: "Ascend310P3", precision: "FP16"}
  - {soc_version: "Ascend910B", precision: "FP32"}
# 生成: 310P3+FP16, 910B+FP32
```

---

## 5. 测试结果保存

### 5.1 结果目录结构

```
results/
├── ResNet50_FP16_Accuracy_Test/          # TestCase名称
│   ├── metadata.json                     # 测试元数据
│   ├── ATC_E2E_Pipeline/                 # Pipeline结果
│   │   ├── pipeline_result.json
│   │   ├── logs/
│   │   └── artifacts/
│   ├── Performance_Test_Pipeline/
│   │   └── ...
│   └── summary.json                      # 汇总结果
```

### 5.2 结果JSON格式

```json
{
  "test_case_name": "ResNet50_FP16_Accuracy_Test",
  "start_time": "2026-04-11T15:00:00",
  "end_time": "2026-04-11T15:30:00",
  "duration_seconds": 1800,
  "status": "passed",
  "pipelines": [
    {
      "pipeline_name": "ATC_E2E_Pipeline",
      "status": "passed",
      "outputs": {
        "test_passed": true,
        "accuracy_score": 0.995
      }
    }
  ]
}
```

---

## 6. TestCaseLoader实现

```python
import yaml
from pathlib import Path
from typing import List, Dict, Any
from itertools import product

class TestCaseLoader:
    """TestCase加载器"""
    
    def load(self, yaml_path: Path) -> List['TestCase']:
        """
        加载TestCase YAML文件
        
        Returns:
            TestCase列表(参数化测试会返回多个)
        """
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        tc_data = data['test_case']
        
        # 检查是否有参数化
        if 'parameters' in tc_data:
            return self._expand_parameterized(tc_data)
        else:
            return [self._create_testcase(tc_data)]
    
    def _expand_parameterized(self, tc_data: Dict) -> List['TestCase']:
        """展开参数化测试"""
        params = tc_data['parameters']
        
        # 生成参数组合(笛卡尔积)
        param_names = list(params.keys())
        param_values = [params[name] for name in param_names]
        combinations = list(product(*param_values))
        
        # 为每个组合创建TestCase
        testcases = []
        for combo in combinations:
            # 复制基础数据
            instance_data = tc_data.copy()
            
            # 生成实例名称
            param_str = '_'.join([f"{k}={v}" for k, v in zip(param_names, combo)])
            instance_data['name'] = f"{tc_data['name']}_{param_str}"
            
            # 合并参数到inputs
            instance_inputs = instance_data.get('inputs', {}).copy()
            for name, value in zip(param_names, combo):
                instance_inputs[name] = value
            instance_data['inputs'] = instance_inputs
            
            testcases.append(self._create_testcase(instance_data))
        
        return testcases
    
    def _create_testcase(self, tc_data: Dict) -> 'TestCase':
        """创建单个TestCase"""
        # 加载Pipeline
        pipelines = []
        if 'pipeline' in tc_data:
            pipelines = [tc_data['pipeline']]
        elif 'pipelines' in tc_data:
            pipelines = [p['name'] for p in tc_data['pipelines']]
        
        return TestCase(
            name=tc_data['name'],
            description=tc_data.get('description', ''),
            pipelines=pipelines,
            inputs=tc_data.get('inputs', {}),
            expected=tc_data.get('expected', {}),
            tags=tc_data.get('tags', []),
            priority=tc_data.get('priority', 'P2'),
            timeout=tc_data.get('timeout', 3600)
        )


class TestCase:
    """测试用例"""
    
    def __init__(self, name: str, description: str, pipelines: List[str],
                 inputs: Dict[str, Any], expected: Dict[str, Any],
                 tags: list, priority: str, timeout: int):
        self.name = name
        self.description = description
        self.pipelines = pipelines
        self.inputs = inputs
        self.expected = expected
        self.tags = tags
        self.priority = priority
        self.timeout = timeout
```

---

## 7. 验收标准

### 7.1 功能验收

- [ ] 支持单Pipeline测试
- [ ] 支持多Pipeline测试
- [ ] 支持参数化测试(笛卡尔积)
- [ ] 支持参数配对组合
- [ ] 测试结果按TestCase维度保存

### 7.2 易用性验收

- [ ] YAML格式简洁易读
- [ ] 参数化测试易于配置
- [ ] 错误提示清晰

---

**文档版本**: v2.0  
**创建日期**: 2026-04-11  
**负责人**: TestPipe核心团队
