from browser_automation import BrowserAutomation
import os
import dotenv
dotenv.load_dotenv()

def main():
    # 从环境变量获取 API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("请设置 ANTHROPIC_API_KEY 环境变量")
        
    # 创建自动化实例
    automation = BrowserAutomation(api_key)
    
    # 定义任务
    task = "打开推特给马斯克的最新帖子点赞" # input("请输入要执行的任务: ")
    
    # 运行自动化流程
    automation.run(task)

if __name__ == "__main__":
    main() 