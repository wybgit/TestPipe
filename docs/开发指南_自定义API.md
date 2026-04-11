# 开发指南 - 自定义API开发

---

## 1. 概述

TestPipe框架的OpAPI提供了统一的底层能力访问接口。你可以扩展OpAPI,添加新的API模块,供测试算子使用。

---

## 2. OpAPI架构

### 2.1 当前API模块

```python
class OpAPI:
    """统一操作API"""
    
    def __init__(self):
        self.ssh = SSHApi()           # SSH操作
        self.transfer = TransferApi() # 文件传输
        self.exec = ExecApi()         # 命令执行
        self.file = FileApi()         # 文件操作
```

### 2.2 API模块接口

每个API模块都是一个独立的类,提供相关的操作方法。

---

## 3. 开发新的API模块

### 3.1 基础示例 - DatabaseApi

```python
# testpipe/api/database_api.py
import sqlite3
from typing import List, Dict, Any

class DatabaseApi:
    """数据库操作API"""
    
    def __init__(self):
        self.conn = None
    
    def connect(self, db_path: str):
        """连接数据库"""
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
    
    def execute(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行SQL查询"""
        if not self.conn:
            raise RuntimeError("数据库未连接")
        
        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        
        # 返回结果
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def execute_many(self, sql: str, params_list: List[tuple]):
        """批量执行SQL"""
        if not self.conn:
            raise RuntimeError("数据库未连接")
        
        cursor = self.conn.cursor()
        cursor.executemany(sql, params_list)
        self.conn.commit()
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
            self.conn = None
```

### 3.2 注册到OpAPI

```python
# testpipe/api/op_api.py
from testpipe.api.database_api import DatabaseApi

class OpAPI:
    """统一操作API"""
    
    def __init__(self):
        self.ssh = SSHApi()
        self.transfer = TransferApi()
        self.exec = ExecApi()
        self.file = FileApi()
        self.database = DatabaseApi()  # 新增
```

---

## 4. 完整示例 - HTTPApi

```python
# testpipe/api/http_api.py
import requests
from typing import Dict, Any, Optional
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class HTTPApi:
    """HTTP请求API"""
    
    def __init__(self):
        self.session = requests.Session()
        
        # 配置重试策略
        retry = Retry(
            total=3,
            backoff_factor=0.3,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
    
    def get(self, url: str, params: Dict = None, 
            headers: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """GET请求"""
        response = self.session.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': response.text,
            'json': response.json() if self._is_json(response) else None
        }
    
    def post(self, url: str, data: Any = None, json: Dict = None,
             headers: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """POST请求"""
        response = self.session.post(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': response.text,
            'json': response.json() if self._is_json(response) else None
        }
    
    def put(self, url: str, data: Any = None, json: Dict = None,
            headers: Dict = None, timeout: int = 30) -> Dict[str, Any]:
        """PUT请求"""
        response = self.session.put(
            url,
            data=data,
            json=json,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': response.text,
            'json': response.json() if self._is_json(response) else None
        }
    
    def delete(self, url: str, headers: Dict = None, 
               timeout: int = 30) -> Dict[str, Any]:
        """DELETE请求"""
        response = self.session.delete(
            url,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'body': response.text
        }
    
    def download(self, url: str, output_path: str, 
                 headers: Dict = None, timeout: int = 300):
        """下载文件"""
        response = self.session.get(
            url,
            headers=headers,
            timeout=timeout,
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def set_auth(self, username: str, password: str):
        """设置认证"""
        self.session.auth = (username, password)
    
    def set_header(self, key: str, value: str):
        """设置默认请求头"""
        self.session.headers[key] = value
    
    def _is_json(self, response) -> bool:
        """检查响应是否为JSON"""
        content_type = response.headers.get('Content-Type', '')
        return 'application/json' in content_type
    
    def close(self):
        """关闭会话"""
        self.session.close()
```

---

## 5. 在测试算子中使用

```python
from testpipe.core import TestOp, register_op

@register_op
class APITestOp(TestOp):
    """API测试算子"""
    
    op_type = "APITest"
    
    def execute(self, context):
        # 使用HTTP API
        response = self.api.http.get(
            url="https://api.example.com/data",
            headers={"Authorization": "Bearer token"}
        )
        
        # 检查响应
        assert response['status_code'] == 200
        data = response['json']
        
        return {"result": data}
```

---

## 6. API模块最佳实践

### 6.1 错误处理

```python
class MyApi:
    def operation(self):
        try:
            # 执行操作
            result = self._do_work()
        except ConnectionError as e:
            raise RuntimeError(f"连接失败: {e}")
        except TimeoutError as e:
            raise RuntimeError(f"操作超时: {e}")
        except Exception as e:
            raise RuntimeError(f"操作失败: {e}")
        
        return result
```

### 6.2 资源管理

```python
class MyApi:
    def __init__(self):
        self.resource = None
    
    def connect(self):
        """获取资源"""
        self.resource = acquire_resource()
    
    def close(self):
        """释放资源"""
        if self.resource:
            self.resource.close()
            self.resource = None
    
    def __enter__(self):
        """支持上下文管理器"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """自动清理"""
        self.close()
```

### 6.3 配置管理

```python
class MyApi:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.retry = self.config.get('retry', 3)
    
    def operation(self):
        # 使用配置
        result = self._do_work(timeout=self.timeout)
        return result
```

### 6.4 日志记录

```python
import logging

class MyApi:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def operation(self):
        self.logger.info("开始操作")
        try:
            result = self._do_work()
            self.logger.info("操作成功")
            return result
        except Exception as e:
            self.logger.error(f"操作失败: {e}")
            raise
```

---

## 7. API模块测试

```python
# tests/api/test_http_api.py
import pytest
from testpipe.api import HTTPApi

def test_http_get():
    """测试GET请求"""
    api = HTTPApi()
    
    response = api.get("https://httpbin.org/get")
    
    assert response['status_code'] == 200
    assert response['json'] is not None

def test_http_post():
    """测试POST请求"""
    api = HTTPApi()
    
    response = api.post(
        "https://httpbin.org/post",
        json={"key": "value"}
    )
    
    assert response['status_code'] == 200
    assert response['json']['json']['key'] == "value"

def test_http_error_handling():
    """测试错误处理"""
    api = HTTPApi()
    
    with pytest.raises(Exception):
        api.get("https://httpbin.org/status/404")
```

---

## 8. API目录结构

```
testpipe/
├── api/
│   ├── __init__.py
│   ├── op_api.py              # OpAPI主类
│   ├── ssh_api.py             # SSH API
│   ├── transfer_api.py        # 文件传输API
│   ├── exec_api.py            # 命令执行API
│   ├── file_api.py            # 文件操作API
│   ├── http_api.py            # HTTP API(新增)
│   └── database_api.py        # 数据库API(新增)
```

---

## 9. 发布API模块

### 9.1 作为插件发布

```python
# my_api_plugin/setup.py
from setuptools import setup

setup(
    name='testpipe-my-api',
    version='1.0.0',
    packages=['my_api_plugin'],
    install_requires=['testpipe', 'requests'],
    entry_points={
        'testpipe.api': [
            'MyApi = my_api_plugin.my_api:MyApi',
        ]
    }
)
```

### 9.2 动态加载API

```python
# testpipe/api/op_api.py
import pkg_resources

class OpAPI:
    def __init__(self):
        # 加载内置API
        self.ssh = SSHApi()
        self.transfer = TransferApi()
        
        # 动态加载插件API
        self._load_plugin_apis()
    
    def _load_plugin_apis(self):
        """加载插件API"""
        for entry_point in pkg_resources.iter_entry_points('testpipe.api'):
            api_class = entry_point.load()
            api_name = entry_point.name
            setattr(self, api_name, api_class())
```

---

## 10. 常见API模块

### 10.1 推荐实现的API

- **HTTPApi** - HTTP请求
- **DatabaseApi** - 数据库操作
- **DockerApi** - Docker容器管理
- **K8sApi** - Kubernetes操作
- **CloudApi** - 云服务API(AWS/Azure/GCP)
- **MonitorApi** - 监控指标采集

### 10.2 API设计原则

- 保持接口简洁清晰
- 提供合理的默认值
- 支持超时和重试
- 完善的错误处理
- 资源自动清理
- 支持上下文管理器

---

**文档版本**: v1.0  
**最后更新**: 2026-04-11
