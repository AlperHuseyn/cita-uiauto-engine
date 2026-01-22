from setuptools import setup, find_packages

setup(
    name="uiauto-core",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pyyaml>=5.4",
        "jsonschema>=4.0.0",
    ],
    python_requires=">=3.8",
    package_data={
        "uiauto_core": ["schemas/*.json"],
    },
)
