from setuptools import setup

# Install with: pip install --editable .

setup(
    name='vlanswap',
    version='0.1',
    py_modules=['vlanswap'],
    install_requires=[
        'Click',
        'pexpect'
    ],
    entry_points='''
        [console_scripts]
        vlanswap=vlanswap:cli
    ''',
)
