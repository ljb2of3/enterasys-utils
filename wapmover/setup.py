from setuptools import setup

setup(
    name='wapmover',
    version='0.1',
    py_modules=['wapmover'],
    install_requires=[
        'Click',
        'pyexpect'
    ],
    entry_points='''
        [console_scripts]
        wapmover=wapmover:cli
    ''',
)
