import anthropic
import httpx
import pyautogui
import time
from PIL import Image, ImageDraw
import io
import base64
import json
from typing import Dict, Any, Tuple, Optional
from cs_magic_log import setup_logger, LogConfig
import os

class BrowserAutomation:
    def __init__(self, api_key: str):
        self.client = anthropic.Client(
            api_key=api_key,
            http_client=anthropic.DefaultHttpxClient(
                proxies="http://localhost:7890",
                transport=httpx.HTTPTransport(local_address="0.0.0.0"),
            ),
        )
        self.running = False
        self.log = setup_logger(LogConfig())
        
        # 设置 PyAutoGUI 安全限制
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.5
        
        self.original_size = None
        self.current_scale = 1.0
        
        self.input_state = {
            "is_input_mode": False,
            "last_input_x": None,
            "last_input_y": None,
            "last_input_time": None
        }
        
        self.screenshot_dir = "screenshots"
        self.current_task_dir = None
        self.step_count = 0
        
        # 确保截图目录存在
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
        
        # 初始化操作历史
        self.action_history = []
        
        # 图片处理相关常量
        self.MAX_SIZE_KB = 20
        self.MIN_QUALITY = 5
        self.MIN_DIMENSION = 480
        
        # 网格线相关常量
        self.GRID_COLOR = (255, 0, 0, 64)  # 红色，透明度降低到 25%
        self.GRID_TEXT_COLOR = (255, 0, 0, 128)  # 文字透明度设为 50%

    def setup_task_directory(self, task: str):
        """为当前任务创建专门的截图目录"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        task_name = "".join(c for c in task[:30] if c.isalnum() or c in (' ', '_')).strip()
        self.current_task_dir = os.path.join(self.screenshot_dir, f"{timestamp}_{task_name}")
        os.makedirs(self.current_task_dir, exist_ok=True)
        self.step_count = 0

    def save_screenshot(self, screenshot: Image.Image, action_info: str = "") -> str:
        """保存截图并返回文件路径"""
        self.step_count += 1
        
        # 清理文件名中的非法字符
        def sanitize_filename(name: str) -> str:
            # 替换常见的非法字符
            invalid_chars = [':', '/', '\\', '*', '?', '"', '<', '>', '|']
            result = name
            for char in invalid_chars:
                result = result.replace(char, '_')
            return result
        
        # 使用清理后的 action_info 创建文件名
        safe_action_info = sanitize_filename(action_info)
        filename = f"step_{self.step_count:03d}_{safe_action_info}.jpg"
        filepath = os.path.join(self.current_task_dir, filename)
        
        # 将 RGBA 转换为 RGB
        if screenshot.mode == 'RGBA':
            screenshot = screenshot.convert('RGB')
        
        screenshot.save(filepath, 'JPEG')
        self.log.info(f"保存截图: {filepath}")
        return filepath

    def wait_for_user_confirmation(self) -> bool:
        """等待用户确认
        返回: True 继续执行, False 终止任务
        """
        while True:
            response = input("\n按 Enter 继续下一步，输入 q 终止任务...").strip().lower()
            if response == '':  # Enter 键
                return True
            elif response == 'q':  # 退出
                return False

    def capture_screen(self) -> Tuple[Image.Image, str]:
        """捕获屏幕截图，添加半透明网格线和坐标标记"""
        screenshot = pyautogui.screenshot()
        self.original_size = screenshot.size
        
        # 将截图转换为 RGBA 模式以支持透明度
        processed_img = screenshot.convert('RGBA')
        overlay = Image.new('RGBA', processed_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 添加半透明网格线
        grid_size = 100
        width, height = processed_img.size
        
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=self.GRID_COLOR, width=1)
            # 坐标文字使用稍高的透明度
            draw.text((x, 10), str(x), fill=self.GRID_TEXT_COLOR)
        
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill=self.GRID_COLOR, width=1)
            draw.text((10, y), str(y), fill=self.GRID_TEXT_COLOR)
        
        # 合并原图和网格层
        processed_img = Image.alpha_composite(processed_img, overlay)
        processed_img = processed_img.convert('RGB')  # 转回 RGB 模式
        
        # 压缩图片
        quality = 50
        scale_factor = 0.5
        
        while True:
            width, height = processed_img.size
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)
            
            if new_width < self.MIN_DIMENSION or new_height < self.MIN_DIMENSION:
                self.log.warning(f"图片尺寸已达到最小限制: {new_width}x{new_height}")
                break
            
            resized = processed_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            gray = resized.convert('L')
            
            buffered = io.BytesIO()
            gray.save(buffered, format="JPEG", quality=quality, optimize=True)
            size_kb = len(buffered.getvalue()) / 1024
            
            if size_kb <= self.MAX_SIZE_KB or (quality <= self.MIN_QUALITY and scale_factor < 0.2):
                self.log.info(f"完成压缩 - 最终尺寸: {new_width}x{new_height}, 质量: {quality}, 大小: {size_kb:.2f}KB")
                self.current_scale = scale_factor
                return processed_img, base64.b64encode(buffered.getvalue()).decode()
            
            if size_kb > self.MAX_SIZE_KB * 2:
                scale_factor *= 0.7
            else:
                quality = max(quality - 10, self.MIN_QUALITY)

    def transform_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """将原始坐标转换为缩放后的坐标"""
        if self.original_size and self.current_scale != 1.0:
            # 将原始坐标转换为缩放后的坐标
            scaled_x = int(x * self.current_scale)
            scaled_y = int(y * self.current_scale)
            
            # 确保坐标不超出屏幕范围
            max_x = int(self.original_size[0] * self.current_scale)
            max_y = int(self.original_size[1] * self.current_scale)
            
            scaled_x = min(max(0, scaled_x), max_x - 1)
            scaled_y = min(max(0, scaled_y), max_y - 1)
            
            self.log.info(f"坐标转换: ({x}, {y}) -> ({scaled_x}, {scaled_y})")
            return scaled_x, scaled_y
        return x, y

    def execute_action(self, action: Dict[str, Any]) -> None:
        """执行 AI 决定的动作"""
        if not isinstance(action, dict):
            self.log.error(f"动作必须是字典类型，收到: {type(action)}")
            return
        
        action_type = action.get("type")
        if not action_type:
            self.log.error("动作缺少 type 字段")
            return
        
        self.log.info(f"执行动作: {action}")
        
        try:
            if action_type in ["move", "click"]:
                if "x" not in action or "y" not in action:
                    raise ValueError(f"{action_type} 动作需要 x, y 坐标")
                
                # 获取原始截图尺寸
                screen_width, screen_height = pyautogui.size()
                
                # 检查坐标是否在屏幕范围内
                if action["x"] > screen_width or action["y"] > screen_height:
                    self.log.warning(f"坐标超出屏幕范围，原始: ({action['x']}, {action['y']})")
                    # 调整坐标到屏幕范围内
                    x = min(action["x"], screen_width - 1)
                    y = min(action["y"], screen_height - 1)
                    self.log.info(f"调整后坐标: ({x}, {y})")
                else:
                    x, y = action["x"], action["y"]
                
                # 转换坐标
                x, y = self.transform_coordinates(x, y)
                
                # 获取点击位置的颜色信息
                screenshot = pyautogui.screenshot()
                color = screenshot.getpixel((x, y))
                
                # 如果点击位置是空白或背景色，尝试调整位置
                if self.is_background_color(color):
                    adjusted_pos = self.find_nearest_clickable(screenshot, x, y)
                    if adjusted_pos:
                        x, y = adjusted_pos
                        self.log.info(f"调整点击位置从 ({action['x']}, {action['y']}) 到 ({x}, {y})")
                
                if action_type == "move":
                    pyautogui.moveTo(x, y)
                else:
                    pyautogui.click(x, y)
                    # 更新输入状态
                    self.input_state["is_input_mode"] = True
                    self.input_state["last_input_x"] = x
                    self.input_state["last_input_y"] = y
                    self.input_state["last_input_time"] = time.time()
            
            elif action_type == "type":
                if "text" not in action:
                    raise ValueError("type 动作需要 text 参数")
                    
                # 检查是否处于输入模式
                if not self.input_state["is_input_mode"]:
                    self.log.warning("尝试输入文字但未处于输入模式，忽略此操作")
                    return
                    
                # 检查上次点击输入框是否超时（比如 5 秒）
                if time.time() - self.input_state["last_input_time"] > 5:
                    self.log.warning("输入模式可能已过期，重新点击上次的输入位置")
                    x, y = self.input_state["last_input_x"], self.input_state["last_input_y"]
                    pyautogui.click(x, y)
                    time.sleep(0.5)  # 等待输入框激活
                    
                pyautogui.typewrite(action["text"])
            
            elif action_type == "press":
                if "key" not in action:
                    raise ValueError("press 动作需要 key 参数")
                pyautogui.press(action["key"])
                # 某些按键可能会退出输入模式
                if action["key"] in ["enter", "escape", "tab"]:
                    self.input_state["is_input_mode"] = False
            
            elif action_type == "scroll":
                if "amount" not in action:
                    raise ValueError("scroll 动作需要 amount 参数")
                pyautogui.scroll(action["amount"])
            
            elif action_type == "none":
                self.log.info("跳过 none 类型动作")
            
            else:
                self.log.warning(f"未知的动作类型: {action_type}")
            
        except ValueError as e:
            self.log.error(f"动作参数错误: {str(e)}")
        except pyautogui.FailSafeException:
            self.log.error("触发 PyAutoGUI 安全限制")
        except Exception as e:
            self.log.error(f"执行动作时出: {str(e)}", exc_info=True)
            self.input_state["is_input_mode"] = False  # 发生错误时重置输入状态
            
    def get_ai_decision(self, task: str, screenshot: str) -> Tuple[Dict[str, Any], bool]:
        """获取 AI 对下一步操作的决策"""
        try:
            input_state_info = "当前处于输入模式" if self.input_state["is_input_mode"] else "当前不处于输入模式"
            
            message_content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": screenshot
                    }
                },
                {
                    "type": "text",
                    "text": f"""基于屏幕截图执行任务: {task}

⚠️ 坐标范围提示：
- 屏幕分辨率：{self.original_size[0]}x{self.original_size[1]}
- 请确保返回的坐标在上述范围内
- x 坐标应小于 {self.original_size[0]}
- y 坐标应小于 {self.original_size[1]}

⚠️ 必须严格按照以下JSON格式返回（示例）：
{{
    "infer": "分析当前看到了什么，以及为什么选择这个动作",
    "action": {{
        "type": "click",  // 必须是以下之一: move/click/type/press/scroll/none
        "x": 100,        // 对于 move/click 操作必须提供
        "y": 200,        // 对于 move/click 操作必须提供
        "text": "...",   // 对于 type 操作必须提供
        "key": "enter",  // 对于 press 操作必须提供
        "amount": -100   // 对于 scroll 操作必须提供
    }},
    "completed": false   // 任务是否完成
}}

当前界面分析要求：
1. 仔细观察是否在浏览器中
2. 识别地址栏、搜索框等关键界面元素
3. 确认当前页面状态（是否已打开特定网站）

系统状态：
{self.get_input_context()}
- 屏幕分辨率：{self.original_size[0]}x{self.original_size[1]}

最近的操作历史：
{self.get_action_history()}

操作规则：
1. 访问网站流程：
   a. 先点击(click)地址栏/搜索框
   b. 等待进入输入模式
   c. 再输入(type)网址
   
2. 严格的输入规则：
   - type 动作只能在输入模式下使用
   - 必须先用 click 激活输入框
   - 每次输入前都要确认输入模式

3. 坐标选择规则：
   - 使用网格线精确定位
   - 选择元素中心位置
   - 避免边缘区域
"""
                }
            ]
            
            self.log.info("发送 AI 请求")
            
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{
                    "role": "user",
                    "content": message_content
                }]
            )
            
            content = response.content[0].text
            self.log.info(f"AI 响应: {content}")
            
            # 修改 JSON 解析部分
            try:
                # 直接尝试解析整个响应
                result = json.loads(content)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试使用正则提取 JSON
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if not json_match:
                    self.log.error("未找到有效的 JSON 数据")
                    return {"type": "none"}, False
                
                try:
                    result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    self.log.error("解析提取的 JSON 数据失败")
                    return {"type": "none"}, False

            # 验证返回数据的格式
            if not isinstance(result, dict):
                raise ValueError("返回数据必须是字典类型")
            
            if "action" not in result or "completed" not in result:
                raise ValueError("返回数据缺少必要字段")
            
            if not isinstance(result["action"], dict) or "type" not in result["action"]:
                raise ValueError("action 必须是包含 type 字段的字典")
            
            if result["action"]["type"] not in ["move", "click", "type", "press", "scroll", "none"]:
                raise ValueError(f"无效的动作类型: {result['action']['type']}")
            
            if not isinstance(result["completed"], bool):
                raise ValueError("completed 必须是布尔值")
            
            # 保存新的操作到历史记录
            self.action_history.append(f"{result['action']['type']}: {result['action']}")
            
            return result["action"], result["completed"]
        
        except Exception as e:
            self.log.error(f"获取 AI 决策时出错: {str(e)}", exc_info=True)
            return {"type": "none"}, False

    def run(self, task: str) -> bool:
        """运行自动化任务"""
        self.running = True
        self.setup_task_directory(task)
        print(f"开始执行任务: {task}")
        
        success = True
        while self.running:
            try:
                # 捕获带网格线的屏幕截图
                processed_screenshot, screenshot_base64 = self.capture_screen()
                
                # 获取 AI 决策
                action, completed = self.get_ai_decision(task, screenshot_base64)
                
                # 保存当前步骤的截图（使用带网格线的版本）
                action_info = f"{action['type']}"
                if 'x' in action and 'y' in action:
                    action_info += f"_at_{action['x']}_{action['y']}"
                elif 'text' in action:
                    action_info += f"_{action['text'][:20]}"
                self.save_screenshot(processed_screenshot, action_info)
                
                # 等待用户确认
                print(f"\n即将执行动作: {action}")
                if not self.wait_for_user_confirmation():
                    print("用户止任务")
                    success = False
                    break
                
                # 执行动作
                if action["type"] != "none":
                    self.execute_action(action)
                    
                if completed:
                    print("任务完成!")
                    break
                    
                time.sleep(1)  # 等待页面响应
                
            except KeyboardInterrupt:
                print("用户中断任务")
                success = False
                break
            except Exception as e:
                print(f"发生错误: {str(e)}")
                self.log.error("任务执行出错", exc_info=True)
                success = False
                break
                
        self.running = False
        return success
                
        self.running = False 

    def is_background_color(self, color: Tuple[int, int, int]) -> bool:
        """判断是否是背景色（白色或接近白色）"""
        return all(c > 240 for c in color)

    def find_nearest_clickable(self, screenshot: Image.Image, x: int, y: int, radius: int = 20) -> Optional[Tuple[int, int]]:
        """在给定位置周围搜索可点击的元素"""
        width, height = screenshot.size
        min_diff = float('inf')
        best_pos = None
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                new_x, new_y = x + dx, y + dy
                if 0 <= new_x < width and 0 <= new_y < height:
                    color = screenshot.getpixel((new_x, new_y))
                    if not self.is_background_color(color):
                        diff = abs(dx) + abs(dy)  # 曼哈顿距离
                        if diff < min_diff:
                            min_diff = diff
                            best_pos = (new_x, new_y)
        
        return best_pos
                
        self.running = False 

    # 新增辅助方法
    def get_input_context(self) -> str:
        """获取格式化的输入状态信息"""
        if self.input_state["is_input_mode"]:
            return f"""当前输入状态:
- 输入框位置: ({self.input_state['last_input_x']}, {self.input_state['last_input_y']})
- 上次点击时间: {time.strftime('%H:%M:%S', time.localtime(self.input_state['last_input_time']))}"""
        else:
            return """⚠️ 当前不在输入模式！需要先点击输入框。"""

    def get_action_history(self) -> str:
        """获取格式化的操作历史"""
        if not self.action_history:
            return "暂无操作历史"
        return "\n".join([f"- {a}" for a in self.action_history[-3:]])