# 开发指南 - 自定义 API 与 Action 扩展

## 1. 文档目标

本文档说明如何扩展 TestPipe 的底层能力层。

这里的扩展对象包括:

- Host / Device 执行动作
- 文件传输动作
- 资源获取动作
- 可选基础设施能力，例如 HTTP、数据库、制品仓

核心原则是: **基础设施能力要集中在统一扩展层，不要散落到 TestOp 中。**

---

## 2. 优先判断应该扩展什么

新增能力前，先判断属于哪一类:

### 2.1 Action Provider

适用于:

- 会产生外部副作用
- 需要统一 tracing、重试、超时、日志

例如:

- `SSHExecProvider`
- `DockerExecProvider`
- `SFTPTransferProvider`
- `NFSProvider`

### 2.2 API Provider

适用于:

- 是底层能力封装
- 被多个算子共享
- 不适合作为独立 TestOp

例如:

- `HTTPProvider`
- `ArtifactRepoProvider`

### 2.3 Helper Library

适用于:

- 纯算法或纯数据处理
- 无需纳入动作追踪

---

## 3. 不推荐的扩展方式

不要再使用“直接修改 `OpAPI.__init__` 挂字段”的方式。

问题在于:

- 主类会越来越臃肿
- 可选依赖难隔离
- 插件化困难
- 文档和发现机制不统一

推荐改为注册式扩展:

```python
ApiRegistry.register("http", HTTPProvider)
ActionRegistry.register("device.ssh", SSHExecProvider)
```

---

## 4. 推荐扩展模型

### 4.1 Provider 接口

```python
class Provider(ABC):
    name: str
    version: str

    def setup(self, runtime_context):
        ...

    def close(self):
        ...
```

### 4.2 Action Provider 接口

```python
class ExecProvider(Provider):
    def exec(self, command, timeout, env=None, cwd=None):
        ...
```

### 4.3 API Provider 接口

```python
class HTTPProvider(Provider):
    def get(self, url, headers=None, timeout=30):
        ...
```

---

## 5. 示例: HTTP Provider

```python
from testpipe.providers import Provider, ApiRegistry


class HTTPProvider(Provider):
    name = "http"
    version = "1.0"

    def setup(self, runtime_context):
        self.session = requests.Session()
        self.trace = runtime_context.trace

    def get(self, url, headers=None, timeout=30):
        response = self.session.get(url, headers=headers, timeout=timeout)
        self.trace.record_action(
            action_type="http.get",
            request={"url": url, "headers": headers, "timeout": timeout},
            response={"status_code": response.status_code},
        )
        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
        }

    def close(self):
        self.session.close()


ApiRegistry.register("http", HTTPProvider)
```

---

## 6. 示例: Device SSH 执行 Provider

```python
class SSHExecProvider(ExecProvider):
    name = "device.ssh"
    version = "1.0"

    def setup(self, runtime_context):
        self.client = create_ssh_client(runtime_context.env.device)
        self.trace = runtime_context.trace

    def exec(self, command, timeout, env=None, cwd=None):
        started_at = now()
        result = self.client.run(command, timeout=timeout, env=env, cwd=cwd)
        self.trace.record_action(
            action_type="device.exec",
            request={"command": command, "timeout": timeout},
            response={
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration_ms": elapsed_ms(started_at),
            },
        )
        return result
```

---

## 7. 与 TestOp 的关系

`TestOp` 不应关心某个能力如何初始化或路由，只应关心调用接口。

推荐使用方式:

```python
def execute(self, context):
    response = context.api.get("http").get("https://example/api")
    result = context.device.exec("bash run.sh", timeout=300)
    return {"status_code": response["status_code"]}
```

这意味着:

- Provider 管连接、认证、重试
- Action 层管 tracing 和标准结果格式
- TestOp 只写业务测试步骤

---

## 8. 扩展时的强制要求

### 8.1 可关闭

所有 Provider 都必须支持 `close()`，避免连接泄漏。

### 8.2 可追踪

所有外部副作用都必须进入 trace 记录。

### 8.3 可配置

Provider 的行为必须由 `EnvProfile` 或运行时配置驱动，不要把配置写死在代码里。

### 8.4 可替换

同一类能力应支持不同实现，例如:

- Host Exec: local / docker
- Device Exec: ssh / telnet
- Transfer: sftp / nfs / rsync

---

## 9. 测试建议

每个 Provider 至少需要:

- 初始化测试
- 成功路径测试
- 异常路径测试
- tracing 测试
- close / 清理测试

对于网络依赖较强的 Provider，建议提供 mock 层或 fake provider，避免单元测试直接依赖外部环境。

---

## 10. 反模式

以下做法不推荐:

- 在 `TestOp` 中直接 new 一个 requests session
- 在多个算子里重复实现 SSH 重试逻辑
- 在 Provider 中偷写全局配置
- 不记录动作 trace 只返回最终结果

---

## 11. 推荐目录

```text
testpipe/
  actions/
    exec/
    transfer/
    resource/
  providers/
    api/
```

如果一个扩展主要服务执行引擎，应优先放在 `actions/`。
如果一个扩展主要服务通用能力访问，应优先放在 `providers/api/`。
