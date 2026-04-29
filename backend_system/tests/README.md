# Backend Tests

本目录包含后端 API、服务和性能相关测试。

## 运行

在 `backend_system` 目录执行：

```bash
python tests/run_tests.py
```

或直接运行 pytest：

```bash
pytest
pytest tests/api/
pytest tests/api/test_devices.py
```

## 目录说明

```text
tests/
  api/          # auth、users、devices、alerts、tasks、streams、system 等接口测试
  performance/  # 性能和负载测试
  logs/         # 测试运行日志
  reports/      # 新生成的测试报告目录
  conftest.py   # pytest fixtures
  run_tests.py  # 测试运行脚本
```

历史 Markdown 测试报告已归档到 `../../md/archive/test-reports/backend_system/`。后续运行测试时如果生成新的报告，可保留在 `tests/reports/` 或按需再次归档。

## 覆盖范围

- 用户登录、token 和当前用户。
- 用户 CRUD 和权限控制。
- 设备 CRUD、bootstrap、`/me`、心跳、标定文件。
- 告警上传、筛选、统计和确认。
- 任务 CRUD 和筛选。
- 视频流 offer、answer、状态、控制和停止。
- 系统健康检查。
