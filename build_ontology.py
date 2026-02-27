import json
import re

# 本体前缀
PREFIXES = """@prefix : <http://sdformat.org/spec/model#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix xml: <http://www.w3.org/XML/1998/namespace> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@base <http://sdformat.org/spec/model> .
"""

def clean_details(raw):
    # Example: "\n Required:  1 Type:  string Default:  __default__ \n "
    info = {}
    
    # 提取 Required
    req_match = re.search(r"Required:\s*(\S+)", raw)
    if req_match:
        info["required"] = req_match.group(1)
        
    # 提取 Type
    type_match = re.search(r"Type:\s*(.*?)(?:Default:|$)", raw)
    if type_match:
        info["type"] = type_match.group(1).strip()
        
    # 提取 Default
    def_match = re.search(r"Default:\s*(.*)", raw)
    if def_match:
        info["default"] = def_match.group(1).strip()
        
    return info

def map_xsd_type(sdf_type):
    sdf_type = sdf_type.lower()
    if sdf_type == "bool" or sdf_type == "boolean":
        return "xsd:boolean"
    elif sdf_type == "string":
        return "xsd:string"
    elif sdf_type in ["int", "integer", "unsigned int"]:
        return "xsd:integer"
    elif sdf_type in ["double", "float"]:
        return "xsd:double"
    elif sdf_type == "vector3":
        return "xsd:string" # 或者定义特定类型
    elif sdf_type == "pose":
        return "xsd:string" # "x y z r p y"
    elif sdf_type == "color":
        return "xsd:string"
    elif sdf_type == "time":
        return "xsd:string"
    else:
        return "xsd:string" # Default

def build_ontology(structure_file, output_file):
    with open(structure_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    turtle_lines = [PREFIXES]
    
    # 我们需要遍历树，为每个 Complex Element 创建 Class
    # 为每个 Simple Element 和 Attribute 创建 Property
    
    classes_defined = set()
    properties_defined = set()
    
    def process_node(node, parent_class_name=None):
        node_name = node.get("name")
        node_type = node.get("node_type")
        description = node.get("description", "").replace('"', '\\"')
        details = clean_details(node.get("details_raw", ""))
        sdf_type = details.get("type", "")
        children = node.get("children", [])
        
        # 确定这是否是一个 ObjectProperty (指向 Class) 还是 DatatypeProperty
        is_complex = len(children) > 0
        
        # 属性名称 (predicate)
        # 如果 parent 是 Model, node 是 static -> :model_static ? 或者直接 :static ?
        # 为了避免冲突，可以使用 :parent_child 命名，或者保持简单如果语义唯一。
        # SDFormat 中很多元素名是重复的（如 name, pose），所以最好带上前缀或者使用域定义。
        # 这里为了简单，我们使用 :has_{node_name} 作为属性名。
        
        prop_name = f"has_{node_name}"
        if node_type == "Attribute":
             prop_name = f"{node_name}_attr" # 区分 attribute 和 element
        
        # 如果是根节点 (Model)
        if parent_class_name is None:
            class_name = node_name.capitalize()
            if class_name not in classes_defined:
                turtle_lines.append(f":{class_name} rdf:type owl:Class ;")
                turtle_lines.append(f"    rdfs:comment \"{description}\" .")
                classes_defined.add(class_name)
            
            # 处理子节点
            for child in children:
                process_node(child, class_name)
            return

        # 对于子节点
        if is_complex:
            # 创建新的 Class
            # Class 名称需要唯一
            # 使用 Parent_Child 命名
            # 首字母大写
            safe_node_name = node_name.capitalize()
            child_class_name = f"{parent_class_name}_{safe_node_name}"
            
            if child_class_name not in classes_defined:
                turtle_lines.append(f":{child_class_name} rdf:type owl:Class ;")
                # 转义描述中的引号
                safe_desc = description.replace('"', '\\"')
                turtle_lines.append(f"    rdfs:comment \"{safe_desc}\" .")
                classes_defined.add(child_class_name)
            
            # 定义 ObjectProperty 连接 Parent 和 Child
            # 使用唯一的属性名避免 Domain/Range 冲突
            unique_prop_name = f"{parent_class_name}_has_{safe_node_name}"
            
            if unique_prop_name not in properties_defined:
                turtle_lines.append(f":{unique_prop_name} rdf:type owl:ObjectProperty ;")
                turtle_lines.append(f"    rdfs:domain :{parent_class_name} ;")
                turtle_lines.append(f"    rdfs:range :{child_class_name} ;")
                turtle_lines.append(f"    rdfs:comment \"Property for {node_name} element\" .")
                properties_defined.add(unique_prop_name)
                
            # 递归处理子节点的子节点
            for child in children:
                process_node(child, child_class_name)
                
        else:
            # Simple Element or Attribute -> DatatypeProperty
            xsd_type = map_xsd_type(sdf_type) # 确保 map_xsd_type 函数在上面定义了
            
            # 属性名唯一性处理
            # 使用 Parent_propName
            unique_prop_name = f"{parent_class_name}_{node_name}"
            if node_type == "Attribute":
                unique_prop_name += "_attr"
            
            # 清理属性名（移除可能的非法字符）
            unique_prop_name = re.sub(r"[^a-zA-Z0-9_]", "_", unique_prop_name)
            
            safe_desc = description.replace('"', '\\"')
            
            turtle_lines.append(f":{unique_prop_name} rdf:type owl:DatatypeProperty ;")
            turtle_lines.append(f"    rdfs:domain :{parent_class_name} ;")
            turtle_lines.append(f"    rdfs:range {xsd_type} ;")
            turtle_lines.append(f"    rdfs:comment \"{safe_desc}\" .")

    # 开始处理根节点
    # 假设 data 是一个列表，通常只有一个根 model
    for root in data:
        process_node(root)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(turtle_lines))
    
    print(f"Ontology saved to {output_file}")

if __name__ == "__main__":
    build_ontology("structure.json", "sdformat_model.ttl")
