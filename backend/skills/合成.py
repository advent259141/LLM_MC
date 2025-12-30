"""
技能: 合成
描述: 合成指定物品，自动处理工作台和配方，支持递归合成缺失的材料
"""

# 常见的2x2配方（不需要工作台）
SIMPLE_RECIPES = {
    "oak_planks": {"材料": {"oak_log": 1}, "产出": 4},
    "birch_planks": {"材料": {"birch_log": 1}, "产出": 4},
    "spruce_planks": {"材料": {"spruce_log": 1}, "产出": 4},
    "jungle_planks": {"材料": {"jungle_log": 1}, "产出": 4},
    "acacia_planks": {"材料": {"acacia_log": 1}, "产出": 4},
    "dark_oak_planks": {"材料": {"dark_oak_log": 1}, "产出": 4},
    "mangrove_planks": {"材料": {"mangrove_log": 1}, "产出": 4},
    "cherry_planks": {"材料": {"cherry_log": 1}, "产出": 4},
    "stick": {"材料": {"_planks": 2}, "产出": 4},  # 任意木板
    "crafting_table": {"材料": {"_planks": 4}, "产出": 1},
}

# 需要工作台的3x3配方
TABLE_RECIPES = {
    "wooden_pickaxe": {"材料": {"_planks": 3, "stick": 2}, "产出": 1},
    "wooden_axe": {"材料": {"_planks": 3, "stick": 2}, "产出": 1},
    "wooden_shovel": {"材料": {"_planks": 1, "stick": 2}, "产出": 1},
    "wooden_sword": {"材料": {"_planks": 2, "stick": 1}, "产出": 1},
    "wooden_hoe": {"材料": {"_planks": 2, "stick": 2}, "产出": 1},
    "stone_pickaxe": {"材料": {"cobblestone": 3, "stick": 2}, "产出": 1},
    "stone_axe": {"材料": {"cobblestone": 3, "stick": 2}, "产出": 1},
    "stone_shovel": {"材料": {"cobblestone": 1, "stick": 2}, "产出": 1},
    "stone_sword": {"材料": {"cobblestone": 2, "stick": 1}, "产出": 1},
    "stone_hoe": {"材料": {"cobblestone": 2, "stick": 2}, "产出": 1},
    "iron_pickaxe": {"材料": {"iron_ingot": 3, "stick": 2}, "产出": 1},
    "iron_axe": {"材料": {"iron_ingot": 3, "stick": 2}, "产出": 1},
    "iron_shovel": {"材料": {"iron_ingot": 1, "stick": 2}, "产出": 1},
    "iron_sword": {"材料": {"iron_ingot": 2, "stick": 1}, "产出": 1},
    "iron_hoe": {"材料": {"iron_ingot": 2, "stick": 2}, "产出": 1},
    "diamond_pickaxe": {"材料": {"diamond": 3, "stick": 2}, "产出": 1},
    "diamond_axe": {"材料": {"diamond": 3, "stick": 2}, "产出": 1},
    "diamond_shovel": {"材料": {"diamond": 1, "stick": 2}, "产出": 1},
    "diamond_sword": {"材料": {"diamond": 2, "stick": 1}, "产出": 1},
    "diamond_hoe": {"材料": {"diamond": 2, "stick": 2}, "产出": 1},
    "golden_pickaxe": {"材料": {"gold_ingot": 3, "stick": 2}, "产出": 1},
    "golden_axe": {"材料": {"gold_ingot": 3, "stick": 2}, "产出": 1},
    "golden_shovel": {"材料": {"gold_ingot": 1, "stick": 2}, "产出": 1},
    "golden_sword": {"材料": {"gold_ingot": 2, "stick": 1}, "产出": 1},
    "golden_hoe": {"材料": {"gold_ingot": 2, "stick": 2}, "产出": 1},
    "furnace": {"材料": {"cobblestone": 8}, "产出": 1},
    "chest": {"材料": {"_planks": 8}, "产出": 1},
    "torch": {"材料": {"coal": 1, "stick": 1}, "产出": 4},
    "ladder": {"材料": {"stick": 7}, "产出": 3},
    "fence": {"材料": {"_planks": 4, "stick": 2}, "产出": 3},
    "boat": {"材料": {"_planks": 5}, "产出": 1},
    "bowl": {"材料": {"_planks": 3}, "产出": 4},
    "bucket": {"材料": {"iron_ingot": 3}, "产出": 1},
    "compass": {"材料": {"iron_ingot": 4, "redstone": 1}, "产出": 1},
    "fishing_rod": {"材料": {"stick": 3, "string": 2}, "产出": 1},
    "bed": {"材料": {"_planks": 3, "white_wool": 3}, "产出": 1},
    "shield": {"材料": {"_planks": 6, "iron_ingot": 1}, "产出": 1},
    "iron_helmet": {"材料": {"iron_ingot": 5}, "产出": 1},
    "iron_chestplate": {"材料": {"iron_ingot": 8}, "产出": 1},
    "iron_leggings": {"材料": {"iron_ingot": 7}, "产出": 1},
    "iron_boots": {"材料": {"iron_ingot": 4}, "产出": 1},
    "diamond_helmet": {"材料": {"diamond": 5}, "产出": 1},
    "diamond_chestplate": {"材料": {"diamond": 8}, "产出": 1},
    "diamond_leggings": {"材料": {"diamond": 7}, "产出": 1},
    "diamond_boots": {"材料": {"diamond": 4}, "产出": 1},
}

# 无法合成的基础材料（需要挖掘/采集/冶炼获取）
RAW_MATERIALS = {
    # 原木
    "oak_log", "birch_log", "spruce_log", "jungle_log", "acacia_log", 
    "dark_oak_log", "mangrove_log", "cherry_log",
    # 矿石产物
    "cobblestone", "stone", "iron_ingot", "gold_ingot", "diamond", 
    "emerald", "coal", "redstone", "lapis_lazuli", "copper_ingot",
    # 其他原材料
    "string", "white_wool", "leather", "feather", "bone", "slime_ball",
    "ender_pearl", "blaze_rod", "ghast_tear", "nether_star",
    "raw_iron", "raw_gold", "raw_copper",
}

# 木板类型列表（用于通配符匹配）
PLANK_TYPES = [
    "oak_planks", "birch_planks", "spruce_planks", "jungle_planks",
    "acacia_planks", "dark_oak_planks", "mangrove_planks", "cherry_planks"
]

# 原木到木板的映射
LOG_TO_PLANKS = {
    "oak_log": "oak_planks",
    "birch_log": "birch_planks",
    "spruce_log": "spruce_planks",
    "jungle_log": "jungle_planks",
    "acacia_log": "acacia_planks",
    "dark_oak_log": "dark_oak_planks",
    "mangrove_log": "mangrove_planks",
    "cherry_log": "cherry_planks",
}


def get_inventory_dict(inventory_result):
    """将背包结果转换为字典 {物品名: 数量}"""
    items_dict = {}
    for item in inventory_result.get("inventory", []):
        items_dict[item["name"]] = items_dict.get(item["name"], 0) + item["count"]
    return items_dict


def find_available_planks(items_dict):
    """查找背包中可用的木板类型"""
    for plank_type in PLANK_TYPES:
        if items_dict.get(plank_type, 0) > 0:
            return plank_type
    return None


def find_available_logs(items_dict):
    """查找背包中可用的原木类型"""
    for log_type in LOG_TO_PLANKS.keys():
        if items_dict.get(log_type, 0) > 0:
            return log_type
    return None


def resolve_material(material_name, items_dict):
    """
    解析材料名称，处理通配符
    _planks -> 返回背包中实际有的木板类型，或优先可合成的木板类型
    """
    if material_name == "_planks":
        # 先检查是否有现成的木板
        available = find_available_planks(items_dict)
        if available:
            return available
        # 没有木板，检查是否有原木可以做木板
        log = find_available_logs(items_dict)
        if log:
            return LOG_TO_PLANKS[log]
        # 默认返回橡木木板
        return "oak_planks"
    return material_name


def get_recipe_info(item_name):
    """获取物品的配方信息，返回 (recipe_dict, needs_table)"""
    if item_name in SIMPLE_RECIPES:
        return SIMPLE_RECIPES[item_name], False
    elif item_name in TABLE_RECIPES:
        return TABLE_RECIPES[item_name], True
    return None, None


def can_craft(material_name):
    """检查材料是否可以合成"""
    if material_name in RAW_MATERIALS:
        return False
    if material_name in SIMPLE_RECIPES or material_name in TABLE_RECIPES:
        return True
    # 检查是否是木板类型
    if material_name in PLANK_TYPES:
        return True
    return False


def calculate_all_requirements(item_name, count=1, items_dict=None, _visited=None):
    """
    递归计算合成物品所需的所有基础材料
    
    Args:
        item_name: 物品名称
        count: 需要的数量
        items_dict: 当前背包物品字典
        _visited: 已访问的物品集合（防止循环）
    
    Returns:
        {
            "craftable": bool,  # 是否可以合成
            "raw_materials": {material: count},  # 需要的基础材料
            "intermediate": {material: count},  # 需要合成的中间产物
            "have": {material: count},  # 已经拥有的
            "missing": {material: count},  # 缺少的基础材料
        }
    """
    if items_dict is None:
        items_dict = {}
    if _visited is None:
        _visited = set()
    
    # 防止循环依赖
    if item_name in _visited:
        return {
            "craftable": False,
            "error": f"循环依赖: {item_name}",
            "raw_materials": {},
            "intermediate": {},
            "have": {},
            "missing": {}
        }
    _visited = _visited | {item_name}
    
    result = {
        "craftable": True,
        "raw_materials": {},
        "intermediate": {},
        "have": {},
        "missing": {}
    }
    
    # 检查背包已有的数量
    have = items_dict.get(item_name, 0)
    if have >= count:
        result["have"][item_name] = count
        return result
    
    # 需要额外制作的数量
    need_to_make = count - have
    if have > 0:
        result["have"][item_name] = have
    
    # 获取配方
    recipe_info, needs_table = get_recipe_info(item_name)
    
    if recipe_info is None:
        # 无配方，检查是否是基础材料
        if item_name in RAW_MATERIALS or not can_craft(item_name):
            result["raw_materials"][item_name] = need_to_make
            if need_to_make > 0:
                result["missing"][item_name] = need_to_make
                result["craftable"] = False
            return result
        else:
            # 未知配方但可能可以合成
            result["intermediate"][item_name] = need_to_make
            return result
    
    # 有配方，计算需要的材料
    output_per_craft = recipe_info["产出"]
    craft_times = (need_to_make + output_per_craft - 1) // output_per_craft
    
    result["intermediate"][item_name] = need_to_make
    
    for material, needed_per_craft in recipe_info["材料"].items():
        resolved_name = resolve_material(material, items_dict)
        needed_total = needed_per_craft * craft_times
        
        # 递归计算这个材料的需求
        sub_result = calculate_all_requirements(resolved_name, needed_total, items_dict, _visited)
        
        # 合并结果
        for key in ["raw_materials", "intermediate", "have", "missing"]:
            for mat, cnt in sub_result.get(key, {}).items():
                result[key][mat] = result[key].get(mat, 0) + cnt
        
        if not sub_result.get("craftable", True):
            result["craftable"] = False
    
    return result


async def find_valid_placement_position(bot):
    """
    智能寻找一个合法的方块放置位置
    
    检查条件：
    1. 目标位置是空气
    2. 目标位置下方有实体方块支撑
    3. 距离在可放置范围内（4格以内）
    
    Returns:
        (x, y, z) 或 None
    """
    pos = await bot.getPosition()
    bot_x, bot_y, bot_z = int(pos["x"]), int(pos["y"]), int(pos["z"])
    
    # 候选位置偏移量（优先级从高到低）
    # 先尝试同一高度的周围位置，再尝试上下
    offsets = [
        # 同一高度的4个方向
        (1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1),
        # 对角线
        (1, 0, 1), (1, 0, -1), (-1, 0, 1), (-1, 0, -1),
        # 上方一格的4个方向
        (1, 1, 0), (-1, 1, 0), (0, 1, 1), (0, 1, -1),
        # 下方一格的4个方向
        (1, -1, 0), (-1, -1, 0), (0, -1, 1), (0, -1, -1),
        # 距离2格的位置
        (2, 0, 0), (-2, 0, 0), (0, 0, 2), (0, 0, -2),
    ]
    
    for dx, dy, dz in offsets:
        target_x = bot_x + dx
        target_y = bot_y + dy
        target_z = bot_z + dz
        
        # 检查目标位置
        target_block = await bot.getBlockAt(target_x, target_y, target_z)
        if not target_block.get("success"):
            continue
        
        # 目标位置必须是空气
        if target_block.get("block", {}).get("name") != "air":
            continue
        
        # 检查下方是否有支撑
        below_block = await bot.getBlockAt(target_x, target_y - 1, target_z)
        if not below_block.get("success"):
            continue
        
        below_name = below_block.get("block", {}).get("name", "air")
        # 下方必须是实体方块（不是空气、水、岩浆等）
        invalid_supports = {"air", "water", "lava", "cave_air", "void_air"}
        if below_name in invalid_supports:
            continue
        
        # 找到合法位置
        bot.log(f"找到合法放置位置: ({target_x}, {target_y}, {target_z})")
        return (target_x, target_y, target_z)
    
    return None


async def place_block_safely(bot, block_name):
    """
    安全地放置方块，自动寻找合法位置
    
    Returns:
        {"success": bool, "message": str, "position": dict or None}
    """
    # 寻找合法位置
    placement_pos = await find_valid_placement_position(bot)
    
    if placement_pos is None:
        return {
            "success": False,
            "message": "找不到合适的位置放置方块",
            "position": None
        }
    
    x, y, z = placement_pos
    result = await bot.placeBlock(block_name, x, y, z)
    
    if result.get("success"):
        return {
            "success": True,
            "message": f"成功放置 {block_name} 在 ({x}, {y}, {z})",
            "position": {"x": x, "y": y, "z": z}
        }
    else:
        return {
            "success": False,
            "message": result.get("message", "放置失败"),
            "position": None
        }


async def ensure_crafting_table(bot, items_dict):
    """确保有可用的工作台，返回是否成功"""
    # 先找附近的工作台
    table = await bot.findCraftingTable(32)
    
    if table.get("found"):
        table_pos = table["position"]
        bot.log(f"找到工作台在 ({table_pos['x']}, {table_pos['y']}, {table_pos['z']})")
        
        # 检查距离，如果太远就走过去
        pos = await bot.getPosition()
        dx = pos["x"] - table_pos["x"]
        dy = pos["y"] - table_pos["y"]
        dz = pos["z"] - table_pos["z"]
        distance = (dx*dx + dy*dy + dz*dz) ** 0.5
        
        if distance > 4:
            bot.log("走近工作台...")
            await bot.goTo(table_pos["x"], table_pos["y"], table_pos["z"])
        return True
    
    # 没有找到工作台，检查背包
    if items_dict.get("crafting_table", 0) > 0:
        bot.log("背包有工作台，智能寻找放置位置...")
        
        place_result = await place_block_safely(bot, "crafting_table")
        if place_result.get("success"):
            await bot.chat("放好工作台啦喵~")
            return True
        else:
            bot.log(f"放置工作台失败: {place_result.get('message')}")
            # 尝试备用方案：简单地在脚下放置
            bot.log("尝试备用放置方案...")
            pos = await bot.getPosition()
            backup_result = await bot.placeBlock("crafting_table",
                int(pos["x"]), int(pos["y"]) - 1, int(pos["z"]) + 1)
            if backup_result.get("success"):
                await bot.chat("放好工作台啦喵~")
                return True
            return False
    
    # 需要合成工作台
    bot.log("需要先合成工作台")
    await bot.chat("需要先做个工作台喵~")
    
    table_result = await 合成(bot, "crafting_table", 1)
    if not table_result.get("success"):
        return False
    
    # 放置工作台
    # 重新获取背包
    inventory = await bot.viewInventory()
    items_dict = get_inventory_dict(inventory)
    
    if items_dict.get("crafting_table", 0) > 0:
        place_result = await place_block_safely(bot, "crafting_table")
        if place_result.get("success"):
            await bot.chat("放好工作台啦喵~")
            return True
    
    return False


async def 合成(bot, itemName, count=1, _depth=0, analyze_only=False):
    """
    合成指定物品，支持递归合成缺失的材料
    
    流程：
    1. 查看物品配方
    2. 检查材料是否足够
    3. 如果材料不足，递归合成缺失的材料
    4. 如果需要工作台，确保有可用的工作台
    5. 执行合成
    
    Args:
        bot: BotAPI实例
        itemName: 要合成的物品名称
        count: 合成数量，默认1
        _depth: 递归深度（内部使用，防止无限递归）
        analyze_only: 仅分析需要的材料，不实际合成
    
    Returns:
        合成结果，包含 requirements 字段说明需要的材料
    """
    MAX_DEPTH = 10  # 最大递归深度
    
    if _depth > MAX_DEPTH:
        return {
            "success": False,
            "message": f"递归深度超过限制({MAX_DEPTH})，可能存在循环依赖"
        }
    
    indent = "  " * _depth  # 用于日志缩进
    bot.log(f"{indent}开始合成: {itemName} x {count} (深度: {_depth})")
    
    # 获取背包
    inventory = await bot.viewInventory()
    items_dict = get_inventory_dict(inventory)
    
    # 计算完整的材料需求
    requirements = calculate_all_requirements(itemName, count, items_dict)
    bot.log(f"{indent}材料需求分析: {requirements}")
    
    # 如果只是分析模式，直接返回需求
    if analyze_only:
        return {
            "success": True,
            "analyze_only": True,
            "item": itemName,
            "count": count,
            "requirements": requirements,
            "message": _format_requirements_message(requirements)
        }
    
    # 获取配方信息
    recipe_info, needs_table = get_recipe_info(itemName)
    
    if recipe_info is None:
        # 未知配方，尝试直接调用craft
        bot.log(f"{indent}未知配方，尝试直接合成 {itemName}")
        result = await bot.craft(itemName, count)
        result["requirements"] = requirements
        return result
    
    bot.log(f"{indent}当前背包: {items_dict}")
    
    # 计算需要合成几次（考虑产出数量）
    output_per_craft = recipe_info["产出"]
    craft_times = (count + output_per_craft - 1) // output_per_craft  # 向上取整
    
    # 解析材料并检查
    resolved_materials = {}  # 解析后的材料需求
    for material, needed_per_craft in recipe_info["材料"].items():
        resolved_name = resolve_material(material, items_dict)
        needed_total = needed_per_craft * craft_times
        resolved_materials[resolved_name] = resolved_materials.get(resolved_name, 0) + needed_total
    
    bot.log(f"{indent}需要的材料: {resolved_materials}")
    
    # 检查并递归合成缺失的材料
    for material, needed_total in resolved_materials.items():
        have = items_dict.get(material, 0)
        
        if have >= needed_total:
            bot.log(f"{indent}  {material}: 足够 ({have}/{needed_total})")
            continue
        
        shortage = needed_total - have
        bot.log(f"{indent}  {material}: 不足 ({have}/{needed_total})，缺少 {shortage}")
        
        # 检查是否可以合成
        if not can_craft(material):
                # 无法合成的基础材料
                bot.log(f"{indent}  {material} 是基础材料，无法合成")
                await bot.chat(f"缺少 {material} x {shortage}，这个需要去采集/挖掘喵~")
                return {
                    "success": False,
                    "message": f"缺少基础材料 {material} x {shortage}，需要采集或挖掘获取",
                    "requirements": requirements,
                    "missing_raw_materials": requirements.get("missing", {}),
                    "missing": [{
                        "material": material,
                        "needed": needed_total,
                        "have": have,
                        "craftable": False
                    }]
                }
        
        # 可以合成，递归调用
        bot.log(f"{indent}  尝试递归合成 {material} x {shortage}")
        await bot.chat(f"先做 {material} x {shortage} 喵~")
        
        sub_result = await 合成(bot, material, shortage, _depth + 1)
        
        if not sub_result.get("success"):
            bot.log(f"{indent}  递归合成 {material} 失败")
            return {
                "success": False,
                "message": f"无法合成中间材料 {material}: {sub_result.get('message')}",
                "requirements": requirements,
                "missing_raw_materials": sub_result.get("missing_raw_materials", requirements.get("missing", {})),
                "sub_error": sub_result
            }
        
        # 递归合成成功，更新背包信息
        inventory = await bot.viewInventory()
        items_dict = get_inventory_dict(inventory)
        bot.log(f"{indent}  递归合成 {material} 成功，更新背包: {items_dict}")
    
    # 所有材料已准备好，如果需要工作台则确保有
    if needs_table:
        if not await ensure_crafting_table(bot, items_dict):
            return {
                "success": False,
                "message": "无法获取工作台",
                "requirements": requirements
            }
    
    # 执行合成
    bot.log(f"{indent}开始合成 {itemName} x {count}")
    if _depth == 0:
        await bot.chat(f"合成 {itemName} 中...")
    
    result = await bot.craft(itemName, count)
    
    if result.get("success"):
        if _depth == 0:
            await bot.chat(f"合成成功喵~ {itemName} x {count}")
        return {
            "success": True,
            "message": f"成功合成 {itemName} x {count}",
            "crafted": count,
            "requirements": requirements
        }
    else:
        if _depth == 0:
            await bot.chat(f"合成失败了喵... {result.get('message')}")
        return {
            "success": False,
            "message": result.get("message", "合成失败"),
            "requirements": requirements
        }


def _format_requirements_message(requirements):
    """格式化材料需求为可读消息"""
    parts = []
    
    if requirements.get("missing"):
        missing_str = ", ".join([f"{mat} x{cnt}" for mat, cnt in requirements["missing"].items()])
        parts.append(f"缺少基础材料: {missing_str}")
    
    if requirements.get("raw_materials"):
        raw_str = ", ".join([f"{mat} x{cnt}" for mat, cnt in requirements["raw_materials"].items()])
        parts.append(f"需要的基础材料: {raw_str}")
    
    if requirements.get("intermediate"):
        inter_str = ", ".join([f"{mat} x{cnt}" for mat, cnt in requirements["intermediate"].items()])
        parts.append(f"需要合成的中间产物: {inter_str}")
    
    if requirements.get("have"):
        have_str = ", ".join([f"{mat} x{cnt}" for mat, cnt in requirements["have"].items()])
        parts.append(f"已拥有: {have_str}")
    
    if requirements.get("craftable"):
        parts.append("可以完成合成")
    else:
        parts.append("无法完成合成（缺少基础材料）")
    
    return "; ".join(parts)