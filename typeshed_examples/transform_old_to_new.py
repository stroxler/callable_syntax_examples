import functools
import os

from typing import Union

import libcst
import libcst.matchers

_current_line = None

TYPESHED_EXAMPLES = os.path.dirname(__file__)
DEDUPLICATED_TXT_FILE = os.path.join(
    TYPESHED_EXAMPLES, "deduplicated_examples.txt"
)
OUTPUT_FILE = os.path.join(
    TYPESHED_EXAMPLES, "transformed_examples.txt"
)


with open(DEDUPLICATED_TXT_FILE, 'r') as f:
    raw_lines = f.readlines()
    lines = [line[4:] for line in raw_lines if line.startswith("    ")]


# These helper functions are stolen from pyre-check/client/commands/infer.py


@functools.lru_cache()
def empty_module() -> libcst.Module:
    return libcst.parse_module("")


def code_for_node(node: libcst.CSTNode) -> str:
    return empty_module().code_for_node(node)



class CallableToCallableSyntaxTransformer(libcst.CSTTransformer):
    def __init__(self):
        """
        This is a super hacky transformer because the syntax we want to transform
        to does not yet exist. As a result, we transform into strings with special
        markers that we can then trivally remove via string manipulation after
        dumping the transformed CST to a string. This is ugly but works and I could
        not think of a better quick-and-dirty alternative.
        """
        super().__init__()

    def leave_Subscript(
        self,
        original_node: libcst.Subscript,
        updated_node: Union[libcst.Tuple, libcst.Subscript, libcst.SimpleString],
    ):
        if libcst.matchers.matches(
            updated_node.value, libcst.matchers.Name("Concatenate")
        ):
            return self.concatenate_to_new_syntax_as_string(
                parameters=updated_node.slice,
            )
            import pudb; pudb.set_trace()
        if libcst.matchers.matches(
            updated_node.value, libcst.matchers.Name("Callable")
        ):
            return self.callable_to_new_syntax_as_string(
                parameters=updated_node.slice[0].slice.value
                returns=updated_node.slice[1].slice.value
            )
            import pudb; pudb.set_trace()
        return original_node

    def concatenate_to_new_syntax_as_string(
        self,
        parameters: List[libcst.SubscriptElement]
    ) -> FILL_ME:
        FILL_ME

    def callable_to_new_syntax_as_string(
        self,
        parameters: Union[libcst.Tuple, libcst.Ellipsis, libcst.List],
        return_type: libcst.Node,
    ) -> LibCST.SimpleString:
        if libcst.matchers.matches(
            parameters, libcst.Tuple:
        ):
            parameters_as_tuple = parameters
        elif libcst.matchers.matches(
            parameters, libcst.Ellipses:
        ):
            parameters_as_tuple = libcst.Tuple(elements=libcst.Ellipsis())
        elif libcst.matchers.matches(
            parameters, libcst.List:
        ):
            parameters_as_tuple = libcst.Tuple(elements=parameters.elements)
        parameters_as_tuple_str = code_for_node(parameters_as_tuple)
        return_type_str = code_for_node(return_type)
        return libcst.SimpleString(f"'<ct>{parameters_as_tuple_str} -> {return_type_str}<ct>'")






transformed_lines = []
for line in lines:
    print(line)
    _current_line = line
    original_tree = libcst.parse_module(line)
    transformed_tree = original_tree.visit(
        CallableToCallableSyntaxTransformer()
    )
    transformed_line_as_ct_string = transformed_tree.code
    print(transformed_line_as_ct_string)
    import pudb; pudb.set_trace()




with open(OUTPUT_FILE, 'w') as f:
    f.writelines(transformed_lines)
