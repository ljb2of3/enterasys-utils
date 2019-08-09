from setuptools import setup

# Install with: pip install --editable .

setup(
    name='macreport',
    version='0.1',
    py_modules=['macreport'],
    install_requires=[
        'Click',
        'pexpect'
    ],
    entry_points='''
        [console_scripts]
        macreport=macreport:cli
    ''',
)
