from setuptools import setup, find_packages

setup(
    name="apfelpilot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=["httpx>=0.27", "click>=8.0"],
    entry_points={"console_scripts": ["apfelpilot=apfelpilot.cli:entry_point"]},
)
