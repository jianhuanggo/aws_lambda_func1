from setuptools import setup, find_packages

setup(
    name="lambda_deployer",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "boto3>=1.26.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "lambda-deployer=lambda_deployer.cli:main",
        ],
    },
    scripts=[
        "bin/lambda-deployer",
    ],
    description="A tool to deploy ECR images to AWS Lambda functions with S3 access and VPC configuration",
    author="Devin AI",
    author_email="devin-ai-integration[bot]@users.noreply.github.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "moto>=4.1.0",
        ],
    },
)
