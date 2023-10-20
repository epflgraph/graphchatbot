from app.interfaces.es import search_nodes

from app.nodes import (
    get_all_nodes_and_filter,
    get_neighborhood,
    filter,
    sort,
    limit,
    take_intersection,
    take_union,
    take_difference,
)

################################################################
# ERROR CODES                                                  #
################################################################

ERR_DUPLICATE_LHS = 'DUPLICATE_LHS'
ERR_NESTED_OPERATOR = 'NESTED_OPERATOR'
ERR_INVALID_OPERATOR = 'INVALID_OPERATOR'
ERR_INVALID_PARAM_COUNT = 'INVALID_PARAM_COUNT'
ERR_INVALID_NODE_TYPE = 'INVALID_NODE_TYPE'
ERR_INVALID_FIELD = 'INVALID_FIELD'
ERR_INVALID_VALUE = 'INVALID_VALUE'
ERR_INVALID_ORDER = 'INVALID_ORDER'
ERR_INVALID_INT = 'INVALID_INT'
ERR_UNDEFINED_NODESET = 'UNDEFINED_NODESET'
ERR_SET_OPERATION_DIFFERENT_TYPES = 'SET_OPERATION_DIFFERENT_TYPES'
ERR_SEVERAL_RETURNS = 'SEVERAL_RETURNS'
ERR_INSTRUCTION_AFTER_RETURN = 'INSTRUCTION_AFTER_RETURN'
ERR_UNUSED_LHS = 'UNUSED_LHS'

################################################################
# MAIN                                                         #
################################################################


def parse_instructions(instructions_str):
    instructions = instructions_str.split('\n')

    parsed_instructions = []
    for instruction in instructions:
        if 'Return' in instruction:
            lhs = None
            rhs = instruction
        else:
            if '=' not in instruction:
                continue

            # Split LHS and RHS
            pieces = instruction.split('=')
            pieces = [piece.strip() for piece in pieces]
            [lhs, rhs] = pieces

        if '(' not in rhs or ')' not in rhs:
            continue

        # Get operator and arguments from RHS
        begin = rhs.find('(')
        end = rhs.rfind(')')
        operator = rhs[: begin]
        params = rhs[begin + 1: end].split(',')
        params = [param.strip() for param in params]

        parsed_instructions.append({'source': instruction, 'lhs': lhs, 'operator': operator, 'params': params})

    # Raise exception if no instructions were extracted
    if len(parsed_instructions) == 0:
        if len(instructions_str) > 60:
            instructions_str = instructions_str[:60] + "..."
        raise ValueError(f"""No instructions can be extracted from "{instructions_str}" """)

    return parsed_instructions


def check_instructions(instructions):
    supported_node_types = ['Concept', 'Person', 'Course', 'Lecture', 'Unit', 'Publication']

    supported_operators = {
        'Search': ['node_type', 'value'],
        'All': ['node_type', 'field', 'value'],
        'Neighborhood': ['nodeset', 'node_type'],
        'Filter': ['nodeset', 'field', 'value'],
        'FilterRange': ['nodeset', 'field', 'value', 'value'],
        'Sort': ['nodeset', 'field', 'order'],
        'Limit': ['nodeset', 'int'],
        'Intersection': ['nodeset', 'nodeset'],
        'Union': ['nodeset', 'nodeset'],
        'Difference': ['nodeset', 'nodeset'],
        'Return': ['nodeset'],
    }

    retrieval_operators = ['Search', 'All']
    navigation_operators = ['Neighborhood']
    manipulation_operators = ['Filter', 'FilterRange', 'Sort', 'Limit']
    set_operators = ['Intersection', 'Union', 'Difference']
    return_operators = ['Return']

    # Check instructions individually
    seen_lhss = {}
    used_lhss = set()
    seen_return = False
    for instruction in instructions:
        source = instruction['source']
        lhs = instruction['lhs']
        operator = instruction['operator']
        actual_params = instruction['params']
        actual_param_count = len(actual_params)

        # Check lhs is not duplicate
        if lhs in seen_lhss:
            return False, {'code': ERR_DUPLICATE_LHS, 'instruction': source}

        # Check valid operator
        if operator not in supported_operators:
            return False, {'code': ERR_INVALID_OPERATOR, 'instruction': source}

        # Check parameter count
        target_params = supported_operators[operator] if operator not in return_operators else supported_operators[operator] * actual_param_count
        target_param_count = len(target_params)

        if actual_param_count != target_param_count:
            return False, {'code': ERR_INVALID_PARAM_COUNT, 'instruction': source}

        # Check parameters
        for actual_param, target_param in zip(actual_params, target_params):
            if target_param == 'node_type' and actual_param not in supported_node_types:
                return False, {'code': ERR_INVALID_NODE_TYPE, 'instruction': source}

            elif target_param == 'field':
                if not isinstance(actual_param, str):
                    return False, {'code': ERR_INVALID_FIELD, 'instruction': source}

                if '(' in actual_param and ')' in actual_param:
                    return False, {'code': ERR_NESTED_OPERATOR, 'instruction': source}

            elif target_param == 'value' and not isinstance(actual_param, str):
                return False, {'code': ERR_INVALID_VALUE, 'instruction': source}

            elif target_param == 'order' and actual_param not in ['Ascending', 'Descending']:
                return False, {'code': ERR_INVALID_ORDER, 'instruction': source}

            elif target_param == 'int' and not actual_param.isdigit():
                return False, {'code': ERR_INVALID_INT, 'instruction': source}

            elif target_param == 'nodeset':
                if '(' in actual_param and ')' in actual_param:
                    return False, {'code': ERR_NESTED_OPERATOR, 'instruction': source}

                if actual_param not in seen_lhss:
                    return False, {'code': ERR_UNDEFINED_NODESET, 'instruction': source}

                used_lhss.add(actual_param)

        # Check set operations of the same node type
        if operator in set_operators:
            node_types = [seen_lhss[nodeset_name] for nodeset_name in actual_params]
            if len(set(node_types)) > 1:
                return False, {'code': ERR_SET_OPERATION_DIFFERENT_TYPES, 'instruction': source}

        # Check only one return
        if seen_return and operator in return_operators:
            return False, {'code': ERR_SEVERAL_RETURNS, 'instruction': source}

        # Check return is last
        if seen_return and operator not in return_operators:
            return False, {'code': ERR_INSTRUCTION_AFTER_RETURN, 'instruction': source}

        # Infer node type
        if operator in retrieval_operators:
            node_type = actual_params[0]
        elif operator in navigation_operators:
            node_type = actual_params[1]
        elif operator in manipulation_operators + set_operators:
            node_type = seen_lhss[actual_params[0]]
        else:
            node_type = None

        # Add instruction lhs and node type to list of seen lhss
        if lhs is not None:
            seen_lhss[lhs] = node_type

        # Update if seen return
        if operator in return_operators:
            seen_return = False

    # After iterating over all instructions, check whether all defined nodesets are used
    # This is not an error on itself, but a strong indicator that the instructions are wrong
    # In any case, they can be simplified by deleting the unused definitions, so we treat it as an error
    unused_lhss = set(seen_lhss.keys()) - used_lhss
    if len(unused_lhss) > 0:
        # Find instructions defining an unused lhs
        unused_instructions = [instruction for instruction in instructions if instruction['lhs'] in unused_lhss]
        # Return the first one
        return False, {'code': ERR_UNUSED_LHS, 'instruction': unused_instructions[0]['source']}

    # If we reach this point, everything was fine
    return True, {}


def follow_instructions(instructions):
    nodesets = {}
    for instruction in instructions:
        lhs = instruction['lhs']
        operator = instruction['operator']
        params = instruction['params']

        if operator == 'Search':
            nodeset = search_nodes(*params)
            nodeset = nodeset[:1]
            nodesets[lhs] = nodeset

        elif operator == 'All':
            [node_type, field, value] = params
            nodesets[lhs] = get_all_nodes_and_filter(node_type, field, value)

        elif operator == 'Neighborhood':
            [nodeset_name, node_type] = params
            nodesets[lhs] = get_neighborhood(nodesets[nodeset_name], node_type)

        elif operator == 'Filter':
            [nodeset_name, field, value] = params
            nodesets[lhs] = filter(nodesets[nodeset_name], field, value)

        elif operator == 'FilterRange':
            [nodeset_name, field, min_value, max_value] = params
            nodesets[lhs] = filter(nodesets[nodeset_name], field, (min_value, max_value))

        elif operator == 'Sort':
            [nodeset_name, field, order] = params
            nodesets[lhs] = sort(nodesets[nodeset_name], field, order)

        elif operator == 'Limit':
            [nodeset_name, n] = params
            nodesets[lhs] = limit(nodesets[nodeset_name], int(n))

        elif operator == 'Intersection':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_intersection(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Union':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_union(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Difference':
            [left_nodeset_name, right_nodeset_name] = params
            nodesets[lhs] = take_difference(nodesets[left_nodeset_name], nodesets[right_nodeset_name])

        elif operator == 'Return':
            return [nodesets[nodeset_name] for nodeset_name in params]

    # Fallback: If no return operation, return nodeset referenced last
    nodeset = nodesets[lhs]

    return [nodeset]


def find_instruction_index(instructions, lhs):
    for i in range(len(instructions)):
        if instructions[i]['lhs'] == lhs:
            return i

    return None


def build_context(instructions, i=-1):
    if i is None:
        return {}

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Search':
        [node_type, name] = params
        return {'operation': 'search', 'node_type': node_type, 'name': name}

    elif operator == 'All':
        [node_type, field, value] = params
        return {'operation': 'all', 'node_type': node_type, 'field': field, 'value': value}

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'neighborhood', 'node_type': node_type, 'child': build_context(instructions, j)}

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'filter', 'field': field, 'value': value, 'child': build_context(instructions, j)}

    elif operator == 'FilterRange':
        [nodeset_name, field, min_value, max_value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'filter_range', 'field': field, 'min_value': min_value, 'max_value': max_value, 'child': build_context(instructions, j)}

    elif operator == 'Sort':
        [nodeset_name, field, order] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'sort', 'field': field, 'order': order, 'child': build_context(instructions, j)}

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return {'operation': 'limit', 'n': int(n), 'child': build_context(instructions, j)}

    elif operator == 'Intersection':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'intersection', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Union':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'union', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Difference':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return {'operation': 'difference', 'left_child': build_context(instructions, left_j), 'right_child': build_context(instructions, right_j)}

    elif operator == 'Return':
        contexts = []
        for nodeset_name in params:
            j = find_instruction_index(instructions, nodeset_name)
            contexts.append(build_context(instructions, j))

        return contexts

    return []


def build_retry_message(error=None):
    if error is None:
        code = None
        instruction = None
    else:
        code = error['code']
        instruction = error['instruction']

    if code is None:
        msg = """There was a problem following these instructions."""
    elif code == ERR_DUPLICATE_LHS:
        msg = f"""The instruction "{instruction}" redefines the same nodeset."""
    elif code == ERR_NESTED_OPERATOR:
        msg = f"""The instruction "{instruction}" has a nested operator."""
    elif code == ERR_INVALID_OPERATOR:
        msg = f"""The instruction "{instruction}" contains an operator that was not specified above."""
    elif code == ERR_INVALID_PARAM_COUNT:
        msg = f"""The instruction "{instruction}" has a number of parameters different to what was specified."""
    elif code == ERR_INVALID_NODE_TYPE:
        msg = f"""The instruction "{instruction}" contains a node type that was not specified above."""
    elif code == ERR_INVALID_FIELD:
        msg = f"""The instruction "{instruction}" does not contain a valid field."""
    elif code == ERR_INVALID_VALUE:
        msg = f"""The instruction "{instruction}" does not contain a valid value."""
    elif code == ERR_INVALID_ORDER:
        msg = f"""The instruction "{instruction}" does not contain a valid order, it should be "Ascending" or "Descending"."""
    elif code == ERR_INVALID_INT:
        msg = f"""The instruction "{instruction}" does not contain a valid integer value."""
    elif code == ERR_UNDEFINED_NODESET:
        msg = f"""The instruction "{instruction}" references a nodeset that has not been defined before."""
    elif code == ERR_SET_OPERATION_DIFFERENT_TYPES:
        msg = f"""The instruction "{instruction}" performs a set operation on nodesets of different type."""
    elif code == ERR_SEVERAL_RETURNS:
        msg = f"""The instruction "{instruction}" is the second "Return" instruction. There should only be one "Return" instruction and it should be the last one."""
    elif code == ERR_INSTRUCTION_AFTER_RETURN:
        msg = f"""The instruction "{instruction}" comes after a "Return" instruction. There should only be one "Return" instruction and it should be the last one."""
    elif code == ERR_UNUSED_LHS:
        msg = f"""The instruction "{instruction}" defines a nodeset that is never used to build the returned nodesets."""
    else:
        msg = f"""The instruction "{instruction}" is not correct."""

    msg = f"""{msg} Give a new list of instructions which avoids this problem and still gives answer to the query. Reply only with the new list of instructions, nothing more."""
    return msg


################################################################
# TO BE REMOVED EVENTUALLY                                     #
################################################################


def emojify(node_type):
    if node_type == 'Concept':
        return '⚛️'
    elif node_type == 'Person':
        return '👤'
    elif node_type == 'Course':
        return '📚'
    elif node_type == 'Lecture':
        return '📖'
    elif node_type == 'Unit':
        return '🔬'
    elif node_type == 'Publication':
        return '📄'
    else:
        return ''


def pluralise(node_type):
    if node_type == 'Person':
        return 'People'
    else:
        return f"{node_type}s"


def build_context_message_step(instructions, i):
    if i is None:
        return ''

    operator = instructions[i]['operator']
    params = instructions[i]['params']

    if operator == 'Search':
        [node_type, name] = params
        return f"the {emojify(node_type)} {node_type} \"{name}\""

    elif operator == 'All':
        [node_type, field, value] = params
        return f"all {emojify(node_type)} {pluralise(node_type)}, filtered by {field}={value}"

    elif operator == 'Neighborhood':
        [nodeset_name, node_type] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{emojify(node_type)} {pluralise(node_type)} related to {build_context_message_step(instructions, j)}"

    elif operator == 'Filter':
        [nodeset_name, field, value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, filtered by {field}={value}"

    elif operator == 'FilterRange':
        [nodeset_name, field, min_value, max_value] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, filtered by {field} between {min_value} and {max_value}"

    elif operator == 'Sort':
        [nodeset_name, field, order] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"{build_context_message_step(instructions, j)}, sorted by {field} ({order})"

    elif operator == 'Limit':
        [nodeset_name, n] = params

        j = find_instruction_index(instructions, nodeset_name)

        return f"at most {n} {build_context_message_step(instructions, j)}"

    elif operator == 'Intersection':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the intersection of {build_context_message_step(instructions, left_j)} and {build_context_message_step(instructions, right_j)}"

    elif operator == 'Union':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the union of {build_context_message_step(instructions, left_j)} and {build_context_message_step(instructions, right_j)}"

    elif operator == 'Difference':
        [left_nodeset_name, right_nodeset_name] = params

        left_j = find_instruction_index(instructions, left_nodeset_name)
        right_j = find_instruction_index(instructions, right_nodeset_name)

        return f"the nodes in {build_context_message_step(instructions, left_j)} not in {build_context_message_step(instructions, right_j)}"

    elif operator == 'Return':
        context_messages = []
        for nodeset_name in params:
            j = find_instruction_index(instructions, nodeset_name)
            context_message = f"Showing {build_context_message_step(instructions, j)}"
            context_messages.append(context_message)

        return context_messages

    return []


def build_context_message(instructions):
    return build_context_message_step(instructions, -1)
