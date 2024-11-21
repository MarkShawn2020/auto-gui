# AI Browser Assistant (experimental)

> 用 cursor 两小时试了一下，目前还需要进一步优化，暂时仅供学习使用。

基于大语言模型的浏览器自动化助手，能够通过自然语言指令完成各种浏览器操作任务。

## 功能特点

- 支持自然语言输入任务指令
- 基于 Claude-3.5 大语言模型的智能决策
- 实时屏幕截图分析
- 自动化鼠标和键盘操作
- 任务进度实时监控
- 支持任务中断和取消

## 工作原理

1. 用户输入自然语言任务描述
2. 系统启动任务循环:
   - 捕获当前屏幕截图
   - 将截图发送给 Claude-3.5 分析
   - 模型根据当前界面状态决定下一步操作
   - 执行相应的鼠标/键盘操作
   - 评估任务完成状态
3. 任务完成或用户手动中断时结束

## 使用示例 (TODO)

```python
# 示例任务: 在京东购买帽子
task = "在京东上找一顶好看且性价比高的帽子并完成购买"
assistant = BrowserAssistant()
assistant.run_task(task)
```


## 环境要求

- Python 3.8+
- 依赖包:
  - opencv-python
  - pyautogui
  - anthropic-sdk
  - pillow

## 安装说明


```bash
git clone https://github.com/yourusername/ai-browser-assistant
cd ai-browser-assistant
pip install -r requirements.txt
```


## 配置说明

1. 在 `config.yaml` 中配置你的 Claude API 密钥:

```yaml
claude:
api_key: "your-api-key-here"
```

2. 根据需要调整截图间隔和其他参数

## 使用注意

- 确保良好的网络连接以保证与 Claude API 的通信
- 建议在操作过程中不要移动鼠标或使用键盘
- 如需中断任务，按 Ctrl+C

## 开发计划

- [ ] 支持更多浏览器操作
- [ ] 优化模型决策准确性
- [ ] 添加任务历史记录
- [ ] 支持并行任务处理
- [ ] 添加 GUI 界面

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目。

## 许可证

MIT License

## 联系方式

- 项目主页: https://github.com/cs-magic/auto-gui
- 问题反馈: https://github.com/cs-magic/auto-gui/issues
