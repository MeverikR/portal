from setuptools import setup

setup(
    name='console',
    version='0.1',
    py_modules=['console'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        yourscript=console:cli
    ''',
)