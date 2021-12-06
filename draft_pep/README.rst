PEP: 9999
Title: Callable Type Syntax
Author: Steven Troxler <steven.troxler@gmail.com>,
        Pradeep Kumar Srinivasan <gohanpra@gmail.com>
Sponsor: TODO
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: xxx
Python-Version: 3.11
Post-History:

Abstract
========

This PEP introduces a concise and structured syntax for callable types, supporting the same functionality as ``typing.Callable`` but with an arrow syntax inspired by the syntax for typed function signatures. This allows types like ``Callable[[int, str], bool]`` to be written ``(int, str) -> bool``.

The proposed syntax supports all the functionality of the existing ``Callable`` time, including ``ParamSpec`` as specified in PEP 612 and ``TypeVarTuple`` as specified by PEP 646.


Motivation
==========


The ``Callable`` type, defined as part of PEP 484, is one of the most commonly used complex types in ``typing`` alongside ``Union`` and collection types like ``Dict`` and ``List``.


There are three major problems with the existing ``Callable`` type:
- it is verbose, particularly for more complex function signatures.
- it does not visually represent the way function headers are written.
- it relies on two levels of nested square brackets. This can be quite hard to read,
  especially when the function arguments themselves have square brackets.
- it requires an explicit import, something we no longer require for most of the other
  very common types after PEP 604 and PEP 525


It is common for ``Callable`` types to become verbose. A simplified real-world example from a web server illustrates how the types can be verbose and require many levels of nested square brackets::

    from typing import Callable
    from app_logic import Response, UserSetting


    def customize_response_for_settings(
        response: Response,
        customizer: Callable[
            [Response, list[UserSetting]],
            FormattedItem
        ]
    ) -> Response
       ...

With our proposal, this code can be abbreviated to::

    from app_logic import Response, UserSetting

    def make_endpoint(
        response: Response,
        customizer: (Response, list[UserSetting]) -> Response,
    ) -> Response:
        ...

This is shorter and requires fewer imports. It also has far less nesting of square brackets - only one level, as opposed to three in the original code.

Rationale
---------

The ``Callable`` type is widely used. For example, in typeshed [#typeshed-stats]_ it is the fifth most common complex type, after ``Optional``, ``Tuple``, ``Union``, and ``List``.

Most of the other commonly used types have gotten improved syntax either via PEP 604 or PEP 525. We believe ``Callable`` is heavily enough used to similarly justify a more usable syntax, particularly given the need for two layers of square brackets in most ``Callable`` types.

Our decision to support ``ParamSpec``, ``Concatenate``, and (assuming PEP 646 is accepted) ``TypeVarTuple`` is informed by looking at how frequently these features are used both in existing ``Callable`` types as well as in untyped callback functions. See the Rejected Alternatives section for more details about why we came to this proposal.

A special case that ``Callable`` cannot support is the use of named or optional (i.e. having a default value) arguments. These currently can be typed using callback protocols [#callback-protocols]_, but not the ``Callable`` type. For both typed and untyped projects, the fraction of callbacks using named or optional arguments is less than 2%.


Specification
=============

Typing Behavior
---------------

Inside of type checkers, the new syntax should be treated with exactly the same semantics as ``typing.Callable``.

So a type checker should treat the following pairs exactly the same::

   from typing import Awaitable, Callable, Concatenate, ParamSpec, TypeVarTuple

    P = ParamSpec("P")
    Ts = = TypeVarTuple('Ts')

    f0: (int, str) -> bool
    f0: TypeAlias Callable[[int, str], bool]
    
    f1: (...) -> bool
    f1: Callable[..., bool]

    f2: async (str) -> str
    f2: Callable[[str], Awaitable[str]]
 
    f3: (**P) -> bool
    f3: Callable[P, bool]

    f4: (int, **P) -> bool
    f4: Callable[Concatenate[int, P], bool]
    
    f5: (*Ts) -> bool
    f5: Callable[[*Ts], bool]

    f6: (int, *Ts, str) -> bool
    f6: Callable[[int, *Ts, str], bool]

Grammar and Ast
---------------

The new syntax we’re proposing can be described by these Ast changes ::

    expr = <prexisting_expr_kinds>
         | AsyncCallableType(callable_type_arguments args, expr returns)
         | CallableType(callable_type_arguments args, expr returns)
                                                                           	 
    callable_type_arguments = AnyArguments
                            | ArgumentsList(expr* posonlyargs)
                            | Concatenation(expr* posonlyargs, expr param_spec)


Here are our proposed changes to the [#python-grammar]_::

    expression:
        | disjunction disjunction 'else' expression
        | callable_type_expression
        | disjunction
        | lambdef

    callable_type_expression:
        | callable_type_arguments '->' expression
        | ASYNC callable_type_arguments '->' expression

    callable_type_arguments:
        | '(' '...' ')'
        | '(' callable_type_positional_argument*  ')'
        | '(' callable_type_positional_argument* ps=callable_type_param_spec ')'

    callable_type_positional_argument:
        | expression ','
        | expression &')'

    callable_type_param_spec:
        | '**' expression ','
        | '**' expression &')'



If PEP 646 is accepted, we intend to include support for unpacked types by modifying the grammar for ``callable_type_positional_argument`` as follows::

    callable_type_positional_argument:
        | expression ','
        | expression &')'
        | '*' expression ','
        | '*' expression &')'


Runtime Behavior
----------------

The precise details of runtime behavior are still under active discussion. We are confident of these aspects:
- The new syntax will evaluate to a C-defined type, probably defined in ``builtins``.
- The new C-defined type must be consistent with existing `typing.Callable` behavior. Specifically:
  - The ``__args__`` and ``__parameters__`` fields must behave the same way
  - Comparing equivalent builtin and ``typing.Callable`` types with ``==`` must return `True` 

A number of details remain to be determined:
- Whether to have a more structured API than ``__args__`` and ``__parameters__``.
- How to make `typing.Callable` behave the same:
  - We could make it desugar to the builtin type so they are certain to be consistent
  - Or we could use runtime logic to make them consistent and attempt to test all edge cases. This is the approach that was taken for PEP 604 type union syntax.



Rejected Alternatives
=====================

Many of the alternatives we considered would have been more powerful than ``typing.Callable``, for example adding support for describing signatures that include named, optional, and variadic arguments.

We decided on a simple proposal focused just on improving syntax for the existing ``Callable`` type based on an extensive analysis of existing projects (see [#callable-type-usage-stats]_, [#callback-usage-stats-typed]_, [#callback-usage-stats]_). We determined that the vast majority of callbacks can be correctly described by the existing ``typing.Callable`` semantics:
- By far the most important case to handle well is simple callable types with positional args, such as ``(int, str) -> bool``
- The next most important feature is good support for PEP 612 ``ParamSpec`` and ``Concatenate`` types like ``(**P) -> bool`` and ``(int, **P) -> bool``. These are common primarily because of the heavy use of decorator patterns in python code.
- The next most important feature, assuming PEP 646 is accepted, is for unpacked types which are common because of cases where a wrapper passes along `*args` to some other function.

Features that other, more complicated proposals would support account for fewer than 2% of the use cases we found. These are already possible using callable Protocols, and since they aren’t common we decided that it made more sense to move forward with a simpler syntax.

Syntax Closer to Function Signatures
------------------------------------

One alternative we had floated was a syntax much more similar to function signatures.

In this proposal, the following types would have been equivalent::

    class Function(typing.Protocol):
        def f(self, x: int, /, y: float, *, z: bool = ..., **kwargs: str) -> bool:
            ...

    Function = (x: int, /, y: float, *, z: bool = ..., **kwargs: str) -> bool


The benefits of this proposal would have included
- Perfect syntactic consistency between signatures and callable types
- Support for most features of function signatures (named, optional, variadic args)

Key downsides that led us to reject the idea include the following:
- A large majority of use cases only use positional-only arguments, and this syntax would be more verbose for that use case, both because of requiring argument names and an explicit ``/``.
- The requirement for explicit ``/`` for positional-only arguments has a high risk of causing frequent bugs - which often wouldn’t be detected by unit tests - where library authors would accidentally use types with named arguments.
- Our analysis suggests that support for ``ParamSpec`` is key, but the scope rules laid out in PEP 612 would have made this difficult.


Extended Syntax Supporting Named and Optional Arguments
-------------------------------------------------------

Another alternative was for a compatible but more complex syntax that could express everything in this PEP but also named, optional, and variadic arguments. In this “extended” syntax proposal the following types would have been equivalent::

    class Function(typing.Protocol):
        def f(self, x: int, /, y: float, *, z: bool = ..., **kwargs: str) -> bool:
            ...

    Function = (int, y: float, *, z: bool = ..., **kwargs: str) -> bool

Advantages of this syntax include:
- Most of the advantages of the proposal in this PEP (conciseness, PEP 612 support, etc)
- Furthermore, the ability to handle named, optional, and variadic arguments

We decided against proposing it for the following reasons:
- The implementation would have been more difficult, and usage stats demonstrate that fewer than 3% of use cases would benefit from any of the added features.
- The group that debated these proposals was split down the middle about whether these changes are even desirable:
  - On the one hand they make callable types more powerful, but on the other hand they could easily confuse users who haven’t read the full specification of callable type syntax.
  - We believe the simpler syntax proposed in this PEP, which introduces no new semantics and closely mimics syntax in other popular languages like Kotlin, Scala, and TypesScript, are much less likely to confuse users.
- We intend to implement the current proposal in a way that is forward-compatible with the more complicated extended syntax. So if the community decides after more experience and discussion that we want the additional features they should be straightforward to propose in the future.

We confirmed that the current proposal is forward-compatible with extended syntax by implementing a quick-and-dirty grammar and AST on top of the grammar and AST for the current proposal [#callable-type-syntax--extended]_.


Requiring Parentheses For Function Types in Return Position 
-----------------------------------------------------------

In the case where multiple ``->`` and ``|`` tokens exist in the same toplevel, our grammar behaves right-associatively. So, for example:
- The type ``(int) -> str | bool`` is equivalent to ``(int) -> (str | bool)``
- The type ``(int) -> (str) -> bool`` is equivalent to ``(int) -> ((str) -> bool)``

Moreover, the following annotation is legal, here ``f`` returns an ``(int) -> bool``::

    def f() -> (int) -> bool:
       return lambda x: x == 0

We considered preventing these in the grammar, but decided that it was better not to every way we looked at the issue:
- Most languages that use arrow-based function types, including TypeScript and Scala, make them right-associative.
- We believe it would be bad to raise ``SyntaxErrors``. If developers want to encourage explicit parentheses they are free to do so in linters and style guides.
- A grammar requiring parentheses would be more complex and harder to read.

Backwards Compatibility
=======================

This PEP proposes a major syntax improvement over ``typing.Callable``, but the static semantics are the same.

As such, the only thing we need for backward compatibility is to ensure that types specified via the new syntax behave the same as equivalent ``typing.Callable`` values.

This is discussed in more detail in the Runtime Behavior section.


Reference Implementation
========================

We have a working implementation of the Ast and Grammar [#callable-type-syntax--shorthand]_ with tests verifying that the grammar proposed here has the desired behaviors.

There is no runtime implementation yet, we need feedback on this PEP before we can invest the time, but we have a doc describing our planned behavior in detail, including all the aspects we are aware of needed for backward compatibility [#runtime-design-notes]_.   TODO: CREATE THE RUNTIME DESIGN NOTES DOC


Resources
=========

Background and History
----------------------

PEP 484 specifies a very similar syntax for function type hint *comments* for use in code that needs to work on Python 2.7: [#pep-484-function-type-hints]_

**Maggie** proposed better callable type syntax at the PyCon Typing Summit 2021: [#type-syntax-simplification]_ ([#type-variables-for-all-slides]_).

**Steven** brought up this proposal on typing-sig: [#typing-sig-thread]_.

**Pradeep** brought this proposal to python-dev for feedback: [#python-dev-thread]_.

Other Languages
---------------

Other languages use a similar arrow syntax to express callable types:
Kotlin uses ``->`` [#kotlin]_
Typescript uses ``=>`` [#typescript]_
Flow uses ``=>`` [#flow]_

Acknowledgments
---------------

Thanks to the following people for their feedback on the PEP and help planning the reference implementation:

Guido Van Rossum, Eric Traut, Maggie Moss, Shannon Zhu

TODO: MAKE SURE THE THANKS STAYS UP TO DATE


References
==========

.. [#callable-type-syntax--shorthand] Reference implementation of proposed syntax: https://github.com/stroxler/cpython/tree/callable-type-syntax--shorthand

.. [#callable-type-syntax--extended] Bare-bones implementation of extended syntax, to demonstrate that shorthand is forward-compatible: https://github.com/stroxler/cpython/tree/callable-type-syntax--extended


.. [#ast-and-runtime-design-discussion] Detailed discussion of our reasoning around the proposed AST and runtime data structures: https://docs.google.com/document/d/1AJ0R7lgcKY0gpZbkBZRxXTvgV-OqxMYDj_JOPYMQFP8/edit


.. [#typeshed-stats] Overall type usage for typeshed: https://github.com/pradeep90/annotation_collector#overall-stats-in-typeshed

.. [#callable-type-usage-stats] Callable type usage stats: https://github.com/pradeep90/annotation_collector#typed-projects---callable-type

.. [#callback-usage-stats] Callback usage stats in open-source projects: https://github.com/pradeep90/annotation_collector#typed-projects---callback-usage

.. [#pep-484-callable] Callable type as specified in PEP 484: https://www.python.org/dev/peps/pep-0484/#callable

.. [#pep-484-function-type-hints] Function type hint comments, as outlined by PEP 484 for Python 2.7 code: https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code

.. [#callback-protocols] Callback protocols: https://mypy.readthedocs.io/en/stable/protocols.html#callback-protocols

.. [#typing-sig-thread] Discussion of Callable syntax in the typing-sig mailing list: https://mail.python.org/archives/list/typing-sig@python.org/thread/3JNXLYH5VFPBNIVKT6FFBVVFCZO4GFR2/

.. [#callable-syntax-proposals-slides] Slides discussing potential Callable syntaxes (from 2021-09-20): https://www.dropbox.com/s/sshgtr4p30cs0vc/Python%20Callable%20Syntax%20Proposals.pdf?dl=0

.. [#python-dev-thread] Discussion of new syntax on the python-dev mailing list: https://mail.python.org/archives/list/python-dev@python.org/thread/VBHJOS3LOXGVU6I4FABM6DKHH65GGCUB/

.. [#callback-protocols] Callback protocols, as described in MyPy docs: https://mypy.readthedocs.io/en/stable/protocols.html#callback-protocols

.. [#sc-note-about-annotations] Steering Council note about type annotations and regular python: https://mail.python.org/archives/list/python-dev@python.org/message/SZLWVYV2HPLU6AH7DOUD7DWFUGBJGQAY/

.. [#type-syntax-simplification] Presentation on type syntax simplification from PyCon 2021: https://drive.google.com/file/d/1XhqTKoO6RHtz7zXqW5Wgq9nzaEz9TXjI/view

.. [#python-grammar] Python's PEG grammar: https://docs.python.org/3/reference/grammar.html

.. [#callable-syntax-grammar-doc] Google doc with BNF and PEG grammar for callable type syntax: https://docs.google.com/document/d/12201yww1dBIyS6s0FwdljM-EdYr6d1YdKplWjPSt1SE/edit

.. [#typescript] Callable types in TypeScript: https://basarat.gitbook.io/typescript/type-system/callable#arrow-syntax

.. [#kotlin] Callable types in Kotlin: https://kotlinlang.org/docs/lambdas.html#function-types

.. [#flow] Callable types in Flow: https://flow.org/en/docs/types/functions/#toc-function-types

Copyright
=========

This document is placed in the public domain or under the
CC0-1.0-Universal license, whichever is more permissive.


..
   Local Variables:
   mode: indented-text
   indent-tabs-mode: nil
   sentence-end-double-space: t
   fill-column: 70
   coding: utf-8
   End:


