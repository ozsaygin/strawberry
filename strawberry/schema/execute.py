from typing import Any, Dict, List

from graphql import (
    ExecutionResult as GraphQLExecutionResult,
    GraphQLError,
    GraphQLSchema,
    execute as original_execute,
    parse,
)
from graphql.pyutils import AwaitableOrValue
from graphql.type import validate_schema
from graphql.validation import validate
from strawberry.extensions.runner import ExtensionsRunner
from strawberry.types import ExecutionContext


def execute(
    schema: GraphQLSchema,
    query: str,
    extensions_runner: ExtensionsRunner,
    root_value: Any = None,
    context_value: Any = None,
    variable_values: Dict[str, Any] = None,
    additional_middlewares: List[Any] = None,
    operation_name: str = None,
) -> AwaitableOrValue[GraphQLExecutionResult]:
    execution_context = ExecutionContext(
        query=query,
        context=context_value,
        variables=variable_values,
        operation_name=operation_name,
    )

    additional_middlewares = additional_middlewares or []

    with extensions_runner.request(execution_context=execution_context):
        schema_validation_errors = validate_schema(schema)

        if schema_validation_errors:
            return GraphQLExecutionResult(data=None, errors=schema_validation_errors)

        try:
            with extensions_runner.parsing():
                document = parse(query)
        except GraphQLError as error:
            return GraphQLExecutionResult(data=None, errors=[error])

        except Exception as error:  # pragma: no cover
            error = GraphQLError(str(error), original_error=error)

            return GraphQLExecutionResult(data=None, errors=[error])

        with extensions_runner.validation():
            validation_errors = validate(schema, document)

        if validation_errors:
            return GraphQLExecutionResult(data=None, errors=validation_errors)

        return original_execute(
            schema,
            document,
            root_value=root_value,
            middleware=extensions_runner.as_middleware_manager(*additional_middlewares),
            variable_values=variable_values,
            operation_name=operation_name,
            context_value=context_value,
        )
