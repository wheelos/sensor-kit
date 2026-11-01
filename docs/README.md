# 正式项目文档

- [独立传感器产品架构](architecture/sensor-sdk-plan.md)：模块边界与交付验收。
- [Bzlmod 构建与共享 FFmpeg](build/bazel-integration.md)：registry、SDK、配置和包构建。
- [Sensor runtime 操作](operations/sensor-runtime.md)：统一 Cyber 工具入口、录制/监控、安装与环境隔离。

车辆/CAN/whl-can 在独立 `vehicle-infra` 仓库维护。本仓库不依赖它。
