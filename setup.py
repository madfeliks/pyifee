import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="pyifee",
    version="2.0",
    author="Danila Gichkin",
    author_email="d.gichkin@s7.ru",
    description="S7 IFEE python libs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://gitlab.web.s7.ru/ife/pyifee",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=['ifee'],
    install_requires=["dbus-python", "pyModeS", "ping3", "requests", "prometheus_client"],
    python_requires=">=3.10",
)
