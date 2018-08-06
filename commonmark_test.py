import CommonMark


def get_node_source(src, ast_node):
    if ast_node.t == 'text':
        return ast_node.literal

    start_line = ast_node.sourcepos[0][0] - 1
    end_line = ast_node.sourcepos[1][0]

    first_line_start_offset = ast_node.sourcepos[0][1] - 1
    last_line_end_offset = ast_node.sourcepos[1][1]

    lines = src.splitlines()[start_line:end_line]
    lines[0] = lines[0][first_line_start_offset:]
    lines[-1] = lines[-1][:last_line_end_offset]

    return "\n".join(lines)

def is_tags(ast_node):
    return ast_node.t == 'paragraph' and ast_node.first_child.t == 'emph' and ast_node.first_child == ast_node.last_child


src = open('examples/schwarzbierbrot.md', 'r').read()
lines = src.splitlines()

parser = CommonMark.Parser()
ast = parser.parse(src)

print(CommonMark.dumpJSON(ast))

title = None
description = ""
tags = None

current = ast.first_child
if current.t == 'heading' and current.level == 1:
    title = get_node_source(src, current.first_child)
    current = current.nxt

while current.t != 'thematic_break' and not is_tags(current):
    description += get_node_source(src, current) + '\n'
    current = current.nxt

if is_tags(current):
    tags_text = get_node_source(src, current.first_child.first_child)
    tags = tags_text.split(',')
    current = current.nxt

if current.t == 'thematic_break':
    current = current.nxt

while current.t != 'thematic_break':
    if current.t == 'list':
        print(current)
    current = current.nxt