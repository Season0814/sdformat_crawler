from html.parser import HTMLParser
import json

class SDFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.items = []
        self.current_item = None
        self.in_h5 = False
        self.in_small = False
        self.in_details = False # col-xs-4
        self.in_description = False # col-xs-8
        self.details_buffer = ""
        self.desc_buffer = ""
        self.name_buffer = ""
        self.type_buffer = ""
        self.tree_stack = [] # 用于构建树结构
        self.capture_mode = False # 只有进入 tree well 后才开始捕获

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()

        if tag == "div" and "tree" in class_list and "well" in class_list:
            self.capture_mode = True

        if not self.capture_mode:
            return

        if tag == "ul":
            self.depth += 1
            # 将当前 items 列表推入栈，开始新的子列表
            # 但这里我们采用线性列表 + depth 或者是递归构建？
            # 让我们尝试维护一个 stack of lists
            # 初始 stack: [root_list]
            # 遇到 ul: new_list = [], current_list.append(new_list) (但这不对，因为 ul 是 li 的子元素)
            # 正确逻辑：
            # items 是一个扁平列表，包含 depth 信息？
            # 或者我们直接构建树。
            pass

        elif tag == "li":
            # 新的项开始
            self.current_item = {"children": [], "depth": self.depth}
            # 找到父节点并添加到其 children 中
            # 这比较复杂，因为 HTMLParser 是流式的。
            # 我们先收集所有项，并在结束后根据 depth 重建树，或者直接在这里处理。
            # 但是我们不知道这个 li 是属于哪个父 li 的，除非我们跟踪 ul。
            # 简单方法：
            # 使用 stack 来保存当前的父节点。
            # 当 depth 增加时，最近的 item 成为父节点。
            pass

        elif tag == "h5":
            self.in_h5 = True
            self.name_buffer = ""

        elif tag == "small":
            self.in_small = True
            self.type_buffer = ""

        elif tag == "div":
            if "col-xs-4" in class_list:
                self.in_details = True
                self.details_buffer = ""
            elif "col-xs-8" in class_list:
                self.in_description = True
                self.desc_buffer = ""

    def handle_endtag(self, tag):
        if not self.capture_mode:
            return

        if tag == "ul":
            self.depth -= 1
            if self.depth == 0:
                # 根 ul 结束
                self.capture_mode = False

        elif tag == "li":
            if self.current_item:
                # 处理完一个 li，将其加入到列表中
                # 这里为了简单，我们只收集扁平列表，包含 depth
                # 后期再重组
                # 但是我们需要知道它是否有效（有 name）
                if "name" in self.current_item:
                     self.items.append(self.current_item)
                self.current_item = None

        elif tag == "h5":
            self.in_h5 = False
            if self.current_item:
                self.current_item["name"] = self.name_buffer.strip()

        elif tag == "small":
            self.in_small = False
            if self.current_item:
                self.current_item["type"] = self.type_buffer.strip().replace("Attribute", "").replace("Element", "").strip()
                # Remove type from name buffer if it was appended
                # h5 content: "name <small>Attribute</small>"
                # handle_data 会按顺序调用
                pass

        elif tag == "div":
            if self.in_details:
                self.in_details = False
                if self.current_item:
                    # Parse details: Required: 1\nType: string\n...
                    parts = self.details_buffer.split("\n") # 或者是其他分隔符
                    # 在 handle_data 中我们会收集文本
                    pass
            elif self.in_description:
                self.in_description = False
                if self.current_item:
                    desc = self.desc_buffer.strip()
                    if desc.startswith("Description:"):
                        desc = desc[len("Description:"):].strip()
                    self.current_item["description"] = desc

    def handle_data(self, data):
        if not self.capture_mode:
            return

        if self.in_small:
            self.type_buffer += data
        elif self.in_h5:
            # h5 包含 name 和 small。small 的内容也会触发 handle_data（在 in_small 状态下）
            # 所以如果在 in_small，不要加到 name_buffer
            if not self.in_small:
                self.name_buffer += data

        if self.in_details:
            self.details_buffer += data + " " # 加空格防止粘连

        if self.in_description:
            self.desc_buffer += data

def parse_html(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    parser = SDFParser()
    parser.feed(content)
    
    # Post-process items to parse details
    for item in parser.items:
        # Clean name
        if "name" in item:
             item["name"] = item["name"].replace("<", "").replace(">", "").strip()
        
        # details 还没有处理
        # 我们需要在 handle_endtag 中处理，或者在这里处理
        # 但是 details_buffer 没保存到 item 中。
        pass
    
    # 让我们改进 Parser，直接在 endtag 处理 details

    return parser.items

# 重新设计 Parser 以更好地处理结构
class BetterSDFParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = [] # stack of (list_of_children)
        self.root_list = []
        self.stack.append(self.root_list)
        
        self.current_item = None
        
        self.in_h5 = False
        self.in_small = False
        self.in_details = False
        self.in_description = False
        
        self.buffers = {
            "name": "",
            "type": "",
            "details": "",
            "description": ""
        }
        
        self.capture_mode = False
        self.div_level = 0 # 跟踪 div 嵌套以确定何时退出 tree well

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_list = attrs_dict.get("class", "").split()

        if tag == "div":
            if "tree" in class_list and "well" in class_list:
                self.capture_mode = True
                self.div_level = 0
            elif self.capture_mode:
                self.div_level += 1
            
            if "col-xs-4" in class_list:
                self.in_details = True
                self.buffers["details"] = ""
            elif "col-xs-8" in class_list:
                self.in_description = True
                self.buffers["description"] = ""

        if not self.capture_mode:
            return

        if tag == "ul":
            # 新的层级
            # 如果当前有 item，这个 ul 是该 item 的 children
            if self.current_item is not None:
                new_list = []
                self.current_item["children"] = new_list
                self.stack.append(new_list)
            else:
                # 可能是根 ul 或者其他情况
                # 如果是根 ul，我们已经有 root_list 在栈底
                # 但是如果是嵌套的 ul 而没有 current_item (这不应该发生，除非 HTML 结构奇怪)
                pass

        elif tag == "li":
            self.current_item = {}
            # 添加到当前层级的列表
            self.stack[-1].append(self.current_item)

        elif tag == "h5":
            self.in_h5 = True
            self.buffers["name"] = ""

        elif tag == "small":
            self.in_small = True
            self.buffers["type"] = ""

    def handle_endtag(self, tag):
        if tag == "div":
            if self.capture_mode:
                if self.in_details:
                    self.in_details = False
                    if self.current_item is not None:
                        # 解析 details
                        text = self.buffers["details"]
                        parts = text.split("  ") # 尝试空格分割，或者用更智能的方法
                        # 实际上 details 包含 <b>Required: </b>1<br>...
                        # handle_data 会拿到 "Required: ", "1", "Type: ", ...
                        # 我们可以在 buffer 中累积所有文本，然后用正则提取
                        self.current_item["details_raw"] = text
                elif self.in_description:
                    self.in_description = False
                    if self.current_item is not None:
                         desc = self.buffers["description"].strip()
                         if desc.startswith("Description:"):
                             desc = desc[len("Description:"):].strip()
                         self.current_item["description"] = desc
                
                self.div_level -= 1
                if self.div_level < 0: # 出了 tree well
                    self.capture_mode = False

        if not self.capture_mode:
            return

        if tag == "ul":
            if len(self.stack) > 1:
                self.stack.pop()
            # current_item 应该置空吗？
            # 这里的 current_item 指的是拥有这个 ul 的那个 item
            # 当 ul 结束，意味着这个 item 的 children 结束了
            # 但是 current_item 变量指向的是最近创建的 item
            pass

        elif tag == "li":
            # item 完成
            # self.current_item = None # 不，我们需要保持它以便处理随后的 ul
            pass

        elif tag == "h5":
            self.in_h5 = False
            if self.current_item is not None:
                name = self.buffers["name"].strip()
                self.current_item["name"] = name.replace("<", "").replace(">", "").strip()

        elif tag == "small":
            self.in_small = False
            if self.current_item is not None:
                type_str = self.buffers["type"].strip().replace("Attribute", "").replace("Element", "").strip()
                if "Attribute" in self.buffers["type"]:
                     self.current_item["node_type"] = "Attribute"
                else:
                     self.current_item["node_type"] = "Element"

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

def main():
    parser = BetterSDFParser()
    with open("page_content.html", "r", encoding="utf-8") as f:
        content = f.read()
    parser.feed(content)
    
    with open("structure.json", "w", encoding="utf-8") as f:
        json.dump(parser.root_list, f, indent=2, ensure_ascii=False)
    
    print("Structure extracted.")

if __name__ == "__main__":
    main()
