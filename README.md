# Example of Callable Syntax Alternatives

This codebase is a snippet of simplified but realistic request-handling
middleware lifted from a django app that requires typed Callables.

Here's the snippet using existing python syntax:
```python
from typing import Awaitable, Callable, List, Optional

from django.http.request import HttpRequest
from django.http.response import HttpResponse

from app_logic import (
    render_page,
    fetch_history,
    format_purchase,
    ActionRecord,
    AuthPermission,
    FormattedItem,
)


def make_history_endpoint(
    action_type: str,
    *,
    formatter: Callable[
        [ActionRecord, List[AuthPermission]],
        FormattedItem
    ]
) -> Callable[[HttpRequest], Awaitable[HttpResponse]]:
    async def handle(request: HttpRequest) -> HttpResponse:
        permissions = get_permissions(request.user_id)
        actions = await fetch_history(action_type)
        return render_page(
            formatter(action, permissions) for action in actions
        )
    return handle


def purchase_formatter(
    purchase: ActionRecord,
    permissions: List[AuthPermission]
):
    purchase.check_can_view_history(permissions)
    return format_purchase(purchase)



purchases_endpoint: Callable[
    [HttpRequest], Awaitable[HttpResponse]
] = (
    action_type="purchase",
    formatter=purchase_history_formatter,
)
```

# Using shorthand syntax

With shorthand syntax, the signature of `make_history_endpoint` can be written
like this:

``` python
def make_history_endpoint(
    action_type: str,
    *,
    formatter: (
        ActionRecord, List[AuthPermission],
    ) -> FormattedItem,
) -> async (HttpRequest) -> HttpResponse:
    ...

```

The semantics of this shorthand syntax are identical to `Callable`, other than
that we can use an `async` prefix to wrap the return type in an `Awaitable`.

The purchases endpoint annotation can be written as:
```python
purchases_endpoint: async (HttpRequest) -> HttpResponse
] = (
    action_type="purchase",
    formatter=purchase_history_formatter,
)
```

# Using def-style syntax with positional arguments

If we use def-style syntax to adapt this code with its existing semantics,
the middleware maintainer is required to use positional-only arguments.

The signature of `make_history_endpoint` can be written either with
a trailing `/` to indicate that arguments are positional:
```python
def make_history_endpoint(
    action_type: str,
    *,
    formatter: (
        action: ActionRecord,
        permissions: List[AuthPermission],
        /
    ) -> FormattedItem,
) -> async (r: HttpRequest, /) -> HttpResponse:
    ...
```

or using `__`-prefixed variable names:
```python
def make_history_endpoint(
    action_type: str,
    *,
    formatter: (
        __actions: List[ActionRecord],
        __permissions: List[AuthPermission],
    ) -> List[FormattedItem],
) -> async (__r: HttpRequest, /) -> HttpResponse:
    ...
```

If we don't want to break existing use cases, where handler implementors
are free to use a variable name (like `purchase`) that is specific to
one particular situation, then we need to be careful to use positional-only
arguments.

The purchases endpoint annotation can be written in def-style as:
```python
purchases_endpoint: async (r: HttpRequest, /) -> HttpResponse
] = (
    action_type="purchase",
    formatter=purchase_history_formatter,
)
```

# Using def-style syntax with named arguments

The flip side of def-style syntax requiring `/` for all existing Callable
types is that we can intentionally pin the variable names, and then call
functions with named arguments.

For example, the middleware author could write this code, which isn't expressible
using the existing `Callable` type because of its use of named arguments:
``` python
def make_history_endpoint(
    action_type: str,
    formatter: (
        action: ActionRecord,
        permissions: List[AuthPermission],
    ) -> FormattedItem,
) -> async (r: HttpRequest) -> HttpResponse:
    async def handle(request: HttpRequest) -> HttpResponse:
        permissions = get_permissions(request.user_id)
        actions = await fetch_history(action_type)
        return render_page(
            formatter(action=action, permissions=permissions)
            for action in actions
        )
    return handle
```

But now the implementation of `purchase_formatter` is incorrect: we used
the variable name `purchase` for the purchases but the use of named-or-positional
arguments means all implementations have to use the generic variable name:

``` python
def purchase_formatter(
    action: ActionRecord,  # this is a purchase, but we can't use that name
    permissions: List[AuthPermission]
):
    purchase.check_can_view_history(permissions)
    return format_purchase(action)
```

If we try to use original, more-specific name `purchases` in our formatter, we'll get a
type error in the endpoint definition:
```python
purchases_endpoint: async (r: HttpRequest) -> HttpResponse) = (
    make_history_endpoint(
        action_type="purchase",
        # InvalidParameterType
        #   passed: (
        #       purchases: ActionRecord,
        #       auth_permissions: List[AuthPermission],
        #   ) -> List[FormattedItem]
        #   expected: (
        #       action: ActionRecord,
        #       permissions: List[AuthPermission],
        #   ) -> List[FormattedItem]
        formatter=purchase_formatter
    )
)
```

A key question is whether the syntactic consistency and increased power of
def-style syntax is worth throwing this kind of type error, which isn't a problem
with the existing `Callable` type or the shorthand syntax.
