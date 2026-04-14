# Pipeline Python实现方案

---

## 1. 设计理念

### 1.1 类比PyTorch

| PyTorch | TestPipe |
|---------|----------|
| `nn.Module` | `Pipeline` |
| `nn.Conv2d()` | `ATCCompileOp()` |
| `forward()` | `forward()` |
| `model.register_module()` | `pipeline.register_op()` |
| `model.eval()` | `pipeline.run()` |

### 1.2 核心优势

✅ **代码即配置** - 用Python代码定义Pipeline,无需JSON  
✅ **IDE支持** - 代码补全、类型检查、跳转定义  
✅ **灵活组合** - 可以用if/for等控制流  
✅ **易于复用** - 继承、组合、装饰器  
✅ **版本管理** - 代码可以用Git管理  
✅ **内置注册** - 自动注册为框架内置Pipeline

---

## 2. Pipeline基类设计

```python
# testpipe/core/pipeline.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from collections import OrderedDict

class Pipeline(ABC):
    """
    Pipeline基类
    
    类似nn.Module,所有Pipeline必须继承此类
    """
    
    def __init__(self):
        # 存储算子(类似nn.Module._modules)
        self._ops: OrderedDict[str, TestOp] = OrderedDict()
        
        # Pipeline元信息
        self.pipeline_name: str = self.__class__.__name__
        self.pipeline_description: str = self.__doc__ or ""
        
        # 输入输出定义
        self.pipeline_inputs: List[str] = []
        self.pipeline_outputs: List[str] = []
    
    @abstractmethod
    def forward(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        定义Pipeline的执行流程
        
        Args:
            inputs: Pipeline输入字典
            
        Returns:
            Pipeline输出字典
        """
        pass
    
    def __setattr__(self, name: str, value: Any):
        """
        重载属性设置,自动注册TestOp
        
        类似nn.Module.__setattr__
        """
        if isinstance(value, TestOp):
            # 自动注册算子
            self._ops[name] = value
            value.name = name
        
        super().__setattr__(name, value)
    
    def ops(self) -> Dict[str, TestOp]:
        """返回所有算子"""
        return self._ops
    
    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Pipeline
        
        Args:
            inputs: 输入数据
            
        Returns:
            输出结果
        """
        # 创建执行上下文
        context = ExecutionContext(work_dir=Path("/tmp/testpipe"))
        
        # 将inputs放入context
        for key, value in inputs.items():
            context.set(key, value)
        
        # 注入API到所有算子
        api = OpAPI()
        for op in self._ops.values():
            op.api = api
            op.logger = logging.getLogger(f"{self.pipeline_name}.{op.name}")
        
        # 执行forward
        try:
            outputs = self.forward(inputs)
            return outputs
        except Exception as e:
            raise PipelineExecutionError(self.pipeline_name, str(e))
    
    def to_json(self) -> Dict:
        """
        导出为JSON格式(用于可视化)
        
        Returns:
            JSON字典
        """
        nodes = []
        for name, op in self._ops.items():
            nodes.append({
                "Node_Name": name,
                "Op_Type": op.op_type,
                "Inputs": op.inputs,
                "Outputs": op.outputs,
                "Attributes": op.attributes
            })
        
        return {
            "Pipeline_Name": self.pipeline_name,
            "Pipeline_Description": self.pipeline_description,
            "Pipeline_Inputs": self.pipeline_inputs,
            "Pipeline_Outputs": self.pipeline_outputs,
            "Nodes": nodes
        }
    
    def __repr__(self):
        lines = [f"{self.__class__.__name__}("]
        for name, op in self._ops.items():
            lines.append(f"  ({name}): {op.op_type}")
        lines.append(")")
        return "\n".join(lines)
```

---

## 3. Pipeline注册机制

```python
# testpipe/core/pipeline_registry.py
from typing import Dict, Type

class PipelineRegistry:
    """Pipeline注册表"""
    
    _registry: Dict[str, Type[Pipeline]] = {}
    
    @classmethod
    def register(cls, pipeline_class: Type[Pipeline]):
        """注册Pipeline"""
        name = pipeline_class.__name__
        if name in cls._registry:
            raise ValueError(f"Pipeline {name} 已注册")
        
        cls._registry[name] = pipeline_class
        print(f"✓ 注册Pipeline: {name}")
    
    @classmethod
    def get(cls, name: str) -> Type[Pipeline]:
        """获取Pipeline类"""
        if name not in cls._registry:
            raise KeyError(f"未找到Pipeline: {name}")
        return cls._registry[name]
    
    @classmethod
    def list_pipelines(cls) -> List[str]:
        """列出所有Pipeline"""
        return list(cls._registry.keys())
    
    @classmethod
    def create(cls, name: str) -> Pipeline:
        """创建Pipeline实例"""
        pipeline_class = cls.get(name)
        return pipeline_class()


# 装饰器: 自动注册Pipeline
def register_pipeline(pipeline_class: Type[Pipeline]) -> Type[Pipeline]:
    """
    装饰器: 自动注册Pipeline
    
    用法:
        @register_pipeline
        class MyPipeline(Pipeline):
            pass
    """
    PipelineRegistry.register(pipeline_class)
    return pipeline_class
```

---

## 4. 完整示例 - ATC E2E Pipeline

```python
# testpipe/pipelines/atc_e2e_pipeline.py
from testpipe.core import Pipeline, register_pipeline
from testpipe.ops import (
    EnvCheckOp, ModelPrepOp, ATCCompileOp,
    TransferOp, InferenceOp, AccuracyCheckOp
)
from typing import Dict, Any

@register_pipeline
class ATC_E2E_Pipeline(Pipeline):
    """ATC模型转换端到端测试Pipeline"""
    
    def __init__(self):
        super().__init__()
        
        # 定义输入输出
        self.pipeline_inputs = ['model_source', 'soc_version', 'input_data', 'golden_output']
        self.pipeline_outputs = ['test_passed', 'accuracy_score']
        
        # 定义算子(自动注册)
        self.check_env = EnvCheckOp(
            check_items=['python_version', 'atc_tool', 'npu_device'],
            timeout=60
        )
        
        self.prepare_model = ModelPrepOp(
            cache_enabled=True,
            timeout=300
        )
        
        self.compile = ATCCompileOp(
            framework=5,
            output_type='FP16',
            precision_mode='allow_fp32_to_fp16',
            timeout=600
        )
        
        self.transfer = TransferOp(
            transfer_method='auto',
            timeout=300
        )
        
        self.inference = InferenceOp(
            device_id=0,
            timeout=300
        )
        
        self.check_accuracy = AccuracyCheckOp(
            threshold=0.99,
            metrics=['cosine', 'mse'],
            timeout=60
        )
    
    def forward(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """定义执行流程"""
        
        # 1. 检查环境
        env_ready = self.check_env()
        
        # 2. 准备模型
        model_path = self.prepare_model(
            model_source=inputs['model_source']
        )
        
        # 3. 编译模型
        om_path = self.compile(
            model_path=model_path,
            soc_version=inputs['soc_version']
        )
        
        # 4. 传输文件
        remote_om_path, remote_input_path = self.transfer(
            om_path=om_path,
            input_data=inputs['input_data']
        )
        
        # 5. 执行推理
        output_data = self.inference(
            om_path=remote_om_path,
            input_path=remote_input_path
        )
        
        # 6. 检查精度
        test_passed, accuracy_score = self.check_accuracy(
            output_data=output_data,
            golden_output=inputs['golden_output']
        )
        
        return {
            'test_passed': test_passed,
            'accuracy_score': accuracy_score
        }
```

---

## 5. 算子调用方式

### 5.1 算子基类支持__call__

```python
# testpipe/core/test_op.py
class TestOp(ABC):
    """测试算子基类"""
    
    def __call__(self, **kwargs):
        """
        使算子可以像函数一样调用
        
        用法:
            result = self.my_op(input1=value1, input2=value2)
        """
        # 创建临时context
        context = ExecutionContext.get_current()
        
        # 将kwargs放入context
        for key, value in kwargs.items():
            context.set(key, value)
        
        # 执行算子
        outputs = self.execute(context)
        
        # 返回结果
        if len(outputs) == 1:
            return list(outputs.values())[0]
        else:
            return tuple(outputs.values())
```

### 5.2 使用示例

```python
def forward(self, inputs):
    # 方式1: 直接调用
    env_ready = self.check_env()
    
    # 方式2: 传参调用
    model_path = self.prepare_model(model_source=inputs['model_source'])
    
    # 方式3: 多返回值
    remote_om, remote_input = self.transfer(
        om_path=om_path,
        input_data=inputs['input_data']
    )
    
    return {'result': result}
```

---

## 6. 高级特性

### 6.1 条件执行

```python
def forward(self, inputs):
    # 根据条件选择不同路径
    if inputs.get('skip_accuracy_check'):
        output = self.inference(...)
        return {'output': output}
    else:
        output = self.inference(...)
        passed, score = self.check_accuracy(output, inputs['golden'])
        return {'test_passed': passed, 'accuracy_score': score}
```

### 6.2 循环执行

```python
def forward(self, inputs):
    results = []
    
    # 对多个模型执行相同流程
    for model in inputs['models']:
        om_path = self.compile(model_path=model)
        output = self.inference(om_path=om_path)
        results.append(output)
    
    return {'results': results}
```

### 6.3 Pipeline组合

```python
@register_pipeline
class MultiSOC_Pipeline(Pipeline):
    """多SOC测试Pipeline"""
    
    def __init__(self):
        super().__init__()
        
        # 组合其他Pipeline
        self.atc_pipeline = ATC_E2E_Pipeline()
        self.perf_pipeline = Performance_Pipeline()
    
    def forward(self, inputs):
        # 串行执行多个Pipeline
        atc_result = self.atc_pipeline.run(inputs)
        perf_result = self.perf_pipeline.run(inputs)
        
        return {
            'atc_passed': atc_result['test_passed'],
            'perf_passed': perf_result['test_passed']
        }
```

### 6.4 动态Pipeline

```python
@register_pipeline
class Dynamic_Pipeline(Pipeline):
    """动态Pipeline"""
    
    def __init__(self, num_layers: int = 3):
        super().__init__()
        
        # 动态创建算子
        self.layers = []
        for i in range(num_layers):
            self.layers.append(ProcessOp(name=f"layer_{i}"))
    
    def forward(self, inputs):
        x = inputs['data']
        
        # 动态执行
        for layer in self.layers:
            x = layer(data=x)
        
        return {'output': x}
```

---

## 7. TestCase使用Pipeline

### 7.1 YAML引用Python Pipeline

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
    description: 验证 Git 模型资源获取与 ATC 转换
    level: P0
```

### 7.2 TestCaseLoader加载

```python
# testpipe/loaders/testcase_loader.py
class TestCaseLoader:
    """TestCase加载器"""
    
    def load(self, yaml_path: Path) -> TestCase:
        """加载TestCase"""
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        
        tc_data = data['test_case']
        
        # 从注册表获取Pipeline
        pipeline_name = tc_data['pipeline']
        pipeline = PipelineRegistry.create(pipeline_name)
        
        return TestCase(
            name=tc_data['name'],
            pipeline=pipeline,
            inputs=tc_data['inputs'],
            expected=tc_data.get('expected', {})
        )
```

---

## 8. 目录结构

```
testpipe/
├── core/
│   ├── pipeline.py              # Pipeline基类
│   ├── pipeline_registry.py     # Pipeline注册表
│   └── test_op.py               # TestOp基类
├── pipelines/                   # 内置Pipeline
│   ├── __init__.py
│   ├── atc_e2e_pipeline.py
│   ├── ascendc_pipeline.py
│   ├── custom_op_pipeline.py
│   └── amct_quant_pipeline.py
├── ops/                         # 测试算子
│   ├── __init__.py
│   ├── env_check_op.py
│   └── ...
└── loaders/
    └── testcase_loader.py
```

---

## 9. CLI使用

```bash
# 列出所有Pipeline
testpipe list-pipelines

# 查看Pipeline详情
testpipe describe-pipeline OnnxGitAtcPipeline

# 运行TestCase(自动加载Pipeline)
testpipe run examples/testcases/onnx_git_atc.yaml

# 导出Pipeline为JSON(用于可视化)
testpipe export-pipeline OnnxGitAtcPipeline --format json --output pipeline.json

# 导出为ONNX
testpipe export-pipeline OnnxGitAtcPipeline --format onnx --output pipeline.onnx
```

---

## 10. 优势对比

### Python Pipeline vs JSON Pipeline

| 特性 | Python Pipeline | JSON Pipeline |
|------|----------------|---------------|
| 灵活性 | ✅ 支持if/for/函数 | ❌ 静态配置 |
| IDE支持 | ✅ 补全/跳转/检查 | ❌ 无 |
| 复用性 | ✅ 继承/组合 | ❌ 复制粘贴 |
| 版本管理 | ✅ Git友好 | ✅ Git友好 |
| 易读性 | ✅ 代码即文档 | ✅ 结构清晰 |
| 学习曲线 | 中等 | 低 |
| 可视化 | ✅ 可导出JSON/ONNX | ✅ 原生支持 |

---

## 11. 最佳实践

### 11.1 Pipeline命名

- 类名: `Xxx_Pipeline` (如`ATC_E2E_Pipeline`)
- 文件名: `xxx_pipeline.py` (如`atc_e2e_pipeline.py`)

### 11.2 算子初始化

```python
# 推荐: 在__init__中配置算子
self.compile = ATCCompileOp(
    framework=5,
    output_type='FP16',
    timeout=600
)

# 不推荐: 在forward中创建算子
def forward(self, inputs):
    compile_op = ATCCompileOp(...)  # 每次都创建新实例
```

### 11.3 输入输出声明

```python
def __init__(self):
    super().__init__()
    
    # 明确声明输入输出
    self.pipeline_inputs = ['model_source', 'soc_version']
    self.pipeline_outputs = ['test_passed', 'accuracy_score']
```

### 11.4 文档字符串

```python
@register_pipeline
class MyPipeline(Pipeline):
    """
    我的测试Pipeline
    
    输入:
        - model_source: 模型路径
        - soc_version: SOC版本
    
    输出:
        - test_passed: 测试是否通过
    """
```

---

**文档版本**: v1.0  
**最后更新**: 2026-04-11
