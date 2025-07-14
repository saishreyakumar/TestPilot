from setuptools import setup, find_packages

setup(
    name="qgjob",
    version="1.0.0",
    description="QualGent Job CLI - Submit and manage AppWright test jobs",
    author="QualGent",
    author_email="dev@qualgent.com",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "requests>=2.25.0",
        "colorama>=0.4.4",
        "tabulate>=0.9.0",
        "python-dotenv>=0.19.0",
    ],
    entry_points={
        "console_scripts": [
            "qgjob=qgjob.cli:main",
        ],
    },
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 