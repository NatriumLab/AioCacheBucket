from setuptools import setup, find_packages
import sys
 
setup(
    name="AioCacheBucket",
    version="0.0.3",
    author="Chenwe-i-lin",
    author_email="1846913566@qq.com",
    description="cache for python, base on asyncio.",
    long_description=open("readme.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/NatriumLab/AioCacheBucket",
    packages=['AioCacheBucket'],
    install_requires=[
        "infinity4py"
    ]
)