"""
技能: 挖矿
描述: 自动寻找并采集指定类型的矿石，支持自动挖开挡路的方块
"""

async def 挖矿(bot, oreType="iron_ore", count=5):
    """
    自动寻找并采集指定矿石，会自动挖开挡路的方块
    
    策略：
    1. 优先寻找低处、距离近的矿石
    2. 如果矿石在采集范围内（约4格）且无遮挡，直接挖掘
    3. 否则使用 collectBlock 走近并挖掘
    4. 如果 collectBlock 失败，尝试挖掘通道过去
    
    Args:
        bot: BotAPI实例
        oreType: 矿石类型（默认iron_ore），支持:
                 - coal_ore (煤矿)
                 - iron_ore (铁矿)
                 - copper_ore (铜矿)
                 - gold_ore (金矿)
                 - diamond_ore (钻石矿)
                 - emerald_ore (绿宝石矿)
                 - lapis_ore (青金石矿)
                 - redstone_ore (红石矿)
        count: 要采集的数量（默认5）
    
    Returns:
        采集结果
    """
    
    # 内嵌辅助函数：装备最好的镐子
    async def equip_best_pickaxe():
        """装备最好的镐子"""
        pickaxe_priority = [
            "netherite_pickaxe",
            "diamond_pickaxe",
            "iron_pickaxe",
            "golden_pickaxe",
            "stone_pickaxe",
            "wooden_pickaxe",
        ]
        
        inventory = await bot.viewInventory()
        items = inventory.get("inventory", [])
        
        for pickaxe in pickaxe_priority:
            for item in items:
                if item.get("name") == pickaxe:
                    result = await bot.equipItem(pickaxe)
                    if result.get("success"):
                        bot.log(f"装备了 {pickaxe}")
                        return pickaxe
        
        bot.log("没有找到镐子，使用空手")
        return None
    
    # 内嵌辅助函数：获取当前位置
    async def get_bot_position():
        """获取bot当前位置"""
        status = await bot.getStatus()
        return status.get("position", {})
    
    # 内嵌辅助函数：计算两点距离
    def calc_distance(pos1, pos2):
        """计算3D距离"""
        dx = pos1.get("x", 0) - pos2.get("x", 0)
        dy = pos1.get("y", 0) - pos2.get("y", 0)
        dz = pos1.get("z", 0) - pos2.get("z", 0)
        return (dx**2 + dy**2 + dz**2) ** 0.5
    
    # 内嵌辅助函数：检查是否可以直接挖掘（在范围内且无遮挡）
    async def can_direct_mine(target_pos):
        """
        检查目标方块是否可以直接挖掘（不需要移动）
        条件：距离在4格以内，且视线中间没有阻挡
        
        Returns:
            bool: 是否可以直接挖掘
        """
        current_pos = await get_bot_position()
        distance = calc_distance(current_pos, target_pos)
        
        # 超过4格肯定不行
        if distance > 4.5:
            return False
        
        # 检查视线是否有阻挡
        # 简化检查：检查从当前位置到目标位置的直线路径上是否有实心方块
        cur_x = current_pos.get("x", 0)
        cur_y = current_pos.get("y", 0) + 1.6  # 眼睛高度
        cur_z = current_pos.get("z", 0)
        
        tar_x = target_pos.get("x", 0) + 0.5  # 方块中心
        tar_y = target_pos.get("y", 0) + 0.5
        tar_z = target_pos.get("z", 0) + 0.5
        
        # 计算方向
        dx = tar_x - cur_x
        dy = tar_y - cur_y
        dz = tar_z - cur_z
        
        steps = int(distance * 2)  # 每0.5格检查一次
        if steps < 1:
            steps = 1
        
        # 透明或非阻挡方块
        non_blocking = ["air", "water", "lava", "cave_air", "void_air", "torch", 
                        "wall_torch", "redstone_torch", "soul_torch", "lantern",
                        "soul_lantern", "chain", "iron_bars", "glass", "glass_pane"]
        
        for i in range(1, steps):
            t = i / steps
            check_x = int(cur_x + dx * t)
            check_y = int(cur_y + dy * t)
            check_z = int(cur_z + dz * t)
            
            # 跳过目标方块本身
            if (check_x == int(target_pos.get("x")) and 
                check_y == int(target_pos.get("y")) and 
                check_z == int(target_pos.get("z"))):
                continue
            
            block_result = await bot.getBlockAt(check_x, check_y, check_z)
            if block_result.get("success"):
                block = block_result.get("block", {})
                block_name = block.get("name", "air")
                
                # 如果遇到实心方块，说明有阻挡
                if block_name not in non_blocking:
                    bot.log(f"视线被 {block_name} 在 ({check_x}, {check_y}, {check_z}) 阻挡")
                    return False
        
        return True
    
    # 内嵌辅助函数：挖掘到目标位置（挖开中间的方块）
    async def dig_to_target(target_pos, max_attempts=30):
        """
        挖掘前往目标位置，会挖开中间挡路的方块
        返回是否成功到达目标附近
        """
        for attempt in range(max_attempts):
            current_pos = await get_bot_position()
            distance = calc_distance(current_pos, target_pos)
            
            # 如果已经足够近（4格内），返回成功
            if distance <= 4.0:
                return True
            
            # 尝试先直接走过去
            go_result = await bot.goTo(target_pos.get("x"), target_pos.get("y"), target_pos.get("z"))
            
            if go_result.get("success"):
                return True
            
            # 走不过去，需要挖掘
            current_pos = await get_bot_position()
            cur_x = current_pos.get("x", 0)
            cur_y = current_pos.get("y", 0)
            cur_z = current_pos.get("z", 0)
            
            tar_x = target_pos.get("x", 0)
            tar_y = target_pos.get("y", 0)
            tar_z = target_pos.get("z", 0)
            
            # 计算方向
            dx = tar_x - cur_x
            dy = tar_y - cur_y
            dz = tar_z - cur_z
            
            # 归一化方向
            dist = max(0.1, (dx**2 + dy**2 + dz**2) ** 0.5)
            dx = dx / dist
            dy = dy / dist
            dz = dz / dist
            
            # 不可挖掘的方块
            unbreakable = ["air", "water", "lava", "cave_air", "void_air", "bedrock", "barrier", "command_block"]
            
            # 检查前方需要挖掘的方块
            blocks_to_dig = []
            
            # 检查前方1-2格的方块（水平方向）
            for step in [1, 2]:
                check_x = int(cur_x + dx * step)
                check_z = int(cur_z + dz * step)
                
                # 检查脚下和头部高度
                for y_offset in [0, 1]:
                    check_y = int(cur_y) + y_offset
                    block_result = await bot.getBlockAt(check_x, check_y, check_z)
                    if block_result.get("success"):
                        block = block_result.get("block", {})
                        block_name = block.get("name", "air")
                        if block_name not in unbreakable:
                            blocks_to_dig.append({
                                "x": check_x,
                                "y": check_y,
                                "z": check_z,
                                "name": block_name
                            })
            
            # 如果目标在上方，需要挖掘上方的方块
            if dy > 0.3:
                check_x = int(cur_x)
                check_y = int(cur_y) + 2
                check_z = int(cur_z)
                block_result = await bot.getBlockAt(check_x, check_y, check_z)
                if block_result.get("success"):
                    block = block_result.get("block", {})
                    block_name = block.get("name", "air")
                    if block_name not in unbreakable:
                        blocks_to_dig.append({
                            "x": check_x,
                            "y": check_y,
                            "z": check_z,
                            "name": block_name
                        })
            
            # 如果目标在下方，需要挖掘脚下的方块
            if dy < -0.3:
                check_x = int(cur_x)
                check_y = int(cur_y) - 1
                check_z = int(cur_z)
                block_result = await bot.getBlockAt(check_x, check_y, check_z)
                if block_result.get("success"):
                    block = block_result.get("block", {})
                    block_name = block.get("name", "air")
                    if block_name not in unbreakable:
                        blocks_to_dig.append({
                            "x": check_x,
                            "y": check_y,
                            "z": check_z,
                            "name": block_name
                        })
            
            if not blocks_to_dig:
                bot.log(f"无法确定需要挖掘的方块，尝试次数: {attempt + 1}")
                await bot.wait(1)
                continue
            
            # 挖掘找到的方块
            for block_info in blocks_to_dig[:3]:  # 最多挖3个
                bot.log(f"挖掘挡路方块: {block_info['name']} 在 ({block_info['x']}, {block_info['y']}, {block_info['z']})")
                await equip_best_pickaxe()
                dig_result = await bot.collectBlock(block_info["name"])
                await bot.wait(0.2)
            
            await bot.wait(0.5)
        
        return False
    
    # 矿石对应的深层矿石名称
    ore_variants = {
        "coal_ore": ["coal_ore", "deepslate_coal_ore"],
        "iron_ore": ["iron_ore", "deepslate_iron_ore"],
        "copper_ore": ["copper_ore", "deepslate_copper_ore"],
        "gold_ore": ["gold_ore", "deepslate_gold_ore"],
        "diamond_ore": ["diamond_ore", "deepslate_diamond_ore"],
        "emerald_ore": ["emerald_ore", "deepslate_emerald_ore"],
        "lapis_ore": ["lapis_ore", "deepslate_lapis_ore"],
        "redstone_ore": ["redstone_ore", "deepslate_redstone_ore"],
    }
    
    # 获取所有可能的矿石名称
    if oreType in ore_variants:
        target_ores = ore_variants[oreType]
    else:
        target_ores = [oreType]
    
    bot.log(f"开始挖矿: {oreType}，目标: {count} 个")
    await bot.chat(f"开始挖 {oreType} 喵~ 目标 {count} 个")
    
    # 先装备镐子
    current_pickaxe = await equip_best_pickaxe()
    if not current_pickaxe:
        await bot.chat("没有镐子，无法挖矿喵...")
        return {
            "success": False,
            "mined": 0,
            "target": count,
            "message": "没有镐子，无法挖矿"
        }
    
    mined = 0
    failed_attempts = 0
    max_failed = 15
    tried_positions = set()
    
    while mined < count and failed_attempts < max_failed:
        # 检查生命值和饥饿值
        health = await bot.getHealth()
        if health.get("health", 20) <= 6:
            await bot.chat("血量太低了，先回去喵...")
            return {
                "success": mined > 0,
                "mined": mined,
                "target": count,
                "message": f"因生命值过低停止，已采集 {mined}/{count}"
            }
        
        if health.get("food", 20) <= 6:
            bot.log("饥饿值低，尝试吃东西")
            await bot.eat()
        
        # 装备最佳镐子
        await equip_best_pickaxe()
        
        # 获取当前位置
        current_pos = await get_bot_position()
        my_y = current_pos.get("y", 64)
        
        # 寻找最近的矿石（优先选择距离近且y坐标接近的）
        best_ore = None
        best_score = float('inf')
        
        for ore_name in target_ores:
            result = await bot.findBlock(ore_name, 48)
            if result.get("found"):
                pos = result.get("position", {})
                pos_key = f"{pos.get('x')},{pos.get('y')},{pos.get('z')}"
                
                if pos_key in tried_positions:
                    continue
                
                distance = result.get("distance", 999)
                y_diff = abs(pos.get("y", 0) - my_y)
                
                # 计算分数：距离 + y坐标差异惩罚
                # 优先选择同一高度附近的矿石
                if y_diff > 5:
                    y_penalty = y_diff * 2
                else:
                    y_penalty = 0
                
                score = distance + y_penalty
                
                if score < best_score:
                    best_score = score
                    best_ore = {
                        "name": ore_name,
                        "position": pos,
                        "distance": distance,
                        "y_diff": y_diff
                    }
        
        if not best_ore:
            bot.log("附近没有找到矿石")
            failed_attempts += 1
            
            if failed_attempts >= 10:
                await bot.chat(f"找不到 {oreType} 了喵~ 已采集 {mined}/{count}")
                return {
                    "success": mined > 0,
                    "mined": mined,
                    "target": count,
                    "message": f"附近没有矿石了，已采集 {mined}/{count}"
                }
            
            await bot.wait(2)
            continue
        
        pos = best_ore["position"]
        ore_name = best_ore["name"]
        pos_key = f"{pos.get('x')},{pos.get('y')},{pos.get('z')}"
        
        bot.log(f"找到 {ore_name} 在 ({pos.get('x')}, {pos.get('y')}, {pos.get('z')}), 距离: {best_ore['distance']:.1f}, y差: {best_ore['y_diff']}")
        
        # 检查是否可以直接挖掘（在范围内且无遮挡）
        can_direct = await can_direct_mine(pos)
        
        if can_direct:
            bot.log("矿石在采集范围内且无遮挡，直接挖掘")
            # 直接使用 collectBlock，它会处理挖掘
            collect_result = await bot.collectBlock(ore_name)
            
            if collect_result.get("success"):
                mined += 1
                failed_attempts = 0
                bot.log(f"直接采集成功! 进度: {mined}/{count}")
                
                if mined < count and mined % 3 == 0:
                    await bot.chat(f"挖到第 {mined} 个啦喵~ ({mined}/{count})")
            else:
                # 直接采集失败，标记位置
                bot.log(f"直接采集失败: {collect_result.get('message', '未知错误')}")
                tried_positions.add(pos_key)
                failed_attempts += 1
        else:
            # 不能直接挖掘，需要移动或挖掘通道
            bot.log("矿石不在直接采集范围内，尝试接近...")
            
            # 先尝试使用 collectBlock（它会自动走近）
            collect_result = await bot.collectBlock(ore_name)
            
            if collect_result.get("success"):
                mined += 1
                failed_attempts = 0
                bot.log(f"采集成功! 进度: {mined}/{count}")
                
                if mined < count and mined % 3 == 0:
                    await bot.chat(f"挖到第 {mined} 个啦喵~ ({mined}/{count})")
            else:
                error_msg = collect_result.get("message", "未知错误")
                bot.log(f"collectBlock失败: {error_msg}，尝试挖掘通道...")
                
                # 尝试挖掘到目标位置
                reached = await dig_to_target(pos, max_attempts=20)
                
                if reached:
                    # 再次尝试采集
                    await equip_best_pickaxe()
                    collect_result2 = await bot.collectBlock(ore_name)
                    
                    if collect_result2.get("success"):
                        mined += 1
                        failed_attempts = 0
                        bot.log(f"挖掘后采集成功! 进度: {mined}/{count}")
                        
                        if mined < count and mined % 3 == 0:
                            await bot.chat(f"挖到第 {mined} 个啦喵~ ({mined}/{count})")
                    else:
                        bot.log(f"挖掘后仍然采集失败，标记该位置")
                        tried_positions.add(pos_key)
                        failed_attempts += 1
                else:
                    bot.log(f"无法到达矿石位置，标记并跳过")
                    tried_positions.add(pos_key)
                    failed_attempts += 1
        
        await bot.wait(0.5)
    
    # 完成
    if mined >= count:
        await bot.chat(f"挖矿完成喵~ 共挖了 {mined} 个 {oreType}!")
        return {
            "success": True,
            "mined": mined,
            "target": count,
            "oreType": oreType,
            "message": f"成功采集 {mined} 个 {oreType}"
        }
    else:
        await bot.chat(f"挖矿中断喵... 只挖到 {mined}/{count} 个")
        return {
            "success": False,
            "mined": mined,
            "target": count,
            "oreType": oreType,
            "message": f"采集中断，只采集了 {mined}/{count} 个"
        }