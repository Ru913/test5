from setuptools import setup, find_packages

setup(
    name="avd-manager",
    version="0.1.0",
    description="Azure Virtual Desktop Management Tool",
    author="QA Test Team",
    author_email="qa@example.com",
    packages=find_packages(),
    install_requires=[
        "azure-identity>=1.15.0",
        "azure-mgmt-desktopvirtualization>=1.0.0",
        "azure-mgmt-compute>=30.5.0",
        "azure-mgmt-network>=25.2.0",
        "python-dotenv>=1.0.0",
        "pyyaml>=6.0.1",
        "requests>=2.31.0",
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)