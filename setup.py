from setuptools import setup, find_packages
from pathlib import Path

# Baca README untuk long_description
readme_path = Path(__file__).parent / "README.md"
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")
else:
    long_description = ""

setup(
    name="webfetch",
    version="0.1.0",
    description="Web content extraction tool that fetches and converts web pages to Markdown, JSON, or TXT format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Webfetch Team",
    keywords=["web", "scraping", "markdown", "content-extraction", "playwright"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Text Processing :: Markup :: Markdown",
    ],
    packages=find_packages(exclude=["tests", "__pycache__"]),
    python_requires=">=3.8",
    install_requires=[
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "lxml>=5.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "webfetch=webfetch:main",
        ],
    },
)
