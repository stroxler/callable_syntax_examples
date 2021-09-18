# Example of Callable Syntax Alternatives

This codebase is a snippet of simplified but realistic request-handling
middleware lifted from a django app that requires typed Callables.

Here's the snippet using existing python syntax:
```python
from typing import Awaitable, Callable, List, Optional

from django.http.request import HttpRequest
from django.http.response import HttpResponse

from app_logic import (
    db,
    render_page,
	format_purchase,
    ActivityHistoryRecord,
    AuthPermission,
    FormattedItem,
)


def make_show_history_endpoint(
    activity_type: str,
    *,
    data_formatter: Callable[
        [ActivityHistoryRecord, List[AuthPermission]],
        FormattedItem
    ]
) -> Callable[[HttpRequest], Awaitable[HttpResponse]]:
    async def handle_request(request: HttpRequest) -> HttpResponse:
        permissions = get_auth_permissions(request.user_id)
        activities = await db.fetch_activities(activity_type)
        return render_page(
            data_formatter(activity, permissions) for activity in activities
        )
    
    return handle_request

   
def purchases_history_formatter(
    purchase: ActivityHistoryRecord,
    permissions: List[AuthPermission]
):
    purchase.check_can_view_history(permissions)
    return format_purchase(purchase)
      


purchase_history_endpoint: Callable[[HttpRequest], Awaitable[HttpResponse]] = (
    activity_type="purchase_chips",
    data_formatter=purchase_history_formatter,
)
```

# Using shorthand

With shorthand syntax, the signature of `make_history_endpoint` can be written
like this:

``` python
def make_show_history_endpoint(
    activity_type: str,
    *,
    data_formatter: (
        activity: ActivityHistoryRecord,
        permissions: List[AuthPermission],
    ) -> FormattedItem,
) -> async (r: HttpRequest) -> HttpResponse:
    ...

```

The semantics of this shorthand syntax are identical to `Callable`, other than
that we can use an `async` prefix to wrap the return type in an `Awaitable`.


# Using def-style syntax with positional arguments

If we use def-style syntax to adapt this code with its existing semantics,
the middleware maintainer is required to use positional-only arguments.

The signature of `make_show_history_endpoint` can be written either with
a trailing `/` to indicate that arguments are positional:
```python
def make_show_history_endpoint(
    activity_type: str,
    *,
    data_formatter: (
        activity: ActivityHistoryRecord,
        permissions: List[AuthPermission],
        /
    ) -> FormattedItem,
) -> async (r: HttpRequest, /) -> HttpResponse:
    ...
```

or using `__`-prefixed variable names:
```python
def make_show_history_endpoint(
    activity_type: str,
    *,
    data_formatter: (
        __activities: List[ActivityHistoryRecord],
        __permissions: List[AuthPermission],
    ) -> List[FormattedItem],
) -> async (__r: HttpRequest, /) -> HttpResponse:
    ...
```

If we don't want to break existing use cases, where handler implementors
are free to use a variable name (like `purchase`) that is specific to
one particular situation, then we need to be careful to use positional-only
arguments.

# Using def-style syntax with named arguments

The flip side of def-style syntax requiring `/` for all existing Callable
types is that we can intentionally pin the variable names, and then call
functions with named arguments.

For example, the middleware author could write this code, which isn't expressible
using the existing `Callable` type because of its use of named arguments:
``` python
def make_show_history_endpoint(
    activity_type: str,
    *,
    data_formatter: (
        activity: ActivityHistoryRecord,
        permissions: List[AuthPermission],
    ) -> FormattedItem,
) -> async (HttpRequest) -> HttpResponse:
    async def handle_request(request: HttpRequest) -> HttpResponse:
        permissions = get_auth_permissions(request.user_id)
        activities = await db.fetch_activities(activity_type)
        return render_page(
            data_formatter(
                activity=activity,
                permissions=permissions,
            ) for activity in activities
        )
    
    return handle_request
```

But now the implementation of `purchases_history_formatter` is incorrect: we used
the variable name `purchase` for the purchases but the use of named-or-positional
arguments means all implementations have to use the generic variable name:

``` python
def purchases_history_formatter(
    activity: ActivityHistoryRecord,  # purchase
    permissions: List[AuthPermission]
):
    purchase.check_can_view_history(permissions)
    return format_purchase(activity)
```

If we try to use original, more-specific name `purchases` in our formatter, we'll get a
type error in the endpoint definition:
```python
chips_history_endpoint: async (r: HttpRequest) -> HttpResponse) = (
    make_show_history_endpoint(
        activity_type="purchase_chips",
        # InvalidParameterType
        #   passed: (
        #       purchases: ActivityHistoryRecord,
        #       auth_permissions: List[AuthPermission],
        #   ) -> List[FormattedItem]
        #   expected: (
        #       activity: ActivityHistoryRecord,
        #       permissions: List[AuthPermission],
        #   ) -> List[FormattedItem]
        data_formatter=chips_history_formatter
    )
)
```

A key question is whether the syntactic consistency and increased power of
def-style syntax is worth throwing this kind of type error, which isn't a problem
with the existing `Callable` type or the shorthand syntax.

