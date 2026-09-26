from setuptools import setup, find_packages

setup(
    name="farmapreco",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["portal"],
    entry_points={
        "console_scripts": [
            "iniciar=portal:main",
        ],
    },
)
