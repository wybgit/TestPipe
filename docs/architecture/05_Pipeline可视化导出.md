# 特性05: Pipeline可视化导出

**阶段**: Phase 1 (MVP)  
**优先级**: P1  
**预计工作量**: 2天  
**依赖**: 特性03 (Pipeline JSON规范)

---

## 1. 需求描述

### 1.1 业务需求

Pipeline需要支持可视化,方便用户理解测试流程:
- **导出ONNX模型** - 可以用Netron查看
- **导出DOT图** - 可以用Graphviz渲染
- 自动分析节点依赖关系,生成有向图

---

## 2. 导出格式

### 2.1 ONNX导出

将Pipeline转换为ONNX模型:
- 每个测试算子 → ONNX算子节点
- 数据流 → ONNX边
- 可以用Netron可视化

### 2.2 DOT图导出

将Pipeline转换为Graphviz DOT格式:
- 每个测试算子 → DOT节点
- 数据流 → DOT边
- 可以用Graphviz渲染为PNG/SVG

---

## 3. ONNX导出器实现

```python
import onnx
from onnx import helper, TensorProto
from testpipe.core import Pipeline

class ONNXExporter:
    """ONNX导出器"""
    
    def export(self, pipeline: Pipeline, output_path: str):
        """
        导出Pipeline为ONNX模型
        
        Args:
            pipeline: Pipeline实例
            output_path: 输出ONNX文件路径
        """
        nodes = []
        inputs = []
        outputs = []
        
        # 创建ONNX节点
        for node in pipeline.nodes.values():
            onnx_node = helper.make_node(
                op_type=node.op_type,
                inputs=node.inputs,
                outputs=node.outputs,
                name=node.name,
                **node.attributes
            )
            nodes.append(onnx_node)
        
        # 创建Pipeline输入
        for inp_name in pipeline.pipeline_inputs:
            inp = helper.make_tensor_value_info(
                inp_name,
                TensorProto.UNDEFINED,
                []
            )
            inputs.append(inp)
        
        # 创建Pipeline输出
        for out_name in pipeline.pipeline_outputs:
            out = helper.make_tensor_value_info(
                out_name,
                TensorProto.UNDEFINED,
                []
            )
            outputs.append(out)
        
        # 创建图
        graph = helper.make_graph(
            nodes=nodes,
            name=pipeline.name,
            inputs=inputs,
            outputs=outputs
        )
        
        # 创建模型
        model = helper.make_model(
            graph,
            producer_name='TestPipe',
            opset_imports=[helper.make_opsetid("", 13)]
        )
        
        # 保存
        onnx.save(model, output_path)
        print(f"✓ ONNX模型已导出: {output_path}")
```

---

## 4. DOT导出器实现

```python
from testpipe.core import Pipeline

class DOTExporter:
    """DOT图导出器"""
    
    def export(self, pipeline: Pipeline, output_path: str):
        """
        导出Pipeline为DOT图
        
        Args:
            pipeline: Pipeline实例
            output_path: 输出DOT文件路径
        """
        lines = []
        lines.append(f'digraph "{pipeline.name}" {{')
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=rounded];')
        lines.append('')
        
        # 添加节点
        for node in pipeline.nodes.values():
            label = f"{node.name}\\n({node.op_type})"
            lines.append(f'  "{node.name}" [label="{label}"];')
        
        lines.append('')
        
        # 添加边
        for node in pipeline.nodes.values():
            for input_name in node.inputs:
                # 找到生产这个输入的节点
                for producer in pipeline.nodes.values():
                    if input_name in producer.outputs:
                        lines.append(f'  "{producer.name}" -> "{node.name}" [label="{input_name}"];')
        
        lines.append('}')
        
        # 保存
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))
        
        print(f"✓ DOT图已导出: {output_path}")
        print(f"  使用以下命令渲染:")
        print(f"  dot -Tpng {output_path} -o {output_path}.png")
```

---

## 5. CLI命令

```bash
# 导出ONNX
testpipe export pipeline.json --format onnx --output pipeline.onnx

# 导出DOT
testpipe export pipeline.json --format dot --output pipeline.dot

# 导出并渲染DOT
testpipe export pipeline.json --format dot --output pipeline.dot --render
```

---

## 6. 使用示例

```python
from testpipe.loaders import PipelineLoader
from testpipe.exporters import ONNXExporter, DOTExporter

# 加载Pipeline
loader = PipelineLoader()
pipeline = loader.load("pipelines/atc_e2e.json")

# 导出ONNX
onnx_exporter = ONNXExporter()
onnx_exporter.export(pipeline, "pipeline.onnx")

# 导出DOT
dot_exporter = DOTExporter()
dot_exporter.export(pipeline, "pipeline.dot")
```

---

## 7. 验收标准

- [ ] 支持导出ONNX模型
- [ ] 支持导出DOT图
- [ ] ONNX可以用Netron查看
- [ ] DOT可以用Graphviz渲染
- [ ] CLI命令工作正常

---

**文档版本**: v2.0  
**创建日期**: 2026-04-11  
**负责人**: TestPipe核心团队
