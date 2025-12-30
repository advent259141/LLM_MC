"""
Python Script Executor for LLM-MC
Allows LLM to write and execute Python code to perform complex actions
"""
import asyncio
import traceback
from typing import Dict, Any, Optional, List
from io import StringIO
import sys

from app.bot.client import bot_client
from app.skills.manager import skill_manager


class BotAPI:
    """
    Safe Bot API wrapper for script execution
    Provides async methods that scripts can call
    """
    
    def __init__(self):
        self.results = []  # 存储执行过程中的结果
        self.logs = []     # 存储日志
        self._loaded_skills = {}  # 已加载的技能函数
    
    def log(self, message: str):
        """记录日志"""
        self.logs.append(str(message))
        print(f"[Script] {message}")
    
    async def chat(self, message: str) -> Dict[str, Any]:
        """发送聊天消息"""
        result = await bot_client.execute_action("chat", {"message": message})
        self.results.append({"action": "chat", "result": result})
        return result
    
    async def goTo(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """移动到指定坐标"""
        result = await bot_client.execute_action("goTo", {"x": x, "y": y, "z": z})
        self.results.append({"action": "goTo", "result": result})
        return result
    
    async def followPlayer(self, playerName: str) -> Dict[str, Any]:
        """跟随玩家"""
        result = await bot_client.execute_action("followPlayer", {"playerName": playerName})
        self.results.append({"action": "followPlayer", "result": result})
        return result
    
    async def stopMoving(self) -> Dict[str, Any]:
        """停止移动"""
        result = await bot_client.execute_action("stopMoving", {})
        self.results.append({"action": "stopMoving", "result": result})
        return result
    
    async def jump(self) -> Dict[str, Any]:
        """跳跃"""
        result = await bot_client.execute_action("jump", {})
        self.results.append({"action": "jump", "result": result})
        return result
    
    async def lookAt(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """看向坐标"""
        result = await bot_client.execute_action("lookAt", {"x": x, "y": y, "z": z})
        self.results.append({"action": "lookAt", "result": result})
        return result
    
    async def attack(self, entityType: str) -> Dict[str, Any]:
        """攻击实体"""
        result = await bot_client.execute_action("attack", {"entityType": entityType})
        self.results.append({"action": "attack", "result": result})
        return result
    
    async def collectBlock(self, blockType: str) -> Dict[str, Any]:
        """挖掘方块"""
        result = await bot_client.execute_action("collectBlock", {"blockType": blockType})
        self.results.append({"action": "collectBlock", "result": result})
        return result
    
    async def wait(self, seconds: float) -> Dict[str, Any]:
        """等待"""
        result = await bot_client.execute_action("wait", {"seconds": seconds})
        self.results.append({"action": "wait", "result": result})
        return result
    
    async def viewInventory(self) -> Dict[str, Any]:
        """查看背包"""
        result = await bot_client.execute_action("viewInventory", {})
        self.results.append({"action": "viewInventory", "result": result})
        return result
    
    async def equipItem(self, itemName: str) -> Dict[str, Any]:
        """装备物品"""
        result = await bot_client.execute_action("equipItem", {"itemName": itemName})
        self.results.append({"action": "equipItem", "result": result})
        return result
    
    async def placeBlock(self, blockName: str, x: int, y: int, z: int) -> Dict[str, Any]:
        """放置方块"""
        result = await bot_client.execute_action("placeBlock", {
            "blockName": blockName, "x": x, "y": y, "z": z
        })
        self.results.append({"action": "placeBlock", "result": result})
        return result
    
    async def dropItem(self, itemName: str, count: int = None) -> Dict[str, Any]:
        """丢弃物品"""
        params = {"itemName": itemName}
        if count is not None:
            params["count"] = count
        result = await bot_client.execute_action("dropItem", params)
        self.results.append({"action": "dropItem", "result": result})
        return result
    
    async def eat(self, foodName: str = None) -> Dict[str, Any]:
        """吃东西恢复饥饿值"""
        params = {}
        if foodName:
            params["foodName"] = foodName
        result = await bot_client.execute_action("eat", params)
        self.results.append({"action": "eat", "result": result})
        return result
    
    async def useItem(self) -> Dict[str, Any]:
        """使用当前手持物品（如使用弓箭、喝药水、使用末影珍珠等）"""
        result = await bot_client.execute_action("useItem", {})
        self.results.append({"action": "useItem", "result": result})
        return result
    
    async def activateBlock(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """
        右键激活/交互方块（如打开门、按按钮、拉拉杆、使用床等）
        
        Args:
            x, y, z: 方块坐标
            
        Returns:
            交互结果
        """
        result = await bot_client.execute_action("activateBlock", {"x": x, "y": y, "z": z})
        self.results.append({"action": "activateBlock", "result": result})
        return result
    
    async def scanBlocks(self, blockTypes: list, range: int = 16) -> Dict[str, Any]:
        """扫描方块"""
        result = await bot_client.execute_action("scanBlocks", {
            "blockTypes": blockTypes, "range": range
        })
        self.results.append({"action": "scanBlocks", "result": result})
        return result
    
    async def findBlock(self, blockType: str, maxDistance: int = 32) -> Dict[str, Any]:
        """寻找方块"""
        result = await bot_client.execute_action("findBlock", {
            "blockType": blockType, "maxDistance": maxDistance
        })
        self.results.append({"action": "findBlock", "result": result})
        return result
    
    async def getBlockAt(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """获取方块信息"""
        result = await bot_client.execute_action("getBlockAt", {"x": x, "y": y, "z": z})
        self.results.append({"action": "getBlockAt", "result": result})
        return result
    
    async def scanEntities(self, range: int = 16, entityType: str = None) -> Dict[str, Any]:
        """扫描实体"""
        params = {"range": range}
        if entityType:
            params["entityType"] = entityType
        result = await bot_client.execute_action("scanEntities", params)
        self.results.append({"action": "scanEntities", "result": result})
        return result
    
    async def listPlayers(self) -> Dict[str, Any]:
        """
        列出服务器上所有在线玩家
        
        Returns:
            包含玩家列表的字典：
            - players: 玩家列表，每个玩家包含 name, position, distance, inRange 等信息
            - totalCount: 总玩家数
            - inRangeCount: 在可见范围内的玩家数
            - botUsername: bot 自己的用户名
            
        Example:
            players = await bot.listPlayers()
            for p in players['players']:
                print(f"玩家 {p['name']} 在 {p.get('distance', '未知')} 格外")
        """
        result = await bot_client.execute_action("listPlayers", {})
        self.results.append({"action": "listPlayers", "result": result})
        return result
    
    async def canReach(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """检查坐标是否可达（不实际移动）"""
        result = await bot_client.execute_action("canReach", {"x": x, "y": y, "z": z})
        self.results.append({"action": "canReach", "result": result})
        return result
    
    async def getPathTo(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """获取到坐标的路径（不实际移动）"""
        result = await bot_client.execute_action("getPathTo", {"x": x, "y": y, "z": z})
        self.results.append({"action": "getPathTo", "result": result})
        return result
    
    # ===== 合成相关方法 =====
    
    async def craft(self, itemName: str, count: int = 1) -> Dict[str, Any]:
        """
        合成物品
        
        Args:
            itemName: 要合成的物品名称（如 oak_planks, stick, crafting_table）
            count: 合成数量（默认1）
            
        Returns:
            合成结果
        """
        result = await bot_client.execute_action("craft", {
            "itemName": itemName, "count": count
        })
        self.results.append({"action": "craft", "result": result})
        return result
    
    async def listRecipes(self, itemName: str) -> Dict[str, Any]:
        """
        查看物品的合成配方
        
        Args:
            itemName: 物品名称
            
        Returns:
            配方列表
        """
        result = await bot_client.execute_action("listRecipes", {"itemName": itemName})
        self.results.append({"action": "listRecipes", "result": result})
        return result
    
    async def smelt(self, itemName: str, fuelName: str = None, count: int = 1) -> Dict[str, Any]:
        """
        使用熔炉烧制物品
        
        Args:
            itemName: 要烧制的物品（如 raw_iron, raw_gold, cobblestone）
            fuelName: 燃料名称（可选，默认自动选择）
            count: 烧制数量（默认1）
            
        Returns:
            烧制结果
        """
        params = {"itemName": itemName, "count": count}
        if fuelName:
            params["fuelName"] = fuelName
        result = await bot_client.execute_action("smelt", params)
        self.results.append({"action": "smelt", "result": result})
        return result
    
    async def openContainer(self, x: int, y: int, z: int) -> Dict[str, Any]:
        """
        打开容器（箱子、桶等）
        
        Args:
            x, y, z: 容器坐标
            
        Returns:
            容器内容
        """
        result = await bot_client.execute_action("openContainer", {"x": x, "y": y, "z": z})
        self.results.append({"action": "openContainer", "result": result})
        return result
    
    async def closeContainer(self) -> Dict[str, Any]:
        """关闭当前打开的容器"""
        result = await bot_client.execute_action("closeContainer", {})
        self.results.append({"action": "closeContainer", "result": result})
        return result
    
    async def depositItem(self, itemName: str, count: int = None) -> Dict[str, Any]:
        """
        向当前打开的容器存入物品
        
        Args:
            itemName: 物品名称
            count: 存入数量（可选，默认全部）
            
        Returns:
            存入结果
        """
        params = {"itemName": itemName}
        if count is not None:
            params["count"] = count
        result = await bot_client.execute_action("depositItem", params)
        self.results.append({"action": "depositItem", "result": result})
        return result
    
    async def withdrawItem(self, itemName: str, count: int = None) -> Dict[str, Any]:
        """
        从当前打开的容器取出物品
        
        Args:
            itemName: 物品名称
            count: 取出数量（可选，默认全部）
            
        Returns:
            取出结果
        """
        params = {"itemName": itemName}
        if count is not None:
            params["count"] = count
        result = await bot_client.execute_action("withdrawItem", params)
        self.results.append({"action": "withdrawItem", "result": result})
        return result
    
    async def findCraftingTable(self, maxDistance: int = 32) -> Dict[str, Any]:
        """
        寻找附近的工作台
        
        Args:
            maxDistance: 最大搜索距离（默认32）
            
        Returns:
            工作台位置信息
        """
        result = await bot_client.execute_action("findCraftingTable", {"maxDistance": maxDistance})
        self.results.append({"action": "findCraftingTable", "result": result})
        return result
    
    async def findFurnace(self, maxDistance: int = 32) -> Dict[str, Any]:
        """
        寻找附近的熔炉
        
        Args:
            maxDistance: 最大搜索距离（默认32）
            
        Returns:
            熔炉位置信息
        """
        result = await bot_client.execute_action("findFurnace", {"maxDistance": maxDistance})
        self.results.append({"action": "findFurnace", "result": result})
        return result
    
    async def findChest(self, maxDistance: int = 32) -> Dict[str, Any]:
        """
        寻找附近的箱子或木桶
        
        Args:
            maxDistance: 最大搜索距离（默认32）
            
        Returns:
            容器位置信息
        """
        result = await bot_client.execute_action("findChest", {"maxDistance": maxDistance})
        self.results.append({"action": "findChest", "result": result})
        return result
    
    # ===== 实体交互方法 =====
    
    async def mountEntity(self, entityType: str = None) -> Dict[str, Any]:
        """
        骑乘实体（马、船、矿车、猪等）
        
        Args:
            entityType: 实体类型（可选，如 horse, boat, minecart）
                       不指定则骑乘最近的可骑乘实体
            
        Returns:
            骑乘结果
            
        Example:
            await bot.mountEntity("horse")  # 骑马
            await bot.mountEntity("boat")   # 上船
            await bot.mountEntity()         # 骑乘最近的可骑乘实体
        """
        params = {}
        if entityType:
            params["entityType"] = entityType
        result = await bot_client.execute_action("mountEntity", params)
        self.results.append({"action": "mountEntity", "result": result})
        return result
    
    async def dismount(self) -> Dict[str, Any]:
        """
        从当前骑乘的实体上下来
        
        Returns:
            下马/下船结果
            
        Example:
            await bot.dismount()  # 下马/下船
        """
        result = await bot_client.execute_action("dismount", {})
        self.results.append({"action": "dismount", "result": result})
        return result
    
    async def useOnEntity(self, entityType: str, hand: str = "hand") -> Dict[str, Any]:
        """
        对实体使用物品/右键交互（喂动物、与村民交易、拴绳等）
        
        Args:
            entityType: 实体类型（如 cow, villager, pig）
            hand: 使用哪只手（hand 或 off-hand，默认 hand）
            
        Returns:
            交互结果
            
        Example:
            await bot.equipItem("wheat")
            await bot.useOnEntity("cow")  # 用小麦喂牛
            
            await bot.useOnEntity("villager")  # 与村民交易
        """
        result = await bot_client.execute_action("useOnEntity", {
            "entityType": entityType, "hand": hand
        })
        self.results.append({"action": "useOnEntity", "result": result})
        return result
    
    # ===== 数据查询方法 =====
    
    async def getRecipeData(self, itemName: str) -> Dict[str, Any]:
        """
        从 minecraft-data 获取物品的配方数据
        
        Args:
            itemName: 物品名称
            
        Returns:
            配方信息，包含材料需求和是否需要工作台
            
        Example:
            recipe = await bot.getRecipeData("wooden_pickaxe")
            if recipe.get("found"):
                for r in recipe["recipes"]:
                    print(f"材料: {r['ingredients']}, 需要工作台: {r['needsCraftingTable']}")
        """
        result = await bot_client.execute_action("getRecipeData", {"itemName": itemName})
        self.results.append({"action": "getRecipeData", "result": result})
        return result
    
    async def getAllRecipes(self) -> Dict[str, Any]:
        """
        获取所有可合成物品的配方数据
        
        Returns:
            包含所有配方的字典，可用于构建配方缓存
            
        Example:
            all_recipes = await bot.getAllRecipes()
            # 检查某物品是否可合成
            if "diamond_pickaxe" in all_recipes["recipes"]:
                print("钻石镐可以合成")
        """
        result = await bot_client.execute_action("getAllRecipes", {})
        self.results.append({"action": "getAllRecipes", "result": result})
        return result
    
    async def getObservation(self) -> Dict[str, Any]:
        """获取当前观察状态"""
        return await bot_client.get_observation()
    
    async def getStatus(self) -> Dict[str, Any]:
        """获取Bot状态"""
        return await bot_client.get_status()
    
    async def getPosition(self) -> Dict[str, Any]:
        """获取当前位置"""
        observation = await bot_client.get_observation()
        return observation.get("position", {"x": 0, "y": 0, "z": 0})
    
    async def getHealth(self) -> Dict[str, Any]:
        """获取生命值和饥饿值"""
        observation = await bot_client.get_observation()
        return observation.get("health", {"health": 20, "food": 20})
    
    # ===== 事件等待方法 =====
    
    async def waitForEvent(
        self,
        event_type: str,
        filter_func = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        等待特定类型的游戏事件
        
        Args:
            event_type: 事件类型，支持的类型包括:
                - 'playerCollect': 玩家捡起物品
                - 'chat': 聊天消息
                - 'health': 生命值变化
                - 'death': 死亡
                - 'spawn': 重生
                - 'itemDrop': 物品掉落
                - 'entitySpawn': 实体生成
            filter_func: 可选的过滤函数，接收事件数据，返回 True 表示匹配
            timeout: 超时时间（秒），默认 30 秒
            
        Returns:
            匹配的事件数据，超时返回 None
            
        Example:
            # 等待某个玩家捡起物品
            event = await bot.waitForEvent(
                "playerCollect",
                filter_func=lambda e: e.get("collector", {}).get("name") == "Steve",
                timeout=10.0
            )
            if event:
                print(f"玩家 {event['collector']['name']} 捡起了物品")
            else:
                print("超时，没有玩家捡起物品")
                
            # 等待聊天消息
            event = await bot.waitForEvent(
                "chat",
                filter_func=lambda e: "hello" in e.get("message", "").lower(),
                timeout=60.0
            )
        """
        self.log(f"等待事件: {event_type} (超时: {timeout}秒)")
        result = await bot_client.wait_for_event(event_type, filter_func, timeout)
        
        if result:
            self.log(f"收到事件: {event_type}")
            self.results.append({"action": f"waitForEvent:{event_type}", "result": result})
        else:
            self.log(f"等待事件超时: {event_type}")
            self.results.append({"action": f"waitForEvent:{event_type}", "result": {"timeout": True}})
        
        return result
    
    async def waitForPlayerCollect(
        self,
        player_name: str = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        等待玩家捡起物品（playerCollect 事件的便捷方法）
        
        Args:
            player_name: 可选，指定等待的玩家名。不指定则等待任意玩家
            timeout: 超时时间（秒），默认 30 秒
            
        Returns:
            事件数据，包含 collector 和 collected 信息，超时返回 None
            
        Example:
            # 等待 Steve 捡起物品
            event = await bot.waitForPlayerCollect("Steve", timeout=10.0)
            if event:
                print(f"Steve 捡起了物品")
            
            # 等待任意玩家捡起
            event = await bot.waitForPlayerCollect(timeout=15.0)
        """
        if player_name:
            filter_func = lambda e: e.get("collector", {}).get("name") == player_name
        else:
            filter_func = None
        
        return await self.waitForEvent("playerCollect", filter_func, timeout)
    
    async def waitForChat(
        self,
        from_player: str = None,
        contains: str = None,
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        等待聊天消息（chat 事件的便捷方法）
        
        Args:
            from_player: 可选，只等待来自特定玩家的消息
            contains: 可选，消息必须包含的文本
            timeout: 超时时间（秒），默认 30 秒
            
        Returns:
            事件数据，包含 username 和 message，超时返回 None
            
        Example:
            # 等待来自 Steve 的消息
            event = await bot.waitForChat(from_player="Steve", timeout=30.0)
            
            # 等待包含 "yes" 的消息
            event = await bot.waitForChat(contains="yes", timeout=30.0)
        """
        def filter_func(e):
            if from_player and e.get("username") != from_player:
                return False
            if contains and contains.lower() not in e.get("message", "").lower():
                return False
            return True
        
        return await self.waitForEvent("chat", filter_func, timeout)
    
    # ===== 技能库相关方法 =====
    
    def listSkills(self) -> List[Dict[str, Any]]:
        """
        列出所有可用技能
        
        Returns:
            技能列表，每个包含 name, description, params
        """
        skills = skill_manager.list_skills()
        self.log(f"已保存的技能: {[s['name'] for s in skills]}")
        return skills
    
    def getSkill(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取技能详情
        
        Args:
            name: 技能名称
            
        Returns:
            技能信息，包含代码
        """
        skill = skill_manager.get_skill(name)
        if skill:
            self.log(f"获取技能: {name}")
        else:
            self.log(f"技能不存在: {name}")
        return skill
    
    def saveSkill(self, name: str, description: str, code: str,
                  params: List[str] = None) -> Dict[str, Any]:
        """
        保存新技能
        
        Args:
            name: 技能名称
            description: 技能描述
            code: 技能代码（函数体，不含async def声明）
            params: 参数列表（可选）
            
        Returns:
            保存结果
            
        Example:
            bot.saveSkill(
                name="采集木头",
                description="寻找并采集附近的木头",
                code='''
wood = await bot.findBlock("oak_log")
if wood.get("found"):
    await bot.goTo(wood["x"], wood["y"], wood["z"])
    await bot.collectBlock("oak_log")
    return "采集成功"
return "没找到木头"
''',
                params=[]
            )
        """
        result = skill_manager.save_skill(name, description, code, params or [])
        if result.get("success"):
            self.log(f"技能已保存: {name}")
        else:
            self.log(f"保存失败: {result.get('error')}")
        return result
    
    def deleteSkill(self, name: str) -> Dict[str, Any]:
        """
        删除技能
        
        Args:
            name: 技能名称
            
        Returns:
            删除结果
        """
        result = skill_manager.delete_skill(name)
        self.log(f"删除技能 {name}: {result}")
        return result
    
    async def useSkill(self, name: str, **kwargs) -> Any:
        """
        调用已保存的技能
        
        Args:
            name: 技能名称
            **kwargs: 技能参数
            
        Returns:
            技能执行结果
            
        Example:
            result = await bot.useSkill("采集木头")
        """
        skill = skill_manager.get_skill(name)
        if not skill:
            error_msg = f"技能 '{name}' 不存在"
            self.log(error_msg)
            return {"success": False, "error": error_msg}
        
        self.log(f"执行技能: {name}")
        
        try:
            # 获取技能代码
            full_code = skill.get('full_code', '')
            
            # 动态执行技能代码
            skill_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'abs': abs,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'round': round,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'isinstance': isinstance,
                    'True': True,
                    'False': False,
                    'None': None,
                },
                'asyncio': asyncio,
            }
            
            skill_locals = {}
            exec(compile(full_code, f'<skill:{name}>', 'exec'), skill_globals, skill_locals)
            
            # 找到技能函数
            func_name = skill_manager._safe_func_name(name)
            if func_name not in skill_locals:
                return {"success": False, "error": f"技能函数 {func_name} 未定义"}
            
            skill_func = skill_locals[func_name]
            
            # 执行技能
            result = await skill_func(self, **kwargs)
            
            self.results.append({"action": f"skill:{name}", "result": result})
            return result
            
        except Exception as e:
            error_msg = f"技能执行失败: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg, "traceback": traceback.format_exc()}


class ScriptExecutor:
    """
    Safe Python script executor with timeout and restrictions
    """
    
    def __init__(self, timeout: float = 120.0):
        self.timeout = timeout
        self.allowed_modules = {
            'asyncio', 'math', 'random', 'json', 'time', 're'
        }
    
    async def execute(self, script: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """
        Execute Python script code
        
        The code should define an async function called 'main' that takes 'bot' as parameter:
        
        async def main(bot):
            result = await bot.findBlock('diamond_ore')
            if result['found']:
                await bot.goTo(result['x'], result['y'], result['z'])
            return "Done!"
        
        Args:
            script: The Python code to execute
            timeout: Execution timeout in seconds (uses default if not provided)
        """
        bot_api = BotAPI()
        effective_timeout = timeout if timeout is not None else self.timeout
        
        # 捕获stdout
        old_stdout = sys.stdout
        sys.stdout = mystdout = StringIO()
        
        try:
            # 创建安全的执行环境
            safe_globals = {
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'str': str,
                    'int': int,
                    'float': float,
                    'bool': bool,
                    'list': list,
                    'dict': dict,
                    'tuple': tuple,
                    'set': set,
                    'abs': abs,
                    'min': min,
                    'max': max,
                    'sum': sum,
                    'round': round,
                    'sorted': sorted,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'isinstance': isinstance,
                    'True': True,
                    'False': False,
                    'None': None,
                },
                'asyncio': asyncio,
                'bot': bot_api,
            }
            
            safe_locals = {}
            
            # 编译并执行代码
            exec(compile(script, '<script>', 'exec'), safe_globals, safe_locals)
            
            # 检查是否定义了main函数
            if 'main' not in safe_locals:
                return {
                    "success": False,
                    "error": "Script must define an async function 'main(bot)'",
                    "logs": bot_api.logs
                }
            
            main_func = safe_locals['main']
            
            # 执行main函数，带超时
            import time
            start_time = time.time()
            try:
                result = await asyncio.wait_for(
                    main_func(bot_api),
                    timeout=effective_timeout
                )
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Script execution timed out after {effective_timeout} seconds",
                    "logs": bot_api.logs,
                    "actions": bot_api.results
                }
            
            execution_time = time.time() - start_time
            
            # 获取stdout输出
            output = mystdout.getvalue()
            
            return {
                "success": True,
                "result": result,
                "output": output,
                "logs": bot_api.logs,
                "actions": bot_api.results,
                "action_count": len(bot_api.results),
                "execution_time": round(execution_time, 2)
            }
            
        except SyntaxError as e:
            return {
                "success": False,
                "error": f"Syntax error: {str(e)}",
                "logs": bot_api.logs
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Execution error: {str(e)}",
                "traceback": traceback.format_exc(),
                "logs": bot_api.logs,
                "actions": bot_api.results
            }
        finally:
            sys.stdout = old_stdout


# 全局执行器实例，默认超时5分钟
script_executor = ScriptExecutor(timeout=300.0)