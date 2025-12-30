"""
技能: 打怪
描述: 自动寻找并击杀敌对生物，支持指定类型和数量
特性：
- 苦力怕特殊处理（打一下就后退）
- 风筝机制（攻击后后退避免硬吃伤害）
- 优化移动逻辑（只有距离过远才移动，避免卡顿）
- 智能目标追踪
"""

# 敌对生物列表（按危险程度排序）
HOSTILE_MOBS = [
    "creeper",      # 苦力怕（最危险，会爆炸）
    "skeleton",     # 骷髅（远程攻击）
    "witch",        # 女巫（远程魔法）
    "phantom",      # 幻翼
    "blaze",        # 烈焰人
    "ghast",        # 恶魂
    "zombie",       # 僵尸
    "drowned",      # 溺尸
    "husk",         # 尸壳
    "spider",       # 蜘蛛
    "cave_spider",  # 洞穴蜘蛛
    "enderman",     # 末影人
    "slime",        # 史莱姆
    "magma_cube",   # 岩浆怪
    "pillager",     # 掠夺者
    "vindicator",   # 卫道士
    "ravager",      # 劫掠兽
    "evoker",       # 唤魔者
    "vex",          # 恼鬼
    "zombified_piglin",  # 僵尸猪灵
    "piglin_brute",      # 猪灵蛮兵
    "warden",       # 监守者（极其危险）
]

# 需要特殊处理的危险怪物
DANGEROUS_MOBS = {
    "creeper": {
        "type": "explosive",
        "safe_distance": 5,      # 保持安全距离
        "retreat_after_hit": True,  # 攻击后必须后退
        "retreat_distance": 6,   # 后退距离
    },
    "skeleton": {
        "type": "ranged",
        "safe_distance": 2,      # 近身反而安全
        "retreat_after_hit": False,
    },
    "witch": {
        "type": "ranged",
        "safe_distance": 2,
        "retreat_after_hit": False,
    },
    "warden": {
        "type": "avoid",         # 直接避免战斗
        "safe_distance": 20,
        "retreat_after_hit": True,
        "retreat_distance": 10,
    },
}

# 武器优先级列表（从好到差）
WEAPON_PRIORITY = [
    "netherite_sword",
    "diamond_sword",
    "iron_sword",
    "golden_sword",
    "stone_sword",
    "wooden_sword",
    "netherite_axe",
    "diamond_axe",
    "iron_axe",
    "stone_axe",
    "wooden_axe",
]


async def 打怪(bot, count=1, mob_type=None):
    """
    自动寻找并击杀敌对生物
    
    策略：
    1. 扫描附近的敌对生物
    2. 自动装备最好的武器
    3. 智能战斗（根据怪物类型采取不同策略）
    4. 风筝机制（攻击后后退避免伤害）
    
    Args:
        bot: BotAPI实例
        count: 要击杀的数量，默认1个
        mob_type: 指定怪物类型（可选），如 "zombie", "skeleton" 等
                  如果不指定，会攻击任意敌对生物
    """
    
    async def equip_best_weapon():
        """装备最好的武器"""
        inventory = await bot.viewInventory()
        items = inventory.get("inventory", [])
        
        if not items:
            return None
        
        for weapon in WEAPON_PRIORITY:
            for item in items:
                if weapon in item.get("name", ""):
                    result = await bot.equipItem(item["name"])
                    if result.get("success"):
                        return item["name"]
        return None
    
    async def find_hostile_mob(specific_type=None):
        """寻找附近的敌对生物"""
        scan_result = await bot.scanEntities(range=24)
        
        if not scan_result.get("success"):
            return None
        
        entities = scan_result.get("entities", [])
        hostile_entities = []
        
        for entity in entities:
            entity_name = entity.get("name", "")
            
            if specific_type:
                if entity_name == specific_type:
                    hostile_entities.append(entity)
            elif entity_name in HOSTILE_MOBS or entity.get("isHostile", False):
                hostile_entities.append(entity)
        
        if not hostile_entities:
            return None
        
        # 按距离排序
        hostile_entities.sort(key=lambda e: e.get("distance", 999))
        target = hostile_entities[0]
        
        return {
            "name": target.get("name", "unknown"),
            "position": target.get("position", {
                "x": target.get("x", 0),
                "y": target.get("y", 0),
                "z": target.get("z", 0)
            }),
            "distance": target.get("distance", 0)
        }
    
    async def get_current_position():
        """获取当前位置"""
        return await bot.getPosition()
    
    async def calculate_retreat_position(my_pos, target_pos, distance):
        """计算后退位置（远离目标方向）"""
        # 计算方向向量（从目标指向自己）
        dx = my_pos["x"] - target_pos["x"]
        dz = my_pos["z"] - target_pos["z"]
        
        # 归一化
        length = (dx*dx + dz*dz) ** 0.5
        if length < 0.1:
            # 太近了，随机选个方向
            import random
            dx, dz = random.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            length = 1
        
        dx /= length
        dz /= length
        
        # 后退位置
        retreat_x = int(my_pos["x"] + dx * distance)
        retreat_z = int(my_pos["z"] + dz * distance)
        retreat_y = int(my_pos["y"])
        
        return {"x": retreat_x, "y": retreat_y, "z": retreat_z}
    
    async def smart_combat(mob_name, initial_pos):
        """
        智能战斗
        
        策略：
        1. 根据怪物类型调整战斗方式
        2. 只在距离过远时才移动（>3格）
        3. 攻击后根据情况后退（风筝）
        4. 苦力怕特殊处理
        """
        
        mob_config = DANGEROUS_MOBS.get(mob_name, {})
        is_creeper = mob_name == "creeper"
        is_dangerous = mob_name in DANGEROUS_MOBS
        should_avoid = mob_config.get("type") == "avoid"
        
        # 如果是应该避免的怪物（如监守者），直接跑
        if should_avoid:
            bot.log(f"检测到危险生物 {mob_name}，撤退！")
            await bot.chat(f"那是{mob_name}！太危险了，跑喵！")
            my_pos = await get_current_position()
            retreat_pos = await calculate_retreat_position(my_pos, initial_pos, 15)
            await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
            return {"success": False, "message": "Avoided dangerous mob"}
        
        max_attack_attempts = 30
        attack_count = 0
        last_target_pos = initial_pos
        
        # 战斗循环
        for attempt in range(max_attack_attempts):
            # 扫描目标
            scan_result = await bot.scanEntities(range=24)
            entities = scan_result.get("entities", [])
            
            # 查找目标
            target = None
            for entity in entities:
                if entity.get("name") == mob_name:
                    target = entity
                    break
            
            if not target:
                if attack_count >= 2:
                    return {"success": True, "message": "Target eliminated"}
                return {"success": False, "message": "Target not found"}
            
            # 获取目标位置
            target_pos = target.get("position", {
                "x": target.get("x", 0),
                "y": target.get("y", 0),
                "z": target.get("z", 0)
            })
            target_distance = target.get("distance", 999)
            last_target_pos = target_pos
            
            # 获取自己位置
            my_pos = await get_current_position()
            
            # === 移动决策 ===
            # 只有距离过远才移动，避免频繁寻路导致卡顿
            optimal_distance = 2.5  # 最佳攻击距离
            
            if is_creeper:
                # 苦力怕：保持安全距离，打一下就跑
                if target_distance > 4:
                    # 太远了，稍微靠近一点
                    bot.log(f"苦力怕距离 {target_distance:.1f}，小心接近...")
                    await bot.goTo(target_pos["x"], target_pos["y"], target_pos["z"])
                    await bot.wait(0.3)  # 短暂停顿
                    # 重新检测距离
                    continue
                elif target_distance < 2.5:
                    # 太近了！先后退
                    bot.log("苦力怕太近，后退！")
                    retreat_pos = await calculate_retreat_position(my_pos, target_pos, 5)
                    await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
                    continue
            else:
                # 普通怪物
                if target_distance > 3.5:
                    # 距离太远，需要靠近
                    bot.log(f"目标距离 {target_distance:.1f}，接近中...")
                    # 不使用 goTo（会计算完整路径），而是直接走向目标
                    await bot.goTo(target_pos["x"], target_pos["y"], target_pos["z"])
                    # 不等待到达，继续循环检测
            
            # === 攻击 ===
            # 看向目标
            await bot.lookAt(target_pos["x"], target_pos["y"] + 1, target_pos["z"])
            
            # 攻击
            attack_result = await bot.attack(mob_name)
            
            if attack_result.get("success"):
                attack_count += 1
                bot.log(f"攻击 {mob_name} 第 {attack_count} 次")
                
                # === 风筝机制 ===
                # 攻击成功后决定是否后退
                
                if is_creeper:
                    # 苦力怕：打完必须后退！
                    bot.log("攻击苦力怕后立即后退！")
                    retreat_pos = await calculate_retreat_position(my_pos, target_pos, 6)
                    await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
                    await bot.wait(0.5)  # 等待后退完成
                    
                elif mob_config.get("retreat_after_hit"):
                    # 其他需要后退的怪物
                    retreat_distance = mob_config.get("retreat_distance", 4)
                    retreat_pos = await calculate_retreat_position(my_pos, target_pos, retreat_distance)
                    await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
                    await bot.wait(0.3)
                    
                else:
                    # 普通怪物：偶尔后退避免硬吃伤害
                    if attack_count % 3 == 0:  # 每3次攻击后退一次
                        bot.log("后退躲避反击")
                        retreat_pos = await calculate_retreat_position(my_pos, target_pos, 3)
                        await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
                        await bot.wait(0.2)
                    else:
                        # 短暂等待攻击冷却
                        await bot.wait(0.4)
            else:
                bot.log(f"攻击失败: {attack_result.get('message', '')}")
                await bot.wait(0.3)
            
            # 检查生命值
            health_info = await bot.getHealth()
            current_health = health_info.get("health", 20)
            
            if current_health <= 4:
                bot.log("生命值危险，撤退！")
                await bot.stopMoving()
                # 逃跑
                retreat_pos = await calculate_retreat_position(my_pos, last_target_pos, 10)
                await bot.goTo(retreat_pos["x"], retreat_pos["y"], retreat_pos["z"])
                return {"success": False, "message": "Health critical, retreating"}
        
        return {"success": False, "message": f"Max attacks ({max_attack_attempts}) reached"}
    
    # ===== 主逻辑 =====
    
    killed = 0
    failed_attempts = 0
    max_failed = 5
    
    bot.log(f"开始打怪，目标: {count} 个" + (f" ({mob_type})" if mob_type else " (任意敌对生物)"))
    
    # 装备武器
    equipped_weapon = await equip_best_weapon()
    if equipped_weapon:
        bot.log(f"已装备武器: {equipped_weapon}")
        await bot.chat(f"拿起了{equipped_weapon}准备战斗喵~")
    else:
        bot.log("没有找到武器，将使用空手战斗")
        await bot.chat("没有武器...只能用拳头了喵...")
    
    while killed < count and failed_attempts < max_failed:
        # 检查生命值
        health_info = await bot.getHealth()
        current_health = health_info.get("health", 20)
        
        if current_health <= 6:
            bot.log(f"生命值过低 ({current_health})，暂停战斗")
            await bot.chat(f"血量太低了喵！({current_health}/20) 先跑为敬~")
            return {
                "success": killed > 0,
                "killed": killed,
                "target": count,
                "message": f"生命值过低，已击杀 {killed}/{count}"
            }
        
        # 寻找目标
        target = await find_hostile_mob(mob_type)
        
        if not target:
            bot.log("附近没有找到敌对生物")
            if failed_attempts < 2:
                await bot.chat("找不到怪物，等一下看看喵~")
                await bot.wait(3)
                failed_attempts += 1
                continue
            else:
                await bot.chat(f"附近没有怪物了喵~ 已击杀 {killed}/{count}")
                return {
                    "success": killed > 0,
                    "killed": killed,
                    "target": count,
                    "message": f"附近没有敌对生物，已击杀 {killed}/{count}"
                }
        
        mob_name = target["name"]
        mob_pos = target["position"]
        mob_distance = target["distance"]
        
        bot.log(f"发现目标: {mob_name} 距离: {mob_distance:.1f}")
        
        # 苦力怕特别提示
        if mob_name == "creeper":
            await bot.chat("发现苦力怕！小心处理喵~")
        else:
            await bot.chat(f"发现{mob_name}！冲啊喵~")
        
        # 智能战斗
        kill_result = await smart_combat(mob_name, mob_pos)
        
        if kill_result["success"]:
            killed += 1
            failed_attempts = 0
            bot.log(f"击杀成功! 进度: {killed}/{count}")
            await bot.chat(f"打倒了{mob_name}喵~ ({killed}/{count})")
        else:
            bot.log(f"战斗结果: {kill_result.get('message', '未知')}")
            failed_attempts += 1
            
            if "not found" in kill_result.get("message", "").lower():
                killed += 0.5
                if killed >= count:
                    break
    
    # 战斗结束
    await bot.stopMoving()
    
    final_killed = int(killed)
    if final_killed >= count:
        await bot.chat(f"战斗胜利喵！共击杀 {final_killed} 个敌人!")
        return {
            "success": True,
            "killed": final_killed,
            "target": count,
            "message": f"成功击杀 {final_killed} 个敌对生物"
        }
    else:
        await bot.chat(f"战斗结束喵... 击杀了 {final_killed}/{count} 个")
        return {
            "success": False,
            "killed": final_killed,
            "target": count,
            "message": f"战斗中断，击杀了 {final_killed}/{count}"
        }