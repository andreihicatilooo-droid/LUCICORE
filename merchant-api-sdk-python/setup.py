from setuptools import setup, find_packages

setup(
    name="merchant-api-sdk",
    version="1.11.1",
    description="SDK for Merchant API with TOR proxy support",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=["requests>=2.25.0"],
    extras_require={"tor": ["requests[socks]>=2.25.0", "PySocks>=1.7.0"]},
)
