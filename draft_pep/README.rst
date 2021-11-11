PEP: 9999
Title: Callable Type Syntax
Author: Steven Troxler <steven.troxler@gmail.com>
Sponsor: TODO
Status: Draft
Type: Standards Track
Content-Type: text/x-rst
Created: xxx
Python-Version: 3.11
Post-History:

Abstract
========

This PEP introduces a concise and structured syntax for callable types, supporting the same functionality as ``typing.Callable`` but with an arrow syntax inspired by the syntax for typed function signatures.

If we adopt this proposal, the following annotated variables
::
  from typing import Awaitable, Callable, Concatenate, ParamSpec, TypeVarTuple

  P = ParamSpec("P")
  Ts = = TypeVarTuple('Ts')

  f0: TypeAlias Callable[[int, str], bool]
  f1: Callable[..., bool]
  f2: Callable[[str], Awaitlable[str]]
  f3: Callable[P, bool]
  f4: Callable[Concatenate[int, P], bool]
  f5: Callable[[*Ts], bool]
  f6: Callable[[int, *Ts, str], bool]


could be written instead as
::
  from typing import ParamSpec, TypeVarTuple

  P = ParamSpec("P")
  Ts = = TypeVarTuple('Ts')

  f0: (int, str) -> bool
  f1: (...) -> bool
  f2: async (str) -> str
  f3: (**P) -> bool
  f4: (int, **P) -> bool
  f5: (*Ts) -> bool
  f6: (int, *Ts, str) -> bool


Motivation
==========


The ``Callable`` type, defined as part of PEP 484, is one of the most commonly used complex types in ``typing`` alongside ``Union`` and collection types like ``Dict`` and ``List``.

It is common for ``Callable`` types to become verbose. A simplified real-world example from an asyncrhonous webserver illustrates how the types can be verbose, and we can get many levels of nested square brackets:

::
    from typing import Callable, Awaitable
    from app_logic import ActionRecord, AuthPermission, Request, Response

    def make_endpoint(
       formatter: Callable[
           [ActionRecord, list[AuthPermission]],
           FormattedItem
       ]
    ) -> Callable[
        [Request], Awaitable[Response]
    ]:
       ...

With our proposal, this code can be abbreviated to

::
    from app_logic import ActionRecord, AuthPermission, Request, Response

    def make_endpoint(
        formatter: (ActionRecord, list[AuthPermission]) -> FormattedItem,
    ) -> async (Request) -> Response:
        ...

This is shorter and requires fewer imports. It also has far less nesting of square brackets - only one level, as opposed to three in the original code.


ParamSpec and Concatenate
-------------------------

The example above illustrates how we get a more concise and visually rich syntax for simple ``Callable`` types. We also proposing to incorporate ``ParamSpec`` support in the syntax because (in part due to decorators) one common use case of callables is to forward all arguments.


With arrow-based ``Callable`` syntax this simple decorator
::
    from typing import Callable, ParamSpec

    P = ParamSpec("P")

    def decorator(
        f: Callable[P, bool],
    ) -> Callable[P, bool]:
        def wrapper(*args: P.args **kwargs: P.kwargs) -> bool:
            return f(*args, **kwargs)
        return wrapper


can be written
::
    from typing import ParamSpec

    P = ParamSpec("P")

    def decorator(
        f: (**P) -> bool
    ) -> (**P) -> bool:
        ...


The resulting code is more concise. Moreover, the ``**P`` makes it obvious that ``P`` is not a positional argument type, whereas it is easier to misread ``Callable[P, bool]`` as ``Callable[[P], bool]``, particularly for developers who are not yet familiar with ``ParamSpec``.


Our proposed syntax also supports ``Concatenate``. It would allow
::
    from typing import Callable, Concatenate, ParamSpec

    P = ParamSpec("P")

    def with_printing(
       f: (**P) -> bool,
    ) -> Callable[Concatenate[str, P], bool]
        def wrapper(message: str, *args: P.args **kwargs: P.kwargs) -> bool:
            print(message)
            return f(*args, **kwargs)
        return wrapper

to be written
::
    from typing import ParamSpec

    P = ParamSpec("P")

    def with_printing(
       f: (**P) -> bool,
    ) -> (str, **P) -> bool:
       ...


TypeVarTuple
------------

According to PEP 646 ``Callable`` should support a splat syntax for passing ``*args`` along to a callback in a type-safe way using ``TypeVarTuple``. For example:

::
    from typing import Callable, Tuple, TypeVarTuple

    def call_target_with_args(
        target: Callable[[*Ts], bool],
        args: Tuple[*Ts],
    ) -> bool:
        return target(*args)

    def f(arg1: int, arg2: str) -> bool : ...

    call_target_with_args(target=f, args=(0, 'foo'))  # Valid
    call_target_with_args(target=f, args=('foo', 0))  # Error

We propose using a similar single-splat syntax so that the code above could be written as

::
    from typing import Callable, Tuple, TypeVarTuple
    def call_target_with_args(
        target: (*Ts) -> bool,
        args: Tuple[*Ts],
    ) -> bool:
        return target(*args)

It is possible to include additional positional arguments around the ``*Ts``, which we would still support, e.g.  ``(int, *Ts, str) -> R`` should be equivalent to ``Callable[[int, *Ts, str], R]``.

QUESTION FOR EDITORS: what do I say about the fact that PEP 646 is still not accepted, but that's because of the grammar changes - the specific functionality we're outlining here doesn't require the grammar changes that are the most controversial bit; it only really requires typecheckers to understand ``TypeVarTuple``.

Usage Statistics
----------------

The ``Callable`` type is widely used. For example, in typeshed [#typeshed-stats]_ it is the fifth most common complex type, after ``Optional``, ``Tuple``, ``Union``, and ``List``. Most of these have gotten improved syntax either via PEP 604 or PEP 525. We believe ``Callable`` is heavily enough used to similarly justify a more usable syntax, particularly given that the need for two layers of square brackets in most ``Callable`` types.


Our decision to support ``ParamSpec``, ``Concatenate``, and ``TypeVarTuple`` is informed by looking at how frequently these features are used both in existing ``Callable`` types as well as in untyped callback functions.

Of existing callable types [#callable-type-usage-stats]_,
 - 57% use only positional arguments
 - 43% use partial typing (e.g. bare ``Callable`` or ``Callable[..., R]``). We'll look at the actual use of callbacks shortly to understand why these callables may be partially-typed.
 - 1% use Callback protocols, which support features like named arguments that ``Callable`` cannot handle
[#callable-type-usage-stats]_ and how often callbacks (whether or not they are typed) use call patterns requiring various features [#callback-usage-stats-typed]__
We want to be sure that we support the most common uses of ``Callable``.

In typed projects, when we look at the actual call patterns for callbacks [#typed-callback-usage]_, what we see is that
* 69% use only positional arguments.
* 9% pass along ``*args`` and ``**kwargs``, which can be made type-safe using ``ParamSpec``.
* 10% pass along just ``*args``, which we can support using ``TypeVarTuple``.
* The remainder make use of features that neither ``Callable`` nor our proposed syntax support.

In untyped projects, which are less constrained by the existing features of ``Callable``, we see a different balance but a similar overall pattern:
* 43% use only positional arguments.
* 26% pass along ``*args`` and ``**kwargs`` and so would benefit from ``ParamSpec``.
* 4% pass along just ``*args``.
* The remainder use features that neither the current ``Callable`` nor our proposal support. And once again only about 2% are using named or default
* 10% pass along just ``*args``, which we can support using ``TypeVarTuple``
* The remainder make use of features that neither ``Callable`` nor our proposed syntax support.

For both untyped *and* typed projects, the fraction of callbacks making use of named and/or optional arguments is around 2%. This is part of why we decided to propose a simple syntax supporting the same features as ``Callable`` rather than an extended syntax supporting named and optional arguments, which are currently possible to describe using callback protocols [#callback-protocols**_


==========================================
Outline of possible sections and resources
==========================================

PEP 604: similar in spirit, also a very similar PEP:
https://www.python.org/dev/peps/pep-0604/

PEP 646: the other current typing PEP that's waiting for grammar changes:
https://www.python.org/dev/peps/pep-0646/

PEP 612 (ParamSpec), which has some overlap in the motivation (although our motivation is really closer to 604, since we're only proposing nicer syntax rather than new semantics):
https://www.python.org/dev/peps/pep-0612

Specification
=============

Grammar
-------

I can start from https://docs.google.com/document/d/1Ookl5s6LM1zZo5rSQpxiOfGknriW9-GRbTWtn8Q0a44/edit

Typing Behavior
---------------

Inside of type checkers, the new syntax should be treated with exactly the same semantics as ``typing.Callable``.

Going back to the examples from our abstract, type checkers should treat the following module
::
  from typing import ParamSpec, TypeVarTuple

  P = ParamSpec("P")
  Ts = = TypeVarTuple('Ts')

  f0: (int, str) -> bool
  f1: (...) -> bool
  f2: async (str) -> str
  f3: (**P) -> bool
  f4: (int, **P) -> bool
  f5: (*Ts) -> bool
  f6: (int, *Ts, str) -> bool

in exactly the same way as the same module written in terms of ``Callable``:
::
  from typing import Awaitable, Callable, Concatenate, ParamSpec, TypeVarTuple

  P = ParamSpec("P")
  Ts = = TypeVarTuple('Ts')

  f0: TypeAlias Callable[[int, str], bool]
  f1: Callable[..., bool]
  f2: Callable[[str], Awaitlable[str]]
  f3: Callable[P, bool]
  f4: Callable[Concatenate[int, P], bool]
  f5: Callable[[*Ts], bool]
  f6: Callable[[int, *Ts, str], bool]


Runtime Behavior
----------------

Rejected Alternatives
=====================

Syntax Closer to Function Signatures
------------------------------------

Talk here about:
- the motivation to avoid unfamiliar syntax
- the basic idea
- why we rejected it
  - the requirement for / was considered a deal-breaker
  - the inability to properly support ParamSpec following PEP 612 scope rules
  - arg names would have meant more verbose, and nuisance parameters

Extended Syntax Supporting Named and Optional Arguments
-------------------------------------------------------

Talk here about
- the motivation to support named and optional arguments
- opinions are mixed about whether this is worth doing, given that
  - ~2% of use cases seem affected
  - callback protocols work for this, and we could make them more ergonomic via functions-as-types
- the proposal is backward compatible with the one we are making

Reference Implementation
========================

TODO. This will require a fork of CPython with the new grammar.


Resources
=========

PEP 484 specifies a very similar syntax for function type hint *comments* for use in code that needs to work on Python 2.7: [#pep-484-function-type-hints]_

**Maggie** proposed better callable type syntax at the PyCon Typing Summit 2021: [#type-syntax-simplification]_ ([#type-variables-for-all-slides]_).

**Steven** brought up this proposal on typing-sig: [#typing-sig-thread]_.

**Pradeep** brought this proposal to python-dev for feedback: [#python-dev-thread]_.

Other languages use a similar arrow syntax to express callable types:
Kotlin uses ``->`` [#kotlin]_
Typescript uses ``=>`` [#typescript]_
Flow uses ``=>`` [#flow]_

Thanks to the following people for their feedback on the PEP:

Guido Van Rossum, Pradeep Kumar Srinivasan, Eric Taub
TODO: ADD MANY MORE THANKS. (keep it alphabetical).


References
==========

.. [#typeshed-stats] Overall type usage for typeshed

    https://github.com/pradeep90/annotation_collector#overall-stats-in-typeshed

.. [#callable-type-usage-stats] Callable type usage stats

    https://github.com/pradeep90/annotation_collector#typed-projects---callable-type

.. [#typed-callback-usage] Callback usage stats in typed projects

    https://github.com/pradeep90/annotation_collector#typed-projects---callback-usage

.. [#typed-callback-usage] Callback usage stats in typed projects

    https://github.com/pradeep90/annotation_collector#typed-projects---callback-usage

.. [#pep-484-callable] Callable type as specified in PEP 484

    https://www.python.org/dev/peps/pep-0484/#callable

.. [#pep-484-function-type-hints] Function type hint comments, as outlined by PEP 484 for Python 2.7 code

    https://www.python.org/dev/peps/pep-0484/#suggested-syntax-for-python-2-7-and-straddling-code

.. [#callback-protocols] Callback protocols

    https://mypy.readthedocs.io/en/stable/protocols.html#callback-protocols

.. [#typing-sig-thread] Discussion of Callable syntax in the typing-sig mailing list.

    https://mail.python.org/archives/list/typing-sig@python.org/thread/3JNXLYH5VFPBNIVKT6FFBVVFCZO4GFR2/

.. [#callable-syntax-proposals-slides] Slides discussing potential Callable syntaxes (from 2021-09-20)

    https://www.dropbox.com/s/sshgtr4p30cs0vc/Python%20Callable%20Syntax%20Proposals.pdf?dl=0

.. [#python-dev-thread] Discussion of new syntax on the python-dev mailing list

    https://mail.python.org/archives/list/python-dev@python.org/thread/VBHJOS3LOXGVU6I4FABM6DKHH65GGCUB/

.. [#callback-protocols] Callback protocols, as described in MyPy docs

    https://mypy.readthedocs.io/en/stable/protocols.html#callback-protocols

.. [#sc-note-about-annotations] Steering Council note about type annotations and regular python

    https://mail.python.org/archives/list/python-dev@python.org/message/SZLWVYV2HPLU6AH7DOUD7DWFUGBJGQAY/

.. [#type-syntax-simplification] Slides on type syntax simplification from PyCon 2021

    TODO: get this, reach out to Maggie if I can't find it

.. [#typescript] Callable types in TypeScript

    https://basarat.gitbook.io/typescript/type-system/callable#arrow-syntax

.. [#kotlin] Callable types in Kotlin

    https://kotlinlang.org/docs/lambdas.html#function-types

.. [#flow] Callable types in Flow

    https://flow.org/en/docs/types/functions/#toc-function-types

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
