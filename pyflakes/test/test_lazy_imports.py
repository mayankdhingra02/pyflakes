from sys import version_info

from pyflakes import messages as m
from pyflakes.test.harness import TestCase, skipIf


@skipIf(version_info < (3, 15), 'new in Python 3.15')
class Test(TestCase):  # pragma: >=3.15 cover
    def test_unused_lazy_imports(self):
        self.flakes('''
        lazy import x
        lazy from y import z
        ''', m.UnusedImport, m.UnusedImport)

    def test_lazy_star_import_not_allowed(self):
        self.flakes('''
        lazy from x import *
        ''', m.LazyImportStarNotPermitted)

    def test_lazy_import_not_at_module_scope(self):
        self.flakes('''
        def f():
            lazy import x
        class C:
            lazy from y import z
        ''', m.LazyImportNotAtModuleScope, m.LazyImportNotAtModuleScope)

    def test_lazy_import_not_at_module_scope_try(self):
        self.flakes('''
        try: lazy import x
        except AssertionError: lazy import x
        else: lazy import x
        finally: lazy import x

        try: lazy import x
        except* AssertionError: ...

        try:
            if True:
                lazy import x
        except AssertionError: ...

        try: lazy from x import y
        except AssertionError: ...
        ''', *(7 * [m.LazyImportNotAtModuleScope]))

        self.flakes('''
        # allowed
        if True:
            lazy import x

        def f(): print(x)
        ''')

    def test_lazy_imports_eager_use_ok(self):
        self.flakes('''
        lazy from x import y

        x: y = ...                 # ok in annotations
        type q = y                 # ok in type aliases
        def f1(u: y) -> y: ...     # ok in function annotations
        def f2(): print(y)         # ok in nested scope
        x = (y for _ in [])        # ok not in generator iter
        ''')

    def test_lazy_imports_eager_use_error(self):
        self.flakes('''
        lazy from x import y
        z = y                     # module scope

        class C:
            z = y                 # class scope

        match y:                  # match expression
            case y.attr: pass     # case attribute

        (_ for _ in y)            # generator expression iterable

        [y for _ in [...]]        # evaluated comprehensions
        {y for _ in [...]}        # evaluated comprehensions
        {0: y for _ in [...]}     # evaluated comprehensions

        ''', *([m.EagerUseOfLazyImport] * 8))

    def test_lazy_imports_eager_use_in_type_alias(self):
        self.flakes('''
        from typing import TypeAlias
        lazy from x import y
        alias: TypeAlias = y      # evaluated eagerly
        ''', m.EagerUseOfLazyImport)

    def test_eager_use_in_TypeVar(self):
        self.flakes('''
        from typing import TypeVar
        lazy from x import y
        T = TypeVar("T", y)
        ''', m.EagerUseOfLazyImport)

    def test_literal_in_type_statements_is_deferred(self):
        self.flakes('''
        lazy from typing import Literal

        type A = Literal[int]
        ''')

    def test_literal_and_annotated_values_in_deferred_annotations(self):
        for annotation in (
                'Literal[Foo.a, Foo.b]',
                'Annotated[int, Foo.a]',
                'list[Literal[Foo.a]]',
                'Annotated[Literal[Foo.a], (Foo.b, Literal[Foo.a])]',
                "Literal['not_a_type', Foo.a]",
                "Annotated[int, 'not_a_type', Foo.a]",
        ):
            annotation = annotation.replace('Literal', 'typing.Literal')
            annotation = annotation.replace('Annotated', 'typing.Annotated')
            for statement in (
                    'value: {annotation}',
                    'class C:\n    value: {annotation}',
                    'def f(value: {annotation}) -> {annotation}: ...',
                    'type Alias = {annotation}',
            ):
                with self.subTest(annotation=annotation, statement=statement):
                    self.flakes('import typing\n'
                                'lazy from foo import Foo\n' +
                                statement.format(annotation=annotation) + '\n')

    def test_values_in_string_annotations_are_deferred(self):
        self.flakes('''
        from typing import Annotated, Literal
        lazy from foo import Foo
        def f(value: 'Literal[Foo.a]') -> 'Annotated[int, Foo.b]': ...
        ''')

    def test_values_in_future_annotations_are_deferred(self):
        self.flakes('''
        from __future__ import annotations
        from typing import Literal
        lazy from foo import Foo
        def f(value: Literal[Foo.a]): ...
        ''')

    def test_values_in_runtime_typing_expressions_are_eager(self):
        for expression in (
                'Literal[Foo.a]',
                'Annotated[int, Foo.a]',
                'list[Literal[Foo.a]]',
                'cast(Literal[Foo.a], 1)',
                'typing.List[Foo]',
        ):
            expression = expression.replace('Literal', 'typing.Literal')
            expression = expression.replace('Annotated', 'typing.Annotated')
            expression = expression.replace('cast(', 'typing.cast(')
            for statement in (
                    'alias = {expression}',
                    'alias: typing.TypeAlias = {expression}',
                    'class C:\n    alias = {expression}',
                    'def f(value={expression}): ...',
                    'f = lambda value={expression}: value',
            ):
                with self.subTest(expression=expression, statement=statement):
                    self.flakes('import typing\n'
                                'lazy from foo import Foo\n' +
                                statement.format(expression=expression) + '\n',
                                m.EagerUseOfLazyImport)
