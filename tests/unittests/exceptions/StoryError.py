# -*- coding: utf-8 -*-
import os

import click

from lark.exceptions import UnexpectedCharacters, UnexpectedToken

from pytest import fixture, mark

from storyscript.Intention import Intention
from storyscript.exceptions import StoryError


@fixture
def error(magic):
    return magic()


@fixture
def storyerror(error):
    return StoryError(error, 'story')


def test_storyerror_init(storyerror, error):
    assert storyerror.error == error
    assert storyerror.story == 'story'
    assert storyerror.path is None
    assert storyerror.error_code is None
    assert issubclass(StoryError, SyntaxError)


def test_storyerror_init_path():
    storyerror = StoryError('error', 'story', path='hello.story')
    assert storyerror.path == 'hello.story'


def test_storyerror_name(storyerror):
    assert storyerror.name() == 'story'


def test_storyerror_name_path(patch, storyerror):
    patch.object(os, 'getcwd', return_value='/abspath')
    storyerror.path = 'hello.story'
    assert storyerror.name() == 'hello.story'


def test_storyerror_name_reduce_path(patch, storyerror):
    """
    Ensures that paths are simplified for stories in the current working
    directory.
    """
    patch.object(os, 'getcwd', return_value='/abspath')
    storyerror.path = '/abspath/hello.story'
    assert storyerror.name() == 'hello.story'


def test_storyerror_get_line(patch, storyerror, error):
    """
    Ensures get_line returns the error line
    """
    error.line = '1'
    storyerror.story = 'x = 0\ny = 1'
    assert storyerror.get_line() == 'x = 0'


def test_storyerror_header(patch, storyerror, error):
    """
    Ensures StoryError.header returns the correct text.
    """
    patch.object(click, 'style')
    patch.object(StoryError, 'name')
    template = 'Error: syntax error in {} at line {}, column {}'
    result = storyerror.header()
    click.style.assert_called_with(StoryError.name(), bold=True)
    assert result == template.format(click.style(), error.line, error.column)


def test_storyerror_symbols(patch, storyerror, error):
    """
    Ensures StoryError.symbols creates one symbol when there is no end column.
    """
    patch.object(click, 'style')
    del error.end_column
    error.column = '1'
    result = storyerror.symbols()
    click.style.assert_called_with('^', fg='red')
    assert result == click.style()


def test_story_error_symbols_end_column(patch, storyerror, error):
    """
    Ensures StoryError.symbols creates many symbols when there is an end
    column.
    """
    patch.object(click, 'style')
    error.end_column = '4'
    error.column = '1'
    result = storyerror.symbols()
    click.style.assert_called_with('^^^', fg='red')
    assert result == click.style()


def test_storyerror_highlight(patch, storyerror, error):
    """
    Ensures StoryError.highlight produces the correct text.
    """
    patch.many(StoryError, ['get_line', 'symbols'])
    error.column = '1'
    result = storyerror.highlight()
    highlight = '{}{}'.format(' ' * 6, StoryError.symbols())
    args = (error.line, StoryError.get_line(), highlight)
    assert result == '{}|    {}\n{}'.format(*args)


def test_storyerror_hint(storyerror, error):
    assert storyerror.hint() == ''


@mark.parametrize('code, message', [
    ('E0002', "A service name can't contain `.`"),
    ('E0003', 'You have defined an argument, but not a service'),
    ('E0004', '`return` is allowed only inside functions'),
    ('E0005', "A variable name can't contain `/`"),
    ('E0006', "A variable name can't contain `-`"),
    ('E0007', 'Missing value after `=`'),
    ('E0008', 'You have misspelt `function`')
])
def test_storyerror_hint_error(storyerror, code, message):
    storyerror.error_code = code
    assert storyerror.hint() == message


def test_storyerror_identify(storyerror):
    assert storyerror.identify() == 'E0001'


@mark.parametrize('name, code', [
    ('service-name', 'E0002'),
    ('arguments-noservice', 'E0003'),
    ('return-outside', 'E0004'),
    ('variables-backslash', 'E0005'),
    ('variables-dash', 'E0006')
])
def test_storyerror_identify_codes(storyerror, error, name, code):
    error.error = name
    assert storyerror.identify() == code


def test_storyerror_identify_unexpected_token(patch, storyerror):
    patch.init(Intention)
    patch.object(Intention, 'assignment', return_value=True)
    patch.object(StoryError, 'get_line')
    storyerror.error = UnexpectedToken('token', 'expected')
    assert storyerror.identify() == 'E0007'


def test_storyerror_identify_unexpected_characters(patch, storyerror):
    patch.init(UnexpectedCharacters)
    patch.init(Intention)
    patch.object(Intention, 'is_function', return_value=True)
    patch.object(StoryError, 'get_line')
    storyerror.error = UnexpectedCharacters('seq', 'lex', 0, 0)
    assert storyerror.identify() == 'E0008'


def test_storyerror_process(patch, storyerror):
    patch.object(StoryError, 'identify')
    storyerror.process()
    assert storyerror.error_code == storyerror.identify()


def test_storyerror_message(patch, storyerror):
    patch.many(StoryError, ['process', 'header', 'highlight', 'hint'])
    result = storyerror.message()
    assert storyerror.process.call_count == 1
    args = (storyerror.header(), storyerror.highlight(), storyerror.hint())
    assert result == '{}\n\n{}\n\n{}'.format(*args)


def test_storyerror_echo(patch, storyerror):
    """
    Ensures StoryError.echo prints StoryError.message
    """
    patch.object(click, 'echo')
    patch.object(StoryError, 'message')
    storyerror.echo()
    click.echo.assert_called_with(StoryError.message())
