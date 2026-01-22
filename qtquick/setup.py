from setuptools import setup, find_packages

setup(
    name="uiauto-qtquick",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "uiauto-core==1.0.0",
        "pywinauto>=0.6.8",
        "comtypes>=1.1.7",
        "pillow>=8.0.0",
    ],
    extras_require={
        "recording": ["pynput>=1.7.0"],
    },
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "uiauto-qtquick=uiauto_qtquick.cli:main",
        ],
    },
)
