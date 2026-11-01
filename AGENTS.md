# Agent 入口与工作规则

修改前先阅读相关构建目标、源码和正式文档；更具体目录的规则优先。

## 文档分层

- `docs/`：正式架构、构建、使用和验收文档；更新 `docs/README.md` 索引。
- `.agents/skills/`：可重复工作流程。
- `.agents/knowledge/`：经过验证的稳定事实。
- `.agents/notes/`：临时调查，不作为正式架构。
- `.github/`：工程治理。

## 工程约定

- 本仓库仅包装 sensors 产品，相机/雷达组合是构建变体，不是额外产品。
- vehicle/CAN/whl-can 归独立 `vehicle-infra` 仓库，两仓库互不依赖。
- 驱动源码由外部模块维护，通过 `bazel_dep` 编译，不迁入本仓库。
- 不依赖 Apollo-lite checkout 或启动脚本；默认使用发布 registry。
- `hardware.build` 提供共享构建规则，FFmpeg 只复用其公开 extension。
- SDK、设备配置和标定必须显式选择；不得默认启动硬件。
- `doctor` 只检查完整性和模板渲染，不宣称传感器正常或性能通过。
- 不覆盖已有数据，不提交构建输出、凭据、私有标定或设备数据。
- 运行覆盖改动的最小测试，不伪造发布、锁或设备验收结果。

## 入口

- [文档索引](docs/README.md)
- [产品架构](docs/architecture/sensor-sdk-plan.md)
- [Bazel 构建](docs/build/bazel-integration.md)
- [Sensor runtime](docs/operations/sensor-runtime.md)
