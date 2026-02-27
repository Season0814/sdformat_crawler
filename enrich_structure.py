import requests
from html.parser import HTMLParser
import json
import re
import shutil
import copy
import sys

# Increase recursion limit just in case, though we should fix the logic
sys.setrecursionlimit(2000)

# 复用 BetterSDFParser，但稍作修改以适应多页面抓取
class SDFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = [] 
        self.root_list = []
        self.stack.append(self.root_list)
        
        self.current_item = None
        self.in_h5 = False
        self.in_small = False
        self.in_details = False
        self.in_description = False
        self.buffers = {"name": "", "type": "", "details": "", "description": ""}
        self.capture_mode = False
        self.div_level = 0
        self.tree_well_depth = 0 # 记录 tree well 的 div 深度

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()

        if tag == "div":
            if "tree" in class_list and "well" in class_list:
                if not self.capture_mode:
                    self.capture_mode = True
                    self.tree_well_depth = self.div_level
            self.div_level += 1

        if not self.capture_mode:
            return

        if tag == "ul":
            # 进入子列表
            # 只有当 current_item 存在时，ul 才是它的 children
            # 但是 HTML 结构可能是 li -> ul
            if self.current_item:
                new_list = self.current_item["children"]
                self.stack.append(new_list)
            else:
                pass

        elif tag == "li":
            # 新的项
            self.current_item = {
                "node_type": "Element", # 默认为 Element，稍后修正
                "name": "",
                "details_raw": "",
                "description": "",
                "children": []
            }
            self.stack[-1].append(self.current_item)
            
            # 清空 buffers
            for k in self.buffers:
                self.buffers[k] = ""

        elif tag == "h5":
            self.in_h5 = True

        elif tag == "small":
            self.in_small = True

        elif tag == "div":
            if "col-xs-4" in class_list:
                self.in_details = True
            elif "col-xs-8" in class_list:
                self.in_description = True

    def handle_endtag(self, tag):
        if tag == "div":
            self.div_level -= 1
            if self.capture_mode and self.div_level == self.tree_well_depth:
                self.capture_mode = False
            
            if self.in_details:
                self.in_details = False
                if self.current_item:
                    self.current_item["details_raw"] = self.buffers["details"]
            
            if self.in_description:
                self.in_description = False
                if self.current_item:
                    desc = self.buffers["description"].strip()
                    if desc.startswith("Description:"):
                        desc = desc[len("Description:"):].strip()
                    self.current_item["description"] = desc

        elif tag == "ul":
            if self.capture_mode:
                if len(self.stack) > 1:
                    self.stack.pop()

        elif tag == "li":
            # 结束当前项，但在 tree view 中，li 包含 ul，所以 li 结束意味着其子树也结束
            # 我们不需要在这里做特别的操作，因为 item 已经在 list 中了
            # 只需要确定 current_item 不再指向它（防止后续误操作，虽然后续是新的 li）
            pass

        elif tag == "h5":
            self.in_h5 = False
            if self.current_item:
                raw_name = self.buffers["name"].strip()
                # 移除 < 和 >
                raw_name = raw_name.replace("<", "").replace(">", "")
                
                # 区分 Attribute (@name) 和 Element (name)
                if raw_name.startswith("@"):
                    self.current_item["node_type"] = "Attribute"
                    self.current_item["name"] = raw_name[1:]
                else:
                    self.current_item["node_type"] = "Element"
                    self.current_item["name"] = raw_name

        elif tag == "small":
            self.in_small = False

    def handle_data(self, data):
        if not self.capture_mode:
            return

        if self.in_small:
            self.buffers["type"] += data
        elif self.in_h5:
            self.buffers["name"] += data

        if self.in_details:
            self.buffers["details"] += data + " "

        if self.in_description:
            self.buffers["description"] += data


def extract_structure_from_url(url, element_name):
    print(f"Crawling {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.text
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return []

    parser = SDFParser()
    parser.feed(content)
    
    # 修正：有些页面可能直接列出属性，没有外层包裹，或者结构略有不同
    # 但 SDF 网站通常结构一致
    
    # 后处理：根节点通常是我们要的元素（例如 link），但 parser 可能会抓取到它的父容器或者直接是列表
    # parser.root_list 通常包含一个或多个顶层元素
    
    # 验证：根节点应该是 element_name
    result = []
    for item in parser.root_list:
        if item["name"] == element_name:
            result.append(item)
        else:
            # 有时页面会包含一些导航或其他 tree well，需要过滤
            # 但根据经验，主要 tree well 包含该元素
            if item["name"] == element_name:
                result.append(item)
    
    # 如果没找到，可能 parser.root_list 就是那个列表，里面包含属性
    # 实际上，parser 会把 <div class="tree well"><ul><li>...</li></ul></div> 解析出来
    # 根通常是 element_name 本身
    
    if not result and parser.root_list:
        # 尝试查找匹配的
        for item in parser.root_list:
             if item.get("name") == element_name:
                 return [item]
    
    return parser.root_list

def merge_structure(main_struct, sub_structs):
    # main_struct 是一个列表，通常包含一个根 'model'
    # sub_structs 是一个字典 { 'link': link_struct_list, 'joint': joint_struct_list }
    
    def recursive_merge(node, depth=0, path=""):
        current_path = f"{path}/{node.get('name', 'unknown')}"
        
        if depth > 100:
             print(f"Max depth reached at: {current_path}")
             return

        node_type = node.get("node_type", "Element") # 默认为 Element
        
        if node_type == "Element":
            name = node.get("name")
            
            # Determine parent name for context-aware expansion
            parent_name = path.split("/")[-1] if "/" in path else path

            # Logic to decide whether to expand using sub_structs
            should_expand = False
            
            if name in sub_structs:
                if name == "joint":
                    # Only expand joint if it is a direct child of model or world
                    if parent_name in ["model", "world", "root"]: # root for top level testing
                        should_expand = True
                elif name == "link":
                    # Only expand link if it is a direct child of model
                    if parent_name in ["model", "root"]:
                        should_expand = True
                else:
                    # For other elements (sensor, light, etc.), expand freely or add restrictions if needed
                    # Sensor can be in link, joint, model, world
                    should_expand = True
            
            if should_expand:
                sub_roots = sub_structs[name]
                if sub_roots:
                    sub_root = sub_roots[0] # 取第一个匹配的根
                    
                    # 检查当前 node 的 children
                    # 重要：为了避免共享引用导致的递归或状态污染，使用 deepcopy
                    if not node.get("children"):
                        node["children"] = copy.deepcopy(sub_root.get("children", []))
                        # 也可以更新描述和 details
                        if not node.get("description"):
                            node["description"] = sub_root.get("description", "")
            
        for child in node.get("children", []):
            recursive_merge(child, depth + 1, current_path)

    for root in main_struct:
        recursive_merge(root, 0, "root")
    
    return main_struct

def main():
    # 1. 读取现有的 structure.json
    try:
        with open("structure.json", "r", encoding="utf-8") as f:
            main_struct = json.load(f)
    except FileNotFoundError:
        print("structure.json not found. Run extract_structure.py first.")
        return

    # 2. 爬取 link 和 joint
    # 还有其他未展开的吗？actor? light? sensor?
    # 用户提到了 link 和 joint。我们也检查一下 sensor, light, actor, collision, visual (在 link 下)
    # 但是 visual/collision 通常在 link 页面里已经展开了。
    # 让我们先关注 link 和 joint。
    
    targets = {
        "link": "https://sdformat.org/spec/1.12/link",
        "joint": "https://sdformat.org/spec/1.12/joint",
        "sensor": "https://sdformat.org/spec/1.12/sensor",
        "light": "https://sdformat.org/spec/1.12/light",
        "actor": "https://sdformat.org/spec/1.12/actor",
        "collision": "https://sdformat.org/spec/1.12/collision",
        "visual": "https://sdformat.org/spec/1.12/visual",
        "inertial": "https://sdformat.org/spec/1.12/inertial"
    }
    
    sub_structs = {}
    
    for name, url in targets.items():
        print(f"Extracting {name}...")
        struct = extract_structure_from_url(url, name)
        if struct:
            sub_structs[name] = struct
            # 同时保存一份单独的文件以备查
            with open(f"structure_{name}.json", "w", encoding="utf-8") as f:
                json.dump(struct, f, indent=2, ensure_ascii=False)
        else:
            print(f"Warning: No structure found for {name}")

    # 3. 合并
    print("Merging structures...")
    merged_struct = merge_structure(main_struct, sub_structs)
    
    # 4. 保存
    with open("structure_merged.json", "w", encoding="utf-8") as f:
        json.dump(merged_struct, f, indent=2, ensure_ascii=False)
    
    # 覆盖原文件？或者保留 merged
    # 为了后续脚本兼容，最好覆盖 structure.json，但先备份
    import shutil
    shutil.copy("structure.json", "structure_backup.json")
    shutil.copy("structure_merged.json", "structure.json")
    
    print("Done. structure.json updated.")

if __name__ == "__main__":
    main()
