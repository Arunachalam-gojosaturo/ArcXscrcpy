from setuptools import setup, find_packages

setup(
    name="arc-link",
    version="1.0.0",
    description="Autonomous Wireless ADB and scrcpy Recovery Bridge for Broken Android Displays",
    author="ARC-LINK Project",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "arc_link": ["ui/*.qss", "ui/widgets/*.py"],
    },
    install_requires=[
        "PyQt6>=6.5.0",
        "scapy>=2.5.0",
    ],
    entry_points={
        "console_scripts": [
            "arc-link = arc_link.main:main",
        ],
    },
    python_requires=">=3.10",
)
