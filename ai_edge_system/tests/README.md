# AI Edge Tests

本目录包含 AI Edge 侧安全规则、检测流程和边缘逻辑测试。

## 运行

在 `ai_edge_system` 目录执行：

```bash
python tests/run_tests.py
```

或按测试文件运行：

```bash
pytest tests/
```

## 目录说明

```text
tests/
  logs/      # 测试运行日志
  reports/   # 新生成的测试报告目录
```

历史 Markdown 测试报告已归档到 `../../md/archive/test-reports/ai_edge_system/`。

## 覆盖范围

- 安全规则核心状态管理。
- 火焰、烟雾、火星检测规则。
- 安全帽等 PPE 规则。
- 气瓶安全距离规则。
- 授权人员和人脸识别相关规则。
