from setuptools import setup, find_packages
import sys
from pathlib import Path
 
setup(
    name="AioCacheBucket",
    version="0.0.6",
    author="Chenwe-i-lin",
    author_email="1846913566@qq.com",
    description="cache for python, base on asyncio.",
    long_description=Path("./readme.md").read_text("utf-8") if Path("./readme.md").exists() else "",
    long_description_content_type="text/markdown",
    license="MIT",
    url="https://github.com/NatriumLab/AioCacheBucket",
    packages=['AioCacheBucket'],
    install_requires=[
        "infinity4py"
    ]
)