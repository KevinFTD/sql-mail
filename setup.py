#!/usr/bin/python
# coding:utf-8
__author__ = 'kevinftd'

from setuptools import setup

setup(
    name="sqlmail",
    version="0.1",
    author='kevinftd',
    author_email='kevin09fjw@gmail.com',
    packages=['sqlmail'],
    include_package_data=True,
    url='https://github.com/KevinFTD/sql-mail',
    license='LICENSE.txt',
    description='send the SQL query results by email for daily mail report',
    long_description=open('README.md').read(),
    install_requires=[
        "Jinja2",
    ],
    test_suite='',
    tests_require=[]

)