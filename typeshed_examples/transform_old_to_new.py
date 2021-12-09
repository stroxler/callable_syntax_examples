import functools
import os
import sys

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
        updated_node: libcst.Subscript,
    ) -> Union[libcst.BinaryOperation, libcst.Subscript]:
        if libcst.matchers.matches(
            updated_node.value, libcst.matchers.Name("Concatenate")
        ):
            raise NotImplementedError(
                "There are currently no Concatenates in our examples, deferring implementation"
            )
        if libcst.matchers.matches(
            updated_node.value, libcst.matchers.Name("Callable")
        ):
            return self.callable_to_new_syntax_as_string(
                parameters=updated_node.slice[0].slice.value,
                return_type=updated_node.slice[1].slice.value,
            )
        return original_node

    def callable_to_new_syntax_as_string(
        self,
        parameters: Union[libcst.Tuple, libcst.Ellipsis, libcst.List],
        return_type: libcst.CSTNode,
    ) -> libcst.BinaryOperation:
        if libcst.matchers.matches(
            parameters, libcst.matchers.Name()
        ):
            transformed_parameters = libcst.Tuple(
                elements=[
                    libcst.Element(libcst.SimpleString("'**'")),
                    libcst.Element(parameters)
                ]
            )
        elif libcst.matchers.matches(
            parameters, libcst.matchers.Tuple()
        ):
            transformed_parameters = parameters
        elif libcst.matchers.matches(
            parameters, libcst.matchers.Ellipsis()
        ):
            transformed_parameters = libcst.Ellipsis(lpar=[libcst.LeftParen()], rpar=[libcst.RightParen()])
        elif libcst.matchers.matches(
            parameters, libcst.matchers.List()
        ):
            transformed_parameters = libcst.Tuple(elements=parameters.elements)
        else:
            raise RuntimeError("oops")
        return libcst.BinaryOperation(
            left=transformed_parameters,
            right=return_type,
            operator=libcst.Add(),
        )






transformed_lines = []
for line in lines:
    try:
        print(line)
        _current_line = line
        original_tree = libcst.parse_module(line)
        transformed_tree = original_tree.visit(
            CallableToCallableSyntaxTransformer()
        )
        raw_transformed_line = transformed_tree.code
        transformed_line = (
            raw_transformed_line.replace("'**', ", "**").replace("+", "->")
        )
        print(transformed_line)
        transformed_lines.append(transformed_line)
        print()
    except Exception as e:
        _, _, tb = sys.exc_info()
        import pudb; pudb.post_mortem(tb)




with open(OUTPUT_FILE, 'w') as f:
    f.writelines(transformed_lines)
