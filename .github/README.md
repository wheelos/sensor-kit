# GitHub 工程治理

此目录用于 GitHub 托管协作配置，例如 Pull Request 模板、Issue 模板和经过审查的 CI workflow。

治理文件应保持最小权限、明确触发条件，并避免在普通构建流程中访问实车或发送执行器命令。硬件在环测试只能由受控 runner 承载，并要求显式审批及隔离的测试环境。

正式设计/使用文档存放在 `docs/`，不要把它们复制到 GitHub 模板或 workflow 文件中。
