"""
丢给玩家技能

使用方法：
    await bot.useSkill("丢给玩家", player_name="玩家名", item_name="物品名", count=数量)
    
参数：
    player_name: 目标玩家名
    item_name: 要丢的物品名（如 diamond, apple, cobblestone）
    count: 丢的数量（可选，默认为1）
    timeout: 等待玩家捡起的超时时间（可选，默认30秒）

返回：
    成功被指定玩家捡起：
        {"success": True, "collected": True, "collected_by_target": True, "collector": "玩家名", ...}
    被其他玩家捡起：
        {"success": True, "collected": True, "collected_by_target": False, "collector": "其他玩家", ...}
    超时未被捡起：
        {"success": True, "collected": False, "timeout": True, ...}
    执行失败：
        {"success": False, "message": "错误信息"}
    
示例：
    # 丢一个钻石给 Steve
    result = await bot.useSkill("丢给玩家", player_name="Steve", item_name="diamond")
    
    if result["collected"]:
        if result["collected_by_target"]:
            print("Steve 成功捡起了钻石！")
        else:
            print(f"物品被 {result['collector']} 捡走了，不是 Steve！")
    else:
        print("超时了，没人捡起物品")
        
特点：
    - 使用物品实体 ID 精确匹配，避免其他物品捡起事件的干扰
    - 即使旁边有人捡其他东西也不会误判
    - 支持一次丢出多个物品（如64个钻石可能分成多个实体）
"""


async def skill_丢给玩家(bot, player_name: str, item_name: str, count: int = 1, timeout: float = 30.0):
    """
    给指定玩家丢物品，并等待确认谁捡起了物品
    
    工作流程：
    1. 检查背包中是否有指定物品
    2. 找到玩家位置
    3. 走到玩家附近（3格内）
    4. 丢出物品，获取所有丢出物品的实体ID列表
    5. 等待 playerCollect 事件，精确匹配任一实体ID
    6. 判断是否是目标玩家捡起，追踪所有物品的收集状态
    """
    
    bot.log(f"开始执行: 丢给玩家 {player_name} {count}个 {item_name}")
    
    # 1. 检查背包中是否有物品
    inventory = await bot.viewInventory()
    if not inventory.get("success"):
        return {"success": False, "message": "无法查看背包"}
    
    items = inventory.get("inventory", [])
    target_item = None
    for item in items:
        if item["name"] == item_name or item_name in item["name"]:
            target_item = item
            break
    
    if not target_item:
        return {"success": False, "message": f"背包中没有 {item_name}"}
    
    actual_count = min(count, target_item["count"])
    if target_item["count"] < count:
        bot.log(f"背包中只有 {target_item['count']} 个 {target_item['name']}，将丢出全部")
    
    bot.log(f"找到物品: {target_item['name']} x{target_item['count']}，将丢出 {actual_count} 个")
    
    # 2. 找到玩家
    players = await bot.listPlayers()
    if not players.get("success"):
        return {"success": False, "message": "无法获取玩家列表"}
    
    target_player = None
    for player in players.get("players", []):
        if player["name"] == player_name:
            target_player = player
            break
    
    if not target_player:
        return {"success": False, "message": f"找不到玩家 {player_name}，在线玩家: {[p['name'] for p in players.get('players', [])]}"}
    
    if not target_player.get("inRange"):
        return {"success": False, "message": f"玩家 {player_name} 不在视野范围内，无法确定位置"}
    
    player_pos = target_player["position"]
    bot.log(f"找到玩家 {player_name} 在 ({player_pos['x']}, {player_pos['y']}, {player_pos['z']})")
    
    # 3. 走到玩家附近
    distance = target_player.get("distance", 100)
    if distance > 3:
        bot.log(f"距离玩家 {distance:.1f} 格，正在接近...")
        
        # 走到玩家位置附近
        result = await bot.goTo(player_pos["x"], player_pos["y"], player_pos["z"])
        if not result.get("success"):
            # 即使没完全成功，检查是否足够近
            players = await bot.listPlayers()
            for p in players.get("players", []):
                if p["name"] == player_name and p.get("distance", 100) <= 5:
                    bot.log("已经足够接近玩家")
                    break
            else:
                return {"success": False, "message": f"无法接近玩家 {player_name}: {result.get('message', '')}"}
    
    # 4. 面向玩家
    # 重新获取玩家位置（玩家可能移动了）
    players = await bot.listPlayers()
    for p in players.get("players", []):
        if p["name"] == player_name and p.get("inRange"):
            player_pos = p["position"]
            break
    
    await bot.lookAt(player_pos["x"], player_pos["y"] + 1, player_pos["z"])  # 看向玩家眼睛高度
    
    # 5. 丢出物品，获取掉落物实体ID
    bot.log(f"丢出 {actual_count} 个 {target_item['name']}...")
    drop_result = await bot.dropItem(target_item["name"], actual_count)
    if not drop_result.get("success"):
        return {"success": False, "message": f"丢物品失败: {drop_result.get('message', '')}"}
    
    # 获取丢出物品的所有实体ID（一组物品可能分成多个实体）
    dropped_entity_ids = drop_result.get("droppedEntityIds", [])
    entity_count = drop_result.get("entityCount", 0)
    
    if dropped_entity_ids:
        bot.log(f"物品实体ID列表: {dropped_entity_ids} (共 {entity_count} 个实体)")
    else:
        # 回退兼容
        single_id = drop_result.get("droppedEntityId")
        if single_id:
            dropped_entity_ids = [single_id]
            bot.log(f"物品实体ID: {single_id}")
        else:
            bot.log("警告: 未能获取物品实体ID，将使用非精确匹配")
    
    bot.log(f"物品已丢出，等待有人捡起... (超时: {timeout}秒)")
    
    # 转换为集合以便快速查找
    dropped_entity_id_set = set(dropped_entity_ids)
    
    # 用于追踪收集状态
    collected_by = {}  # entity_id -> collector_name
    collected_events = []
    
    # 6. 等待 playerCollect 事件
    # 使用实体ID集合进行精确匹配
    if dropped_entity_ids:
        # 精确匹配：只匹配我们丢出的物品
        def entity_filter(event):
            collected = event.get("collected", {})
            collected_id = collected.get("id")
            return collected_id in dropped_entity_id_set
        
        # 等待第一个匹配事件
        event = await bot.waitForEvent("playerCollect", filter_func=entity_filter, timeout=timeout)
    else:
        # 回退到非精确匹配（任意捡起事件）
        event = await bot.waitForPlayerCollect(player_name=None, timeout=timeout)
    
    if event:
        collector_name = event.get("collector", {}).get("name", "未知")
        collector_type = event.get("collector", {}).get("type", "unknown")
        collected_info = event.get("collected", {})
        collected_entity_id = collected_info.get("id")
        
        bot.log(f"检测到捡起事件: {collector_name} ({collector_type}) 捡起了实体 {collected_entity_id}")
        
        # 记录收集信息
        if collected_entity_id:
            collected_by[collected_entity_id] = collector_name
        
        # 判断是否是目标玩家
        is_target = (collector_name == player_name)
        
        # 计算剩余未收集的实体
        remaining_entities = len(dropped_entity_id_set) - len(collected_by)
        
        if is_target:
            # 目标玩家成功捡起（至少一个）
            bot.log(f"✓ 成功: {player_name} 捡起了物品!")
            return {
                "success": True,
                "message": f"成功! {player_name} 捡起了 {actual_count} 个 {target_item['name']}",
                "collected": True,
                "collected_by_target": True,
                "target_player": player_name,
                "collector": collector_name,
                "collector_type": collector_type,
                "item_dropped": target_item["name"],
                "count_dropped": actual_count,
                "dropped_entity_ids": dropped_entity_ids,
                "entity_count": entity_count,
                "collected_entity_id": collected_entity_id,
                "remaining_entities": remaining_entities,
                "event": event
            }
        else:
            # 被其他玩家/实体捡走了
            bot.log(f"✗ 物品被 {collector_name} 捡走了，不是目标玩家 {player_name}")
            return {
                "success": True,  # 操作本身成功了（物品丢出去了）
                "message": f"物品被 {collector_name} 捡走了，不是目标玩家 {player_name}",
                "collected": True,
                "collected_by_target": False,
                "target_player": player_name,
                "collector": collector_name,
                "collector_type": collector_type,
                "item_dropped": target_item["name"],
                "count_dropped": actual_count,
                "dropped_entity_ids": dropped_entity_ids,
                "entity_count": entity_count,
                "collected_entity_id": collected_entity_id,
                "remaining_entities": remaining_entities,
                "event": event
            }
    else:
        # 超时，没有人捡起物品
        bot.log(f"✗ 等待超时 ({timeout}秒)，没有人捡起物品")
        return {
            "success": True,  # 物品确实丢出去了
            "message": f"物品已丢出，但 {timeout} 秒内没有人捡起",
            "collected": False,
            "collected_by_target": False,
            "timeout": True,
            "timeout_seconds": timeout,
            "target_player": player_name,
            "item_dropped": target_item["name"],
            "count_dropped": actual_count,
            "dropped_entity_ids": dropped_entity_ids,
            "entity_count": entity_count
        }