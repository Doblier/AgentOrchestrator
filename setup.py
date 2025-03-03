"""
Setup script for AORBIT package.
"""

from setuptools import setup, find_packages
import os
import re

# Read version from the __init__.py file
with open(os.path.join("agentorchestrator", "__init__.py"), "r") as f:
    content = f.read()
    version_match = re.search(r'^__version__ = ["\']([^"\']*)["\']', content, re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string in __init__.py")

# Read long description from README.md
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="aorbit",
    version=version,
    author="AORBIT Team",
    author_email="info@aorbit.io",
    description="A powerful agent orchestration framework optimized for financial applications",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aorbit/aorbit",
    project_urls={
        "Bug Tracker": "https://github.com/aorbit/aorbit/issues",
        "Documentation": "https://docs.aorbit.io",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    package_dir={"": "."},
    packages=find_packages(where="."),
    python_requires=">=3.10",
    install_requires=[
        "fastapi>=0.110.0",
        "pydantic>=2.5.0",
        "uvicorn>=0.25.0",
        "redis>=5.0.0",
        "click>=8.1.7",
        "cryptography>=42.0.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "httpx>=0.25.2",
        "python-jose[cryptography]>=3.3.0",
        "langgraph>=0.0.19",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "isort>=5.12.0",
            "mypy>=1.5.1",
            "ruff>=0.0.292",
        ],
        "docs": [
            "mkdocs>=1.5.3",
            "mkdocs-material>=9.4.2",
            "mkdocstrings>=0.23.0",
            "mkdocstrings-python>=1.7.3",
        ],
    },
    entry_points={
        "console_scripts": [
            "aorbit=agentorchestrator.cli:cli",
        ],
    },
) 